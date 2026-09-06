"""
Django Query Executor.

Centralizes the execution of protocol-agnostic QueryIntents on Django QuerySets.
"""

# pylint: disable=protected-access  # Django's _meta is part of the public API for model introspection

import logging
from functools import lru_cache
from typing import Any

from django.db.models import Prefetch, QuerySet

from fc_selector.core import exceptions as core_ex
from fc_selector.core.dtos.utils import get_dto_fields
from fc_selector.core.intent import ExpandIntent, QueryIntent
from fc_selector.core.utils import get_base_field, is_private_field, odata_path_to_django
from fc_selector.django.utils import (
    get_field_safe,
    is_forward_relation,
    resolve_field_alias,
)
from fc_selector.django.visitors import AstToDjangoQVisitor

logger = logging.getLogger(__name__)

# (model, relation_name) pairs already warned about @property fields
_WARNED_PROPERTY_MODELS: set[tuple[type, str]] = set()


def apply_pagination(queryset: QuerySet, intent: QueryIntent) -> QuerySet:
    """Apply limit/offset from an intent to a queryset."""
    if not intent.pagination or not intent.pagination.has_pagination():
        return queryset

    offset = intent.pagination.offset or 0
    limit = intent.pagination.limit

    if limit is not None:
        return queryset[offset : offset + limit]
    if offset > 0:
        return queryset[offset:]

    return queryset


def get_expand_config(expandable_fields: dict[str, Any], relation_name: str) -> dict | None:
    """Normalise an expandable_fields entry to a config dict.

    Entries may be a bare DTO class or a dict with 'dto_class' and optional
    'only_fields'. Returns None when the relation is not configured.
    """
    config = expandable_fields.get(relation_name)
    if not config:
        return None
    return config if isinstance(config, dict) else {"dto_class": config}


