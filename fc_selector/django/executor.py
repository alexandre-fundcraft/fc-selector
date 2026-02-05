"""
Django Query Executor.

Centralizes the execution of protocol-agnostic QueryIntents on Django QuerySets.
"""

import logging
from typing import Any

from django.db.models import Prefetch, QuerySet

from fc_selector.core import exceptions as core_ex
from fc_selector.core.dtos.utils import get_dto_fields
from fc_selector.core.intent import ExpandIntent, QueryIntent
from fc_selector.core.utils import is_private_field, odata_path_to_django
from fc_selector.django.utils import (
    get_field_safe,
    is_forward_relation,
    resolve_field_alias,
)
from fc_selector.django.visitors import AstToDjangoQVisitor

logger = logging.getLogger(__name__)


class DjangoExecutor:
    """
    Executes a QueryIntent against a Django QuerySet.
    """

    def __init__(
        self,
        field_aliases: dict[str, str] | None = None,
        allowed_fields: list[str] | None = None,
        expandable_fields: dict[str, Any] | None = None,
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
        """
        self.field_aliases = field_aliases or {}
        self.allowed_fields = allowed_fields
        self.expandable_fields = expandable_fields or {}

    def execute(
        self, queryset: QuerySet, intent: QueryIntent, *, use_values: bool = False
    ) -> QuerySet:
        """
        Apply the full QueryIntent to the queryset.

        Args:
            queryset: Base Django QuerySet
            intent: Query intent with filter, select, expand, ordering, pagination
            use_values: If True, use .values() instead of .only() for much faster
                       dict-based results. Only works when there are no $expand
                       relations (will be ignored if expand is present).

        Returns:
            QuerySet (or ValuesQuerySet if use_values=True and no expand)
        """
        if not intent:
            return queryset

        # Check if values mode is possible (no expand relations)
        can_use_values = use_values and (
            not intent.expand or not intent.expand.has_relations()
        )

        # 1. Apply Filters
        queryset = self._apply_filter(queryset, intent)

        # 2. Apply Ordering
        queryset = self._apply_ordering(queryset, intent)

        # 3. Apply Select & Expand (Optimization)
        queryset = self._apply_optimizations(queryset, intent, use_values=can_use_values)

        # 4. Apply Pagination
        queryset = self._apply_pagination(queryset, intent)

        return queryset

    def _apply_filter(self, queryset: QuerySet, intent: QueryIntent) -> QuerySet:
        """Apply filtering using AST visitor."""
        if not intent.filter or not intent.filter.ast:
            return queryset

        try:
            visitor = AstToDjangoQVisitor(
                queryset.model,
                field_aliases=self.field_aliases,
                allowed_fields=self.allowed_fields,
            )
            q_object = visitor.visit(intent.filter.ast)
            return queryset.filter(q_object)

        except (core_ex.SelectorError, core_ex.QueryError, ValueError, TypeError) as e:
            if isinstance(e, core_ex.SelectorError):
                raise
            raise core_ex.QueryError(f"Error applying filter: {e}") from e

    def _apply_ordering(self, queryset: QuerySet, intent: QueryIntent) -> QuerySet:
        """Apply sorting."""
        if not intent.orderby or not intent.orderby.has_ordering():
            return queryset

        order_fields = []
        for field in intent.orderby.fields:
            prefix = "-" if field.direction == "desc" else ""
            django_field = odata_path_to_django(field.field)
            # Resolve alias to actual model field
            resolved_field = resolve_field_alias(django_field, self.field_aliases)
            order_fields.append(f"{prefix}{resolved_field}")

        return queryset.order_by(*order_fields)

    def _apply_pagination(self, queryset: QuerySet, intent: QueryIntent) -> QuerySet:
        """Apply limit/offset."""
        if not intent.pagination or not intent.pagination.has_pagination():
            return queryset

        offset = intent.pagination.offset or 0
        limit = intent.pagination.limit

        if limit is not None:
            return queryset[offset : offset + limit]
        elif offset > 0:
            return queryset[offset:]

        return queryset

    def _model_has_properties(self, model) -> list[str]:
        """Detect @property methods on a Django model class that might access related fields.

        Args:
            model: Django model class (not instance)

        Returns:
            List of property names found on the model class.
        """
        properties = []
        for name in dir(model):
            if is_private_field(name):
                continue
            try:
                # model is already a class, so get attribute directly
                attr = getattr(model, name, None)
                if isinstance(attr, property):
                    properties.append(name)
            except (AttributeError, TypeError):
                pass
        return properties

    def _apply_optimizations(
        self, queryset: QuerySet, intent: QueryIntent, *, use_values: bool = False
    ) -> QuerySet:
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
            queryset, expand_only_fields, skip_only_for_relations = self._apply_expands(
                queryset, intent.expand
            )
            only_fields.update(expand_only_fields)
            logger.debug(f"[OData] expand_only_fields: {expand_only_fields}")

        # 2. Select (field limiting) - collect main model fields for only()
        if intent.select and intent.select.has_fields():
            queryset, select_only_fields = self._apply_selects(queryset, intent)
            only_fields.update(select_only_fields)
            logger.debug(f"[OData] select_only_fields: {select_only_fields}")

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
                    logger.debug(f"[OData] using values() with fields: {safe_only_fields}")
                    queryset = queryset.values(*list(safe_only_fields))
                else:
                    # STANDARD MODE: Return deferred model instances
                    logger.debug(f"[OData] final only_fields: {safe_only_fields}")
                    queryset = queryset.only(*list(safe_only_fields))
        elif use_values:
            # No specific fields selected but values mode requested - get all fields
            logger.debug("[OData] using values() with all fields")
            queryset = queryset.values()

        # Debug: log the SQL query
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"[OData] SQL: {queryset.query}")

        return queryset

    def _apply_expands(
        self, queryset: QuerySet, expand_intent: ExpandIntent
    ) -> tuple[QuerySet, set[str], set[str]]:
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
            # Security: Validate against allowed expandable fields if configured
            if self.expandable_fields and relation_name not in self.expandable_fields:
                allowed = list(self.expandable_fields.keys())
                raise core_ex.InvalidFieldError(
                    relation_name,
                    model.__name__,
                    reason=f"field is not expandable. Allowed: {allowed}",
                )

            is_forward = is_forward_relation(model, relation_name)
            django_relation = odata_path_to_django(relation_name)

            if is_forward:
                select_related.append(django_relation)

                # Get configuration for this relation
                expand_config = self._get_expand_config(relation_name)
                field = get_field_safe(model, relation_name)

                if expand_config and field and hasattr(field, "related_model"):
                    related_model = field.related_model

                    # Check if the related model has @property methods
                    properties = self._model_has_properties(related_model)
                    if properties:
                        logger.warning(
                            f"[OData] ⚠️  Model '{related_model.__name__}' has @property methods: {properties}. "
                            f"Skipping only() optimization for '{relation_name}' to avoid N+1 queries. "
                            f"Consider adding explicit 'only_fields' config or select_related for nested relations."
                        )
                        skip_only_relations.add(django_relation)

                        # Auto-detect OneToOne relations that need select_related
                        # (e.g., Author.user for accessing email/name properties)
                        from django.db.models import OneToOneField

                        for f in related_model._meta.fields:
                            if isinstance(f, OneToOneField):
                                nested_path = f"{django_relation}__{f.name}"
                                if nested_path not in select_related:
                                    select_related.append(nested_path)
                                    logger.debug(
                                        f"[OData] Auto-added select_related for '{nested_path}' "
                                        f"(OneToOne on model with properties)"
                                    )

                    # If explicit only_fields are provided, use them directly
                    elif "only_fields" in expand_config:
                        for only_field in expand_config["only_fields"]:
                            only_fields.add(f"{django_relation}__{only_field}")
                            # Auto-add select_related for nested relations (e.g., user__email -> user)
                            if "__" in only_field:
                                nested_relation = only_field.split("__")[0]
                                nested_path = f"{django_relation}__{nested_relation}"
                                if nested_path not in select_related:
                                    select_related.append(nested_path)
                        # Always include PK
                        only_fields.add(f"{django_relation}__{related_model._meta.pk.name}")
                    else:
                        # Fall back to DTO introspection
                        dto_fields = get_dto_fields(expand_config.get("dto_class"))
                        if dto_fields:
                            for dto_field in dto_fields:
                                model_field = self._resolve_dto_field_to_model(related_model, dto_field)
                                if model_field:
                                    only_fields.add(f"{django_relation}__{model_field}")
                                    # Auto-add select_related for nested relations
                                    if "__" in model_field:
                                        nested_relation = model_field.split("__")[0]
                                        nested_path = f"{django_relation}__{nested_relation}"
                                        if nested_path not in select_related:
                                            select_related.append(nested_path)
                            only_fields.add(f"{django_relation}__{related_model._meta.pk.name}")

                # Check for nested expands (deep select_related)
                if nested_intent.expand:
                    for nested_rel in nested_intent.expand.get_relation_names():
                        select_related.append(f"{django_relation}__{nested_rel.replace('.', '__')}")
            else:
                prefetch_obj = self._build_prefetch_object(queryset.model, django_relation, nested_intent)
                if prefetch_obj:
                    prefetch_related.append(prefetch_obj)

        if select_related:
            queryset = queryset.select_related(*select_related)

        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)

        return queryset, only_fields, skip_only_relations

    def _get_expand_config(self, relation_name: str) -> dict | None:
        """Get expand configuration for a relation.

        Returns:
            Dict with 'dto_class' and optionally 'only_fields', or None if not configured.
        """
        config = self.expandable_fields.get(relation_name)
        if not config:
            return None

        # If it's a dict, return as-is
        if isinstance(config, dict):
            return config

        # If it's a class (DTO), wrap it
        return {"dto_class": config}


    def _resolve_dto_field_to_model(self, model, dto_field: str) -> str | None:
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

