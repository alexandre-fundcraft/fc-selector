"""
OData Selector for Django models.

Provides a clean selector interface for executing OData queries on Django models.
"""

# pylint: disable=protected-access  # Django's _meta is part of the public API for model introspection

import logging
import re
import time
from typing import TYPE_CHECKING, Any, Literal, Optional, cast

from django.db.models import QuerySet

from fc_selector.core import exceptions as core_ex
from fc_selector.core.query_builder import QueryBuilder
from fc_selector.django.executor import DjangoExecutor

logger = logging.getLogger(__name__)

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

    @staticmethod
    def is_filterable() -> bool:
        """Check if $filter is supported for this entity."""
        return True

    @staticmethod
    def is_sortable() -> bool:
        """Check if $orderby is supported for this entity."""
        return True

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
        from fc_selector.protocols.odata.converters import odata_query_to_intent
        from fc_selector.protocols.odata.parsers.query.parser import parse_odata_query

        model = model_class or self.model
        if not model:
            raise ValueError("model_class required")

        if base_queryset is None:
            base_queryset = self.get_queryset()

        if not query_string:
            return base_queryset

        # Security: Validate query string length to prevent DoS
        if len(query_string) > MAX_QUERY_STRING_LENGTH:
            raise core_ex.QueryError(
                f"Query string too long ({len(query_string)} chars). Maximum allowed: {MAX_QUERY_STRING_LENGTH}"
            )

        # Resolve aliases in query string (OData specific logic)
        resolved_qs = self._resolve_aliases_in_query_string(query_string)

        # Parse OData query string to QueryIntent
        odata_query = parse_odata_query(resolved_qs)
        intent = odata_query_to_intent(odata_query)

        # Ensure AST is populated for filters (lazy parsing handling)
        if intent.filter and intent.filter.expression and not intent.filter.ast:
            from fc_selector.protocols.odata.parsers.filter import parse_filter

            intent.filter.ast = parse_filter(intent.filter.expression)

        # Use internal executor which has allowed_fields configured
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
        from fc_selector.protocols.odata.converters import odata_query_to_intent
        from fc_selector.protocols.odata.parsers.query.parser import parse_odata_query

        model = model_class or self.model
        if not model:
            raise ValueError("model_class required")

        if base_queryset is None:
            base_queryset = self.get_queryset()

        if not query_string:
            return self.to_dtos(base_queryset)

        # Security: Validate query string length to prevent DoS
        if len(query_string) > MAX_QUERY_STRING_LENGTH:
            raise core_ex.QueryError(
                f"Query string too long ({len(query_string)} chars). Maximum allowed: {MAX_QUERY_STRING_LENGTH}"
            )

        resolved_qs = self._resolve_aliases_in_query_string(query_string)
        odata_query = parse_odata_query(resolved_qs)
        intent = odata_query_to_intent(odata_query)

        if intent.filter and intent.filter.expression and not intent.filter.ast:
            from fc_selector.protocols.odata.parsers.filter import parse_filter

            intent.filter.ast = parse_filter(intent.filter.expression)

        if self.values_mode:
            hybrid = self._executor.try_hybrid(base_queryset, intent, self.dto_class)
            if hybrid is not None:
                return list(hybrid)

        # Standard path: convert model instances to DTOs
        queryset = self._executor.execute(base_queryset, intent)
        selected_fields = set(odata_query.select.fields) if odata_query.select else None
        expand_options = dict(odata_query.expand.nested_options) if odata_query.expand else {}

        return self.to_dtos(queryset, selected_fields, set(expand_options.keys()), expand_options)

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
        from fc_selector.protocols.odata.converters import odata_query_to_intent
        from fc_selector.protocols.odata.parsers.query.parser import parse_odata_query

        model = model_class or self.model
        if not model:
            raise ValueError("model_class required")

        if base_queryset is None:
            base_queryset = self.get_queryset()

        if not query_string:
            return list(base_queryset.values())

        # Security: Validate query string length to prevent DoS
        if len(query_string) > MAX_QUERY_STRING_LENGTH:
            raise core_ex.QueryError(
                f"Query string too long ({len(query_string)} chars). Maximum allowed: {MAX_QUERY_STRING_LENGTH}"
            )

        resolved_qs = self._resolve_aliases_in_query_string(query_string)
        odata_query = parse_odata_query(resolved_qs)
        intent = odata_query_to_intent(odata_query)

        if intent.filter and intent.filter.expression and not intent.filter.ast:
            from fc_selector.protocols.odata.parsers.filter import parse_filter

            intent.filter.ast = parse_filter(intent.filter.expression)

        if self.values_mode:
            hybrid = self._executor.try_hybrid(base_queryset, intent, self.dto_class, as_dicts=True)
            if hybrid is not None:
                return hybrid

        return list(self._executor.execute(base_queryset, intent, use_values=True))

    # --- New Query Builder Methods ---

    def get_many(self, query_builder: QueryBuilder | None = None) -> list[Any]:
        t0 = time.perf_counter()

        if query_builder is None:
            query_builder = QueryBuilder()

        intent = query_builder.build()

        # Apply default ordering if not specified
        if self.default_ordering and (not intent.orderby or not intent.orderby.has_ordering()):
            from fc_selector.core.intent import OrderField, OrderIntent

            order_fields = []
            for field in self.default_ordering:
                direction = cast(Literal["asc", "desc"], "desc" if field.startswith("-") else "asc")
                field_name = field.lstrip("-")
                order_fields.append(OrderField(field=field_name, direction=direction))
            intent.orderby = OrderIntent(fields=order_fields)

        # Apply default pagination if not specified
        if not intent.pagination or not intent.pagination.has_pagination():
            from fc_selector.core.intent import PaginationIntent

            intent.pagination = PaginationIntent(limit=self.default_limit, offset=0)
        elif intent.pagination.limit and intent.pagination.limit > self.max_limit:
            # Cap at max_limit
            intent.pagination.limit = self.max_limit

        t1 = time.perf_counter()

        # Try hybrid values path first
        base_qs = self.get_queryset()
        if self.values_mode:
            hybrid = self._executor.try_hybrid(base_qs, intent, self.dto_class)
            t2 = time.perf_counter()

            if hybrid is not None:
                logger.debug(
                    "[get_many] build_intent=%.3fs, hybrid_execute=%.3fs",
                    t1 - t0,
                    t2 - t1,
                )
                return hybrid
        else:
            t2 = t1

        # Standard path: evaluate queryset -> model instances -> DTOs
        qs_str = query_builder.build_query_string()
        from fc_selector.protocols.odata.parsers.query import parse_odata_query

        qp = parse_odata_query(qs_str) if qs_str else None

        sel = set(qp.select.fields) if qp and qp.select else None
        opts = dict(qp.expand.nested_options) if qp and qp.expand else {}
        t3 = time.perf_counter()

        queryset = self.execute(intent)
        t4 = time.perf_counter()

        dtos = self.to_dtos(queryset, sel, set(opts.keys()), opts)
        t5 = time.perf_counter()

        logger.debug(
            "[get_many] build_intent=%.3fs, execute=%.3fs, parse_opts=%.3fs, fetch_db=%.3fs, to_dtos=%.3fs",
            t1 - t0,
            t2 - t1,
            t3 - t2,
            t4 - t3,
            t5 - t4,
        )

        return dtos

    def get_many_dicts(self, query_builder: QueryBuilder | None = None) -> list[dict]:
        """Execute query and return results as plain dictionaries.

        Args:
            query_builder: Optional QueryBuilder with filter, select, orderby, etc.

        Returns:
            List of dicts.
        """
        t0 = time.perf_counter()

        if query_builder is None:
            query_builder = QueryBuilder()

        intent = query_builder.build()

        # Apply default ordering if not specified
        if self.default_ordering and (not intent.orderby or not intent.orderby.has_ordering()):
            from fc_selector.core.intent import OrderField, OrderIntent

            order_fields = []
            for field in self.default_ordering:
                direction = cast(Literal["asc", "desc"], "desc" if field.startswith("-") else "asc")
                field_name = field.lstrip("-")
                order_fields.append(OrderField(field=field_name, direction=direction))
            intent.orderby = OrderIntent(fields=order_fields)

        # Apply default pagination if not specified
        if not intent.pagination or not intent.pagination.has_pagination():
            from fc_selector.core.intent import PaginationIntent

            intent.pagination = PaginationIntent(limit=self.default_limit, offset=0)
        elif intent.pagination.limit and intent.pagination.limit > self.max_limit:
            intent.pagination.limit = self.max_limit

        t1 = time.perf_counter()

        base_qs = self.get_queryset()
        if self.values_mode:
            hybrid = self._executor.try_hybrid(base_qs, intent, self.dto_class, as_dicts=True)
            t2 = time.perf_counter()

            if hybrid is not None:
                logger.debug(
                    "[get_many_dicts] build_intent=%.3fs, hybrid_execute=%.3fs",
                    t1 - t0,
                    t2 - t1,
                )
                return hybrid
        else:
            t2 = t1

        results = list(self.execute(intent, use_values=True))
        t3 = time.perf_counter()

        logger.debug(
            "[get_many_dicts] build_intent=%.3fs, execute=%.3fs, fetch_db=%.3fs",
            t1 - t0,
            t2 - t1,
            t3 - t2,
        )

        return results

    def get_one(self, query_builder: QueryBuilder) -> Any | None:
        intent = query_builder.build()
        queryset = self.execute(intent)
        instance = queryset.first()
        if not instance:
            return None

        qs_str = query_builder.build_query_string()
        from fc_selector.protocols.odata.parsers.query import parse_odata_query

        qp = parse_odata_query(qs_str) if qs_str else None
        sel = set(qp.select.fields) if qp and qp.select else None
        opts = dict(qp.expand.nested_options) if qp and qp.expand else {}

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

    def _resolve_aliases_in_query_string(self, query_string: str) -> str:
        if not query_string or not self.field_aliases:
            return query_string
        from urllib.parse import unquote_plus

        query_string = unquote_plus(query_string)
        params = {}
        for param in query_string.split("&"):
            if "=" in param:
                k, v = param.split("=", 1)
                if k == "$filter":
                    v = self._resolve_aliases_in_filter(v)
                elif k == "$select":
                    v = self._resolve_aliases_in_select(v)
                elif k == "$orderby":
                    v = self._resolve_aliases_in_orderby(v)
                params[k] = v
        return "&".join(f"{k}={v}" for k, v in params.items())

    def _resolve_aliases_in_filter(self, filter_value: str) -> str:
        result = filter_value
        for alias in sorted(self.field_aliases.keys(), key=len, reverse=True):
            internal = self.field_aliases[alias]
            pattern = r"\b" + re.escape(alias) + r"\b(?=(?:[^']*'[^']*')*[^']*$)"
            result = re.sub(pattern, internal, result)
        return result

    def _resolve_aliases_in_select(self, val):
        return ",".join([self.field_aliases.get(f.strip(), f.strip()) for f in val.split(",")])

    def _resolve_aliases_in_orderby(self, val):
        parts = []
        for p in val.split(","):
            tokens = p.split()
            if tokens:
                f = self.field_aliases.get(tokens[0], tokens[0])
                direction = tokens[1] if len(tokens) > 1 else ""
                parts.append(f"{f} {direction}".strip())
        return ",".join(parts)