class DjangoExecutor:
    """
    Executes a QueryIntent against a Django QuerySet.
    """

    def __init__(
        self,
        field_aliases: dict[str, str] | None = None,
        allowed_fields: list[str] | None = None,
        expandable_fields: dict[str, Any] | None = None,
        non_sortable_fields: list[str] | None = None,
    ):
        """Initialize executor with optional field aliases and allowed fields.

        Args:
            field_aliases: Dict mapping API field names to actual model field names.
                          Allows using e.g. 'client_uuid' in queries when the model
                          field is 'client_id'.
            allowed_fields: List of fields that are allowed to be queried.
                           Used for validation and to skip model field checks for annotated fields.
            expandable_fields: Dict mapping relation names to either:
                              - A DTO class (fields will be introspected)
                              - A dict with 'dto_class' and 'only_fields' keys for explicit control
                              Example:
                                {
                                    "author": AuthorDTO,  # Auto-introspect
                                    "created_by": {
                                        "dto_class": EmployeeDTO,
                                        "only_fields": ["uuid", "user__email"],  # Explicit
                                    }
                                }
            non_sortable_fields: List of fields that cannot be used in $orderby.
                               Used to enforce sortable_fields/non_sortable_fields from the selector.
        """
        self.field_aliases = field_aliases or {}
        self.allowed_fields = allowed_fields
        self.expandable_fields = expandable_fields or {}
        self.non_sortable_fields = set(non_sortable_fields) if non_sortable_fields else None

    def try_hybrid(
        self,
        queryset: QuerySet,
        intent: QueryIntent,
        dto_class: type | None = None,
        *,
        as_dicts: bool = False,
    ) -> list | None:
        """Try hybrid values mode for $expand (forward FK, reverse FK, M2M).

        Uses .values() with __ notation for forward relations, plus extra
        queries for reverse FK (1 per relation) and M2M (2 per relation).
        Unflattens results into nested DTOs (default) or plain dicts.
        Property-based fields are left as UNSET in DTO mode — they are
        simply skipped by the builder.

        Args:
            queryset: Base queryset.
            intent: The QueryIntent.
            dto_class: DTO class for field introspection.
            as_dicts: If True, return plain dicts instead of DTO instances.

        Returns:
            List of DTOs/dicts if hybrid mode applies, None otherwise.
        """
        if not dto_class or not intent or not intent.expand or not intent.expand.has_relations():
            return None

        from fc_selector.django.hybrid_values_builder import HybridValuesBuilder

        forward, reverse_fk, m2m = HybridValuesBuilder.classify_relations(
            queryset.model, intent.expand, self.expandable_fields
        )
        if not forward and not reverse_fk and not m2m:
            return None

        builder = HybridValuesBuilder(
            field_aliases=self.field_aliases,
            expandable_fields=self.expandable_fields,
        )
        queryset = self._apply_filter(queryset, intent)
        queryset = self._apply_ordering(queryset, intent)
        return builder.execute(queryset, intent, dto_class, as_dicts=as_dicts)

    def execute(
        self,
        queryset: QuerySet,
        intent: QueryIntent,
        *,
        use_values: bool = False,
    ) -> QuerySet:
        """
        Apply the full QueryIntent to the queryset.

        Always returns a QuerySet.  For hybrid values mode with $expand,
        call try_hybrid() first.

        Args:
            queryset: Base Django QuerySet
            intent: Query intent with filter, select, expand, ordering, pagination
            use_values: If True, use .values() instead of .only() for much faster
                       dict-based results. Only works when there are no $expand
                       relations (will be ignored if expand is present).

        Returns:
            QuerySet (or ValuesQuerySet if use_values=True and no expand).
        """
        if not intent:
            return queryset

        # Check if values mode is possible (no expand relations)
        can_use_values = use_values and (not intent.expand or not intent.expand.has_relations())

        # 1. Apply Filters
        queryset = self._apply_filter(queryset, intent)

        # 2. Apply Ordering
        queryset = self._apply_ordering(queryset, intent)

        # 3. Apply Select & Expand (Optimization)
        queryset = self._apply_optimizations(queryset, intent, use_values=can_use_values)

        # 4. Apply Pagination
        queryset = apply_pagination(queryset, intent)

        return queryset

    def _apply_filter(self, queryset: QuerySet, intent: QueryIntent) -> QuerySet:
        """Apply filtering using AST visitor."""
        if not intent.filter:
            return queryset
        if not intent.filter.ast:
            raise core_ex.QueryError(f"Invalid filter expression: {intent.filter.expression}")

        try:
            allowed = set(self.allowed_fields) if self.allowed_fields else None
            visitor = AstToDjangoQVisitor(
                queryset.model,
                field_aliases=self.field_aliases,
                allowed_fields=allowed,
            )
            q_object = visitor.visit(intent.filter.ast)
            return queryset.filter(q_object)

        except (ValueError, TypeError) as e:
            logger.debug(
                "Filter error on model=%s filter=%s: %s",
                queryset.model.__name__,
                intent.filter.expression,
                e,
            )
            raise core_ex.QueryError(f"Error applying filter: {e}") from e

    def _apply_ordering(self, queryset: QuerySet, intent: QueryIntent) -> QuerySet:
        """Apply sorting."""
        if not intent.orderby or not intent.orderby.has_ordering():
            return queryset

        order_fields = []
        for field in intent.orderby.fields:
            base_field = get_base_field(odata_path_to_django(field.field))
            if self.non_sortable_fields and base_field in self.non_sortable_fields:
                raise core_ex.InvalidFieldError(
                    field.field,
                    queryset.model.__name__,
                    reason="field is not sortable",
                )

            prefix = "-" if field.direction == "desc" else ""
            django_field = odata_path_to_django(field.field)
            resolved_field = resolve_field_alias(django_field, self.field_aliases)
            order_fields.append(f"{prefix}{resolved_field}")

        return queryset.order_by(*order_fields)

    @staticmethod
    @lru_cache(maxsize=None)
    def _model_has_properties(model) -> list[str]:
        """Detect @property methods on a Django model class that might access related fields.

        Args:
            model: Django model class (not instance)

        Returns:
            List of property names found on the model class.
        """
        properties = []
        for name in dir(model):
            if is_private_field(name) or name == "pk":
                continue
            try:
                # model is already a class, so get attribute directly
                attr = getattr(model, name, None)
                if isinstance(attr, property):
                    properties.append(name)
            except (AttributeError, TypeError):
                pass
        return properties

    def _apply_optimizations(self, queryset: QuerySet, intent: QueryIntent, *, use_values: bool = False) -> QuerySet:
        """Apply select_related, prefetch_related and only() or values().

        Args:
            queryset: The queryset to optimize
            intent: Query intent with select/expand info
            use_values: If True, use .values() instead of .only() for faster dict results.
                       Should only be True when there are no expand relations.
        """
        only_fields: set[str] = set()
        skip_only_for_relations: set[str] = set()

        # 1. Expand (eager loading) - collect related fields for only()
        # Note: use_values should be False if we have expands, but check anyway
        if intent.expand and intent.expand.has_relations():
            queryset, expand_only_fields, skip_only_for_relations = self._apply_expands(queryset, intent.expand)
            only_fields.update(expand_only_fields)
            logger.debug("[OData] expand_only_fields: %s", expand_only_fields)

        # 2. Select (field limiting) - collect main model fields for only()
        if intent.select and intent.select.has_fields():
            queryset, select_only_fields = self._apply_selects(queryset, intent)
            only_fields.update(select_only_fields)
            logger.debug("[OData] select_only_fields: %s", select_only_fields)

        # 3. Apply optimization: .values() for dicts or .only() for model instances
        if only_fields:
            # Filter out fields from relations that have properties
            safe_only_fields = set()
            for field in only_fields:
                relation_prefix = field.split("__")[0] if "__" in field else None
                if relation_prefix and relation_prefix in skip_only_for_relations:
                    continue
                safe_only_fields.add(field)

            if safe_only_fields:
                if use_values:
                    # VALUES MODE: Return dicts instead of model instances (much faster)
                    logger.debug("[OData] using values() with fields: %s", safe_only_fields)
                    queryset = queryset.values(*list(safe_only_fields))
                else:
                    # STANDARD MODE: Return deferred model instances
                    logger.debug("[OData] final only_fields: %s", safe_only_fields)
                    queryset = queryset.only(*list(safe_only_fields))
        elif use_values:
            # No specific fields selected but values mode requested - get all fields
            logger.debug("[OData] using values() with all fields")
            queryset = queryset.values()

        # Debug: log the SQL query
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("[OData] SQL: %s", queryset.query)

        return queryset

    def _apply_expands(self, queryset: QuerySet, expand_intent: ExpandIntent) -> tuple[QuerySet, set[str], set[str]]:
        """Apply select_related and prefetch_related based on ExpandIntent.

        Returns:
            Tuple of (queryset, only_fields, skip_only_relations) where:
            - only_fields contains the related model fields to include in only()
            - skip_only_relations contains relation names where only() should NOT be applied
              (because the model has @property methods that might access other fields)
        """
        select_related = []
        prefetch_related = []
        only_fields: set[str] = set()
        skip_only_relations: set[str] = set()

        model = queryset.model

        for relation_name, nested_intent in expand_intent.relations.items():
            self._validate_expandable_field(relation_name, model)

            is_forward = is_forward_relation(model, relation_name)
            django_relation = odata_path_to_django(relation_name)

            if is_forward:
                select_related.append(django_relation)
                self._process_forward_relation(
                    model,
                    relation_name,
                    django_relation,
                    nested_intent,
                    select_related,
                    only_fields,
                    skip_only_relations,
                )
            else:
                prefetch_obj = self._build_prefetch_object(queryset.model, django_relation, nested_intent)
                if prefetch_obj:
                    prefetch_related.append(prefetch_obj)

        if select_related:
            queryset = queryset.select_related(*select_related)

        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)

        return queryset, only_fields, skip_only_relations

    def _validate_expandable_field(self, relation_name: str, model) -> None:
        """Validate that a relation is in the allowed expandable fields."""
        if self.expandable_fields and relation_name not in self.expandable_fields:
            allowed = list(self.expandable_fields.keys())
            raise core_ex.InvalidFieldError(
                relation_name,
                model.__name__,
                reason=f"field is not expandable. Allowed: {allowed}",
            )

    def _process_forward_relation(
        self,
        model,
        relation_name: str,
        django_relation: str,
        nested_intent: QueryIntent,
        select_related: list[str],
        only_fields: set[str],
        skip_only_relations: set[str],
    ) -> None:
        """Process a forward relation for expand optimization."""
        expand_config = get_expand_config(self.expandable_fields, relation_name)
        field = get_field_safe(model, relation_name)

        if expand_config and field and hasattr(field, "related_model"):
            related_model = field.related_model
            self._handle_related_model_fields(
                related_model,
                relation_name,
                django_relation,
                expand_config,
                select_related,
                only_fields,
                skip_only_relations,
            )

        DjangoExecutor._process_nested_expands(nested_intent, django_relation, select_related)

    def _handle_related_model_fields(
        self,
        related_model,
        relation_name: str,
        django_relation: str,
        expand_config: dict,
        select_related: list[str],
        only_fields: set[str],
        skip_only_relations: set[str],
    ) -> None:
        """Handle field collection for a related model based on expand config."""
        properties = DjangoExecutor._model_has_properties(related_model)

        if properties:
            self._handle_model_with_properties(
                related_model, relation_name, django_relation, properties, select_related, skip_only_relations
            )
        elif "only_fields" in expand_config:
            DjangoExecutor._add_explicit_only_fields(
                expand_config, django_relation, related_model, select_related, only_fields
            )
        else:
            self._add_dto_introspected_fields(
                expand_config, django_relation, related_model, select_related, only_fields
            )

    def _handle_model_with_properties(
        self,
        related_model,
        relation_name: str,
        django_relation: str,
        properties: list[str],
        select_related: list[str],
        skip_only_relations: set[str],
    ) -> None:
        """Handle models that have @property methods."""
        # Configuration advice, not a per-request event: warn once per relation.
        if (related_model, relation_name) not in _WARNED_PROPERTY_MODELS:
            _WARNED_PROPERTY_MODELS.add((related_model, relation_name))
            logger.warning(
                "[OData] ⚠️  Model '%s' has @property methods: %s. "
                "Skipping only() optimization for '%s' to avoid N+1 queries. "
                "Consider adding explicit 'only_fields' config or select_related for nested relations.",
                related_model.__name__,
                properties,
                relation_name,
            )
        skip_only_relations.add(django_relation)
        DjangoExecutor._auto_add_onetoone_relations(related_model, django_relation, select_related)

    @staticmethod
    def _auto_add_onetoone_relations(related_model, django_relation: str, select_related: list[str]) -> None:
        """Auto-detect and add OneToOne relations for models with properties."""
        from django.db.models import OneToOneField

        for field in related_model._meta.fields:
            if isinstance(field, OneToOneField):
                nested_path = f"{django_relation}__{field.name}"
                if nested_path not in select_related:
                    select_related.append(nested_path)
                    logger.debug(
                        "[OData] Auto-added select_related for '%s' (OneToOne on model with properties)",
                        nested_path,
                    )

    @staticmethod
    def _add_explicit_only_fields(
        expand_config: dict,
        django_relation: str,
        related_model,
        select_related: list[str],
        only_fields: set[str],
    ) -> None:
        """Add explicitly configured only_fields to the optimization."""
        for only_field in expand_config["only_fields"]:
            only_fields.add(f"{django_relation}__{only_field}")
            if "__" in only_field:
                nested_relation = only_field.split("__")[0]
                nested_path = f"{django_relation}__{nested_relation}"
                if nested_path not in select_related:
                    select_related.append(nested_path)

        only_fields.add(f"{django_relation}__{related_model._meta.pk.name}")

    def _add_dto_introspected_fields(
        self,
        expand_config: dict,
        django_relation: str,
        related_model,
        select_related: list[str],
        only_fields: set[str],
    ) -> None:
        """Add fields introspected from DTO class."""
        dto_class = expand_config.get("dto_class")
        dto_fields = get_dto_fields(dto_class) if dto_class else None

        if dto_fields:
            for dto_field in dto_fields:
                model_field = DjangoExecutor._resolve_dto_field_to_model(related_model, dto_field)
                if model_field:
                    only_fields.add(f"{django_relation}__{model_field}")
                    if "__" in model_field:
                        nested_relation = model_field.split("__")[0]
                        nested_path = f"{django_relation}__{nested_relation}"
                        if nested_path not in select_related:
                            select_related.append(nested_path)

            only_fields.add(f"{django_relation}__{related_model._meta.pk.name}")

    @staticmethod
    def _process_nested_expands(nested_intent: QueryIntent, django_relation: str, select_related: list[str]) -> None:
        """Process nested expand relations for deep select_related."""
        if nested_intent.expand:
            for nested_rel in nested_intent.expand.relations:
                select_related.append(f"{django_relation}__{nested_rel.replace('.', '__')}")

    @staticmethod
    def _resolve_dto_field_to_model(model, dto_field: str) -> str | None:
        """Resolve a DTO field name to the actual model field name."""
        # Direct field match
        if get_field_safe(model, dto_field):
            return dto_field

        # Handle common patterns like 'email' -> 'user__email'
        # Check if field exists on a OneToOne related model
        from django.db.models import OneToOneField

        for f in model._meta.fields:
            if isinstance(f, OneToOneField) and hasattr(f, "related_model"):
                nested_field = get_field_safe(f.related_model, dto_field)
                if nested_field:
                    return f"{f.name}__{dto_field}"

        return None

    def _build_prefetch_object(self, root_model, relation_name: str, nested_intent: QueryIntent):
        """Build a Prefetch object with nested optimizations."""
        # Handle reverse relation lookup via model meta if possible
        field = get_field_safe(root_model, relation_name)
        if field and hasattr(field, "related_model"):
            related_model = field.related_model
        else:
            # Try related objects for reverse FKs
            related_model = None
            for rel in root_model._meta.related_objects:
                if rel.get_accessor_name() == relation_name:
                    related_model = rel.related_model
                    break

        if not related_model:
            # If we can't find the model, we can't optimize nested queries safely
            # Just return the string name for basic prefetch
            return relation_name

        nested_queryset = related_model.objects.all()

        # Recursive execution
        nested_executor = DjangoExecutor(
            field_aliases=self.field_aliases,
            allowed_fields=self.allowed_fields,
            expandable_fields=self.expandable_fields,
        )
        optimized_nested_qs = nested_executor.execute(nested_queryset, nested_intent)

        return Prefetch(relation_name, queryset=optimized_nested_qs)

    def _apply_selects(self, queryset: QuerySet, intent: QueryIntent) -> tuple[QuerySet, set[str]]:
        """Collect fields for only() based on $select.

        Returns:
            Tuple of (queryset, only_fields) where only_fields contains the
            main model fields to include in the only() call.
        """
        only_fields: set[str] = set()

        if not intent.select or not intent.select.fields:
            return queryset, only_fields

        model = queryset.model

        # Always include PK
        only_fields.add(model._meta.pk.name)

        # Add requested fields (resolve aliases first to handle e.g. client_uuid -> client_id)
        for field_name in intent.select.fields:
            resolved_field = resolve_field_alias(field_name, self.field_aliases)
            if get_field_safe(model, resolved_field):
                only_fields.add(resolved_field)

        # Add FKs for expanded relations
        if intent.expand:
            for relation_name in intent.expand.relations.keys():
                field = get_field_safe(model, relation_name)
                if field and hasattr(field, "attname"):
                    only_fields.add(field.attname)

        return queryset, only_fields
