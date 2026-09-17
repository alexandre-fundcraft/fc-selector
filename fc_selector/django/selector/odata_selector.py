"""
OData Selector for Django models.

Provides a clean selector interface for executing OData queries on Django models.
"""

# pylint: disable=protected-access  # Django's _meta is part of the public API for model introspection

import re
from typing import TYPE_CHECKING, Any, Optional

from django.db.models import QuerySet

from fc_selector.core import exceptions as core_ex
from fc_selector.core.intent.policies import collection_defaults
from fc_selector.core.query_builder import QueryBuilder
from fc_selector.django.executor import DjangoExecutor
from fc_selector.django.utils import resolve_field_alias
from fc_selector.protocols.odata.builder import dto_options

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

        self.apply_functions = getattr(meta, "apply_functions", {})
        self.apply_aggregates = getattr(meta, "apply_aggregates", {})

        # Security: Validate field aliases to prevent injection
        ODataSelector._validate_field_aliases(self.field_aliases)

        non_sortable = [] if getattr(meta, "sortable_fields", None) is not None else self.non_sortable_fields
        self._executor = DjangoExecutor(
            field_aliases=self.field_aliases,
            allowed_fields=self.allowed_fields,
            expandable_fields=self.expandable_fields,
            non_sortable_fields=non_sortable or None,
            filterable_fields=getattr(meta, "filterable_fields", None),
            non_filterable_fields=self.non_filterable_fields,
            sortable_fields=getattr(meta, "sortable_fields", None),
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
            allowed = {resolve_field_alias(f, self.field_aliases) for f in self.filterable_fields}
            return [f for f in all_fields if f not in allowed]
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
            allowed = {resolve_field_alias(f, self.field_aliases) for f in self.sortable_fields}
            return [f for f in all_fields if f not in allowed]
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

        params = parse_query_params(query_string)
        return params, parse_odata_query(params)

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
        if selected_fields is None and self.allowed_fields is not None:
            selected_fields = set(self.allowed_fields)
        # Pass reverse aliases for field mapping (model_field -> dto_field)
        from fc_selector.django.projection import read_model_value
        from fc_selector.protocols.odata.builder import projection_intent

        intent = projection_intent(selected_fields, expanded_fields, expand_options)
        return self.dto_class.from_object(
            instance, intent, value_reader=read_model_value, **self._executor.projection_mappings(intent)
        )

    def to_dtos(self, instances, selected_fields=None, expanded_fields=None, expand_options=None) -> list[Any]:
        return [self.to_dto(inst, selected_fields, expanded_fields, expand_options) for inst in instances]

    def query_as_dtos(self, query_string: str | None = None, model_class=None, base_queryset=None) -> list[Any]:
        if not (model_class or self.model):
            raise ValueError("model_class required")

        if base_queryset is None:
            base_queryset = self.get_queryset()

        _, intent = self._parse(query_string or "")
        intent = self._apply_defaults(intent)
        return self._materialize(intent, base_queryset)

    def _materialize(self, intent, queryset, *, as_dicts=False) -> list:
        intent = self._executor.prepare(queryset, intent)
        if self.values_mode:
            hybrid = self._executor._try_hybrid_prepared(queryset, intent, self.dto_class, as_dicts=as_dicts)
            if hybrid is not None:
                return hybrid
        has_expand = intent.expand and intent.expand.has_relations()
        has_properties = self.dto_class and any(
            isinstance(getattr(queryset.model, resolve_field_alias(name, self.field_aliases), None), property)
            for name in (intent.select.fields if intent.select else self.dto_class._get_dto_fields())
        )
        if as_dicts and not has_expand and not has_properties:
            rows = list(self._executor._execute_prepared(queryset, intent, use_values=True))
            if intent.select is not None:
                return [
                    {
                        (name if self.dto_class else resolve_field_alias(name, self.field_aliases)): row[
                            resolve_field_alias(name, self.field_aliases)
                        ]
                        for name in intent.select.fields
                        if resolve_field_alias(name, self.field_aliases) in row
                    }
                    for row in rows
                ]
            return rows
        queryset = self._executor._execute_prepared(queryset, intent)
        selected, options = dto_options(intent)
        dtos = self.to_dtos(queryset, selected, set(options), options)
        return [dto.to_dict() for dto in dtos] if as_dicts else dtos

    def query_as_dicts(
        self,
        query_string: str | None = None,
        model_class: Optional["Model"] = None,
        base_queryset: QuerySet | None = None,
    ) -> list[dict]:
        if not (model_class or self.model):
            raise ValueError("model_class required")

        if base_queryset is None:
            base_queryset = self.get_queryset()

        _, intent = self._parse(query_string or "")
        if intent.apply is not None and intent.apply.has_apply():
            from fc_selector.django.query.apply_executor import apply_to_queryset

            queryset = apply_to_queryset(
                base_queryset,
                intent.apply,
                allowed_fields=self.allowed_fields,
                apply_functions=self.apply_functions,
                apply_aggregates=self.apply_aggregates,
            )
            return list(queryset)

        return self._materialize(self._apply_defaults(intent), base_queryset, as_dicts=True)

    def _build_intent(self, query_builder: QueryBuilder | None) -> "QueryIntent":
        """Build the intent for a builder, applying the selector's defaults."""
        return self._apply_defaults((query_builder or QueryBuilder()).build())

    def _apply_defaults(self, intent: "QueryIntent") -> "QueryIntent":
        """Bound materialized collections; low-level query/execute remain composable."""
        return collection_defaults(
            intent, ordering=self.default_ordering, limit=self.default_limit, maximum=self.max_limit
        )

    def get_many(self, query_builder: QueryBuilder | None = None) -> list[Any]:
        """Execute a query and return results as DTOs."""
        return self._materialize(self._build_intent(query_builder), self.get_queryset())

    def get_many_dicts(self, query_builder: QueryBuilder | None = None) -> list[dict]:
        """Execute a bounded collection query as dictionaries."""
        return self._materialize(self._build_intent(query_builder), self.get_queryset(), as_dicts=True)

    def get_one(self, query_builder: QueryBuilder, base_queryset: QuerySet | None = None) -> Any | None:
        intent = query_builder.build()
        if base_queryset is None:
            base_queryset = self.get_queryset()
        intent = self._executor.prepare(base_queryset, intent)
        queryset = self._executor._execute_prepared(base_queryset, intent)
        instance = queryset.first()
        if not instance:
            return None

        sel, opts = dto_options(intent)

        return self.to_dto(instance, sel, set(opts.keys()), opts)

    def get_by_pk(self, pk: Any, query_builder: QueryBuilder | None = None) -> Any | None:
        if self.model is None:
            raise ValueError("model not configured")
        pk_field = self.model._meta.pk
        queryset = self.get_queryset().filter(pk=pk_field.to_python(pk))
        return self.get_one(query_builder or QueryBuilder(), queryset)

    def count_by(self, query_builder: QueryBuilder | None = None) -> int:
        if query_builder is None:
            query_builder = QueryBuilder()
        intent = query_builder.build()
        intent.pagination = None
        count: int = self.execute(intent).count()
        return count

    def exists_by(self, query_builder: QueryBuilder | None = None) -> bool:
        if query_builder is None:
            query_builder = QueryBuilder()
        exists: bool = self.execute(query_builder.build()).exists()
        return exists

    # --- Alias Support (Private implementation needed by query()) ---
