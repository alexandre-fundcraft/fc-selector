"""
OData Selector for Django models.

Provides a clean selector interface for executing OData queries on Django models.
"""

# pylint: disable=protected-access  # Django's _meta is part of the public API for model introspection

import re
from typing import TYPE_CHECKING, Any, Literal, Optional, cast
from urllib.parse import unquote_plus

from django.db.models import QuerySet

from fc_selector.core import exceptions as core_ex
from fc_selector.core.query_builder import QueryBuilder
from fc_selector.django.executor import DjangoExecutor

# Security: Valid field name pattern (alphanumeric + underscore only)
_VALID_FIELD_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Security: Maximum query string length to prevent DoS attacks
MAX_QUERY_STRING_LENGTH = 4096

# Pagination defaults
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500

if TYPE_CHECKING:
    from django.db.models import Model

    from fc_selector.core.intent import QueryIntent


class ODataSelector:
    """
    Selector for executing OData queries on Django models.

    This class provides a high-level API for data access using OData patterns,
    abstracting away the Django ORM details.
    """

    def __init__(self, model_class: Optional["Model"] = None):
        """Initialize selector.

        All configuration must be defined in an inner Meta class:
            - model: The Django model class
            - dto_class: The DTO class for serialization
            - expandable_fields: Dict mapping relation names to DTO classes
            - field_aliases: Dict mapping API field names to DB column names
            - allowed_fields: List of fields available for $select
            - filterable_fields: List of fields available for $filter (positive list, takes priority)
            - non_filterable_fields: List of fields NOT available for $filter (negative list)
            - sortable_fields: List of fields available for $orderby (positive list, takes priority)
            - non_sortable_fields: List of fields NOT available for $orderby (negative list)
            - default_ordering: List of default ordering fields (e.g., ["-created_at"])
            - default_limit: Default limit if $top not specified (default: 100)
            - max_limit: Maximum allowed limit (default: 500)
            - values_mode: If True (default), use .values() and hybrid mode for
                          forward $expand.  Set to False when your DTO includes
                          @property fields that need model instantiation.

        Field restriction priority (hybrid approach):
            1. If filterable_fields is defined → only those fields are filterable
            2. If only non_filterable_fields is defined → all fields except those are filterable
            3. If neither is defined → all fields are filterable

        Same logic applies to sortable_fields/non_sortable_fields.
        """
        if not hasattr(self.__class__, "Meta"):
            raise ValueError(f"{self.__class__.__name__} must define a Meta class")

        meta = self.__class__.Meta
        self.model = getattr(meta, "model", model_class)
        self.dto_class = getattr(meta, "dto_class", None)
        self.expandable_fields = getattr(meta, "expandable_fields", {})
        self.field_aliases = getattr(meta, "field_aliases", {})
        self.allowed_fields = getattr(meta, "allowed_fields", None)
        self.filterable_fields = getattr(meta, "filterable_fields", [])
        self.non_filterable_fields = getattr(meta, "non_filterable_fields", [])
        self.sortable_fields = getattr(meta, "sortable_fields", [])
        self.non_sortable_fields = getattr(meta, "non_sortable_fields", [])
        self.default_ordering = getattr(meta, "default_ordering", [])
        self.default_limit = getattr(meta, "default_limit", DEFAULT_PAGE_SIZE)
        self.max_limit = getattr(meta, "max_limit", MAX_PAGE_SIZE)
        self.values_mode = getattr(meta, "values_mode", True)

        # Security: Validate field aliases to prevent injection
        ODataSelector._validate_field_aliases(self.field_aliases)

        non_sortable = self.get_non_sortable_fields()
        self._executor = DjangoExecutor(
            field_aliases=self.field_aliases,
            allowed_fields=self.allowed_fields,
            expandable_fields=self.expandable_fields,
            non_sortable_fields=non_sortable or None,
        )
        self._reverse_aliases: dict[str, str] = {v: k for k, v in self.field_aliases.items()}

    @staticmethod
    def _validate_field_aliases(aliases: dict[str, str]) -> None:
        """Validate field aliases to prevent injection attacks.

        Args:
            aliases: Dictionary of alias -> internal field name mappings

        Raises:
            ValueError: If any alias or field name contains invalid characters
        """
        if not aliases:
            return
        for alias, internal in aliases.items():
            if not _VALID_FIELD_PATTERN.match(alias):
                raise ValueError(f"Invalid field alias '{alias}': must be alphanumeric with underscores only")
            # Internal field can have dots for nested access (e.g., "user.email")
            for part in internal.split("."):
                if not _VALID_FIELD_PATTERN.match(part):
                    raise ValueError(
                        f"Invalid internal field '{internal}': each part must be alphanumeric with underscores only"
                    )

    # ==================== Field Introspection ====================

    def _get_model_field_names(self) -> list[str]:
        """Get all concrete field names from the model."""
        if not self.model:
            return []
        return [f.name for f in self.model._meta.get_fields() if hasattr(f, "name") and hasattr(f, "get_internal_type")]

    def get_non_filterable_fields(self) -> list[str]:
        """Get list of fields that cannot be used in $filter.

        Uses hybrid approach:
        1. If filterable_fields is defined → invert to get non-filterable
        2. If only non_filterable_fields is defined → use directly
        3. If neither → empty list (all fields filterable)
        """
        if self.filterable_fields:
            all_fields = self._get_model_field_names()
            return [f for f in all_fields if f not in self.filterable_fields]
        if self.non_filterable_fields:
            return list(self.non_filterable_fields)
        return []

    def get_non_sortable_fields(self) -> list[str]:
        """Get list of fields that cannot be used in $orderby.

        Uses hybrid approach:
        1. If sortable_fields is defined → invert to get non-sortable
        2. If only non_sortable_fields is defined → use directly
        3. If neither → empty list (all fields sortable)
        """
        if self.sortable_fields:
            all_fields = self._get_model_field_names()
            return [f for f in all_fields if f not in self.sortable_fields]
        if self.non_sortable_fields:
            return list(self.non_sortable_fields)
        return []

    # ==================== Public API ====================

    def get_queryset(self) -> QuerySet:
        """
        Get base queryset for this selector.

        Automatically detects OneToOne fields and applies select_related to prevent
        N+1 queries for profile-like models.
        """
        if not self.model:
            raise ValueError("model not configured")

        qs = self.model.objects.all()

        # Auto-detect OneToOne fields and select_related them
        try:
            from django.db.models import OneToOneField

            select_related_fields = []
            for field in self.model._meta.fields:
                if isinstance(field, OneToOneField):
                    select_related_fields.append(field.name)

            if select_related_fields:
                qs = qs.select_related(*select_related_fields)
        except (AttributeError, TypeError):
            pass

        return qs

    def _parse(self, query_string: str) -> tuple[dict[str, str], "QueryIntent"]:
        """Parse an OData query string into (raw params, QueryIntent).

        Field aliases are resolved per field further down (executor, visitor and
        hybrid builder all call ``resolve_field_alias``), so nothing is rewritten
        in the raw query string here.
        """
        from fc_selector.protocols.odata.parsers.query import parse_odata_query, parse_query_params

        # Security: Validate query string length to prevent DoS
        if len(query_string) > MAX_QUERY_STRING_LENGTH:
            raise core_ex.QueryError(
                f"Query string too long ({len(query_string)} chars). Maximum allowed: {MAX_QUERY_STRING_LENGTH}"
            )

        params = parse_query_params(unquote_plus(query_string))
        return params, parse_odata_query(params)

    @staticmethod
    def _dto_options(params: dict[str, str]) -> tuple[set[str] | None, dict]:
        """Read the $select fields and raw $expand options the DTO layer needs."""
        from fc_selector.protocols.odata.parsers.expand import parse_expand
        from fc_selector.protocols.odata.parsers.select import parse_select

        selected = set(parse_select(params["$select"])) if params.get("$select") else None
        expand_options = parse_expand(params["$expand"]) if params.get("$expand") else {}
        return selected, expand_options

    def query(
        self,
        query_string: str | None = None,
        model_class: Optional["Model"] = None,
        base_queryset: QuerySet | None = None,
    ) -> QuerySet:
        """Execute OData query string and return QuerySet.

        Uses the internal executor which has allowed_fields configured,
        enabling filtering on annotated fields.
        """
        if not (model_class or self.model):
            raise ValueError("model_class required")

        if base_queryset is None:
            base_queryset = self.get_queryset()

        if not query_string:
            return base_queryset

        _, intent = self._parse(query_string)
        return self._executor.execute(base_queryset, intent)

    def execute(
        self,
        intent: "QueryIntent",
        base_queryset: QuerySet | None = None,
        *,
        use_values: bool = False,
    ) -> QuerySet:
        """Execute a QueryIntent and return a QuerySet.

        Args:
            intent: QueryIntent with filter, select, expand, etc.
            base_queryset: Optional base queryset to apply intent to
            use_values: If True, use .values() for faster dict-based results.

        Returns:
            QuerySet (or ValuesQuerySet when use_values=True and no expand).
        """
        if base_queryset is None:
            base_queryset = self.get_queryset()

        return self._executor.execute(base_queryset, intent, use_values=use_values)

    # --- DTO Conversion logic ---

    def to_dto(self, instance: "Model", selected_fields=None, expanded_fields=None, expand_options=None) -> Any:
        if not self.dto_class:
            raise ValueError("dto_class not configured")
        # Pass reverse aliases for field mapping (model_field -> dto_field)
        return self.dto_class.from_model(
            instance, selected_fields, expanded_fields, expand_options, field_mapping=self._reverse_aliases
        )

    def to_dtos(self, instances, selected_fields=None, expanded_fields=None, expand_options=None) -> list[Any]:
        return [self.to_dto(inst, selected_fields, expanded_fields, expand_options) for inst in instances]

    def query_as_dtos(self, query_string: str | None = None, model_class=None, base_queryset=None) -> list[Any]:
        if not (model_class or self.model):
            raise ValueError("model_class required")

        if base_queryset is None:
            base_queryset = self.get_queryset()

        if not query_string:
            return self.to_dtos(base_queryset)

        params, intent = self._parse(query_string)

        if self.values_mode:
            hybrid = self._executor.try_hybrid(base_queryset, intent, self.dto_class)
            if hybrid is not None:
                return list(hybrid)

        # Standard path: convert model instances to DTOs
        queryset = self._executor.execute(base_queryset, intent)
        selected_fields, expand_options = self._dto_options(params)

        return self.to_dtos(queryset, selected_fields, set(expand_options), expand_options)

    def query_as_dicts(
        self,
        query_string: str | None = None,
        model_class: Optional["Model"] = None,
        base_queryset: QuerySet | None = None,
    ) -> list[dict]:
        """Execute OData query and return results as plain dictionaries.

        Args:
            query_string: OData query string (e.g., "$filter=name eq 'test'&$select=id,name")
            model_class: Optional model class override
            base_queryset: Optional base queryset to apply query to

        Returns:
            List of dicts.
        """
        if not (model_class or self.model):
            raise ValueError("model_class required")

        if base_queryset is None:
            base_queryset = self.get_queryset()

        if not query_string:
            return list(base_queryset.values())

        _, intent = self._parse(query_string)

        if self.values_mode:
            hybrid = self._executor.try_hybrid(base_queryset, intent, self.dto_class, as_dicts=True)
            if hybrid is not None:
                return hybrid

        return list(self._executor.execute(base_queryset, intent, use_values=True))

    # --- New Query Builder Methods ---

    def _build_intent(self, query_builder: QueryBuilder | None) -> "QueryIntent":
        """Build the intent for a builder, applying the selector's defaults."""
        from fc_selector.core.intent import OrderField, OrderIntent, PaginationIntent

        intent = (query_builder or QueryBuilder()).build()

        if self.default_ordering and (not intent.orderby or not intent.orderby.has_ordering()):
            intent.orderby = OrderIntent(
                fields=[
                    OrderField(
                        field=field.lstrip("-"),
                        direction=cast(Literal["asc", "desc"], "desc" if field.startswith("-") else "asc"),
                    )
                    for field in self.default_ordering
                ]
            )

        if not intent.pagination or not intent.pagination.has_pagination():
            intent.pagination = PaginationIntent(limit=self.default_limit, offset=0)
        elif intent.pagination.limit and intent.pagination.limit > self.max_limit:
            intent.pagination.limit = self.max_limit

        return intent

    def get_many(self, query_builder: QueryBuilder | None = None) -> list[Any]:
        """Execute a query and return results as DTOs."""
        intent = self._build_intent(query_builder)

        if self.values_mode:
            hybrid = self._executor.try_hybrid(self.get_queryset(), intent, self.dto_class)
            if hybrid is not None:
                return hybrid

        # Standard path: evaluate queryset -> model instances -> DTOs
        sel, opts = self._select_and_expand_options(query_builder)
        return self.to_dtos(self.execute(intent), sel, set(opts.keys()), opts)

    def get_many_dicts(self, query_builder: QueryBuilder | None = None) -> list[dict]:
        """Execute a query and return results as plain dictionaries."""
        intent = self._build_intent(query_builder)

        if self.values_mode:
            hybrid = self._executor.try_hybrid(self.get_queryset(), intent, self.dto_class, as_dicts=True)
            if hybrid is not None:
                return hybrid

        return list(self.execute(intent, use_values=True))

    @staticmethod
    def _select_and_expand_options(query_builder: QueryBuilder | None) -> tuple[set[str] | None, dict]:
        """Read back $select fields and $expand options from a builder."""
        return ODataSelector._dto_options(query_builder.to_dict() if query_builder else {})

    def get_one(self, query_builder: QueryBuilder) -> Any | None:
        intent = query_builder.build()
        queryset = self.execute(intent)
        instance = queryset.first()
        if not instance:
            return None

        sel, opts = self._select_and_expand_options(query_builder)

        return self.to_dto(instance, sel, set(opts.keys()), opts)

    def get_by_pk(self, pk: Any, query_builder: QueryBuilder | None = None) -> Any | None:
        if query_builder is None:
            query_builder = QueryBuilder()
        query_builder.and_filter(f"id eq {pk}")
        return self.get_one(query_builder)

    def count_by(self, query_builder: QueryBuilder | None = None) -> int:
        if query_builder is None:
            query_builder = QueryBuilder()
        count: int = self.execute(query_builder.build()).count()
        return count

    def exists_by(self, query_builder: QueryBuilder | None = None) -> bool:
        if query_builder is None:
            query_builder = QueryBuilder()
        exists: bool = self.execute(query_builder.build()).exists()
        return exists

    # --- Alias Support (Private implementation needed by query()) ---
