"""
Hybrid Values Builder.

Executes a QueryIntent using .values() with $expand support for forward relations
(FK, OneToOne), reverse FK, and M2M relations. Returns DTO instances with nested DTOs.

Strategy:
- Forward relations: JOIN via select_related + .values('rel__field')
- Reverse FK: 1 extra query per relation, filtered by parent PKs
- M2M: 2 extra queries per relation (through table + child table)
- Recursive nesting supported up to MAX_DTO_RECURSION_DEPTH levels
"""

import logging
from collections import defaultdict
from typing import Any

from django.db.models import QuerySet

from fc_selector.core.dtos.base import UNSET, MAX_DTO_RECURSION_DEPTH, BaseODataDTO
from fc_selector.core.dtos.utils import get_dto_fields
from fc_selector.core.intent import QueryIntent
from fc_selector.core.utils import odata_path_to_django
from fc_selector.django.utils import (
    get_field_safe,
    get_m2m_info,
    get_reverse_fk_info,
    is_forward_relation,
    is_m2m_relation,
    resolve_field_alias,
)
from fc_selector.django.visitors import AstToDjangoQVisitor

logger = logging.getLogger(__name__)


class HybridValuesBuilder:
    """
    Executes a QueryIntent using .values() with $expand support for forward,
    reverse FK, and M2M relations. Returns DTO instances, not raw dicts.
    """

    def __init__(
        self,
        field_aliases: dict[str, str] | None = None,
        expandable_fields: dict[str, Any] | None = None,
    ):
        self.field_aliases = field_aliases or {}
        self.expandable_fields = expandable_fields or {}

    def execute(
        self,
        queryset: QuerySet,
        intent: QueryIntent,
        dto_class: type[BaseODataDTO],
    ) -> list[BaseODataDTO]:
        """Full pipeline: classify -> collect fields -> query -> unflatten -> DTO."""
        model = queryset.model

        forward_relations: dict[str, QueryIntent] = {}
        reverse_fk_relations: dict[str, QueryIntent] = {}
        m2m_relations: dict[str, QueryIntent] = {}

        if intent.expand and intent.expand.has_relations():
            forward_relations, reverse_fk_relations, m2m_relations = (
                self.classify_relations(
                    model, intent.expand, self.expandable_fields
                )
            )

        # Phase 1: existing .values() for root + forward (unchanged)
        values_fields = self._collect_values_fields(model, intent, forward_relations)

        if forward_relations:
            queryset = queryset.select_related(*list(forward_relations.keys()))

        queryset = queryset.values(*values_fields)
        queryset = _apply_pagination(queryset, intent)

        rows = list(queryset)
        parent_dtos = [
            self._unflatten_and_build(row, dto_class, intent, forward_relations)
            for row in rows
        ]

        # Phase 2: attach reverse FK children
        if reverse_fk_relations and parent_dtos:
            self._attach_reverse_fk_children(
                model, parent_dtos, reverse_fk_relations
            )

        # Phase 3: attach M2M children
        if m2m_relations and parent_dtos:
            self._attach_m2m_children(model, parent_dtos, m2m_relations)

        return parent_dtos

    @staticmethod
    def classify_relations(
        model,
        expand_intent,
        expandable_fields,
    ) -> tuple[dict[str, QueryIntent], dict[str, QueryIntent], dict[str, QueryIntent]]:
        """Split expand into forward (FK/O2O), reverse FK, and M2M.

        Returns:
            (forward_dict, reverse_fk_dict, m2m_dict) where each maps
            relation_name -> nested QueryIntent.
        """
        forward: dict[str, QueryIntent] = {}
        reverse_fk: dict[str, QueryIntent] = {}
        m2m: dict[str, QueryIntent] = {}

        for relation_name, nested_intent in expand_intent.relations.items():
            if is_forward_relation(model, relation_name):
                forward[relation_name] = nested_intent
            elif is_m2m_relation(model, relation_name):
                m2m[relation_name] = nested_intent
            elif get_reverse_fk_info(model, relation_name):
                reverse_fk[relation_name] = nested_intent
            else:
                logger.warning(
                    "Relation '%s' on %s is not a recognized forward, reverse FK, "
                    "or M2M relation — ignoring.",
                    relation_name,
                    model.__name__,
                )

        return forward, reverse_fk, m2m

    # ── Forward relation helpers (unchanged) ────────────────────────

    def _collect_values_fields(
        self,
        model,
        intent: QueryIntent,
        forward_relations: dict[str, QueryIntent],
        dto_class: type[BaseODataDTO] | None = None,
    ) -> list[str]:
        """Build field list for .values().

        Args:
            model: Django model to query.
            intent: QueryIntent with select/expand info.
            forward_relations: Forward relations to include via __ notation.
            dto_class: Optional DTO class for field introspection (used for
                child queries where DTO fields guide the field list).

        Example output: ['id', 'title', 'target__id', 'target__name', 'target__code']
        """
        fields: list[str] = []
        pk_name = model._meta.pk.name
        fields.append(pk_name)

        if intent.select and intent.select.has_fields():
            for field_name in intent.select.fields:
                resolved = resolve_field_alias(field_name, self.field_aliases)
                if resolved in forward_relations:
                    continue
                if get_field_safe(model, resolved) and resolved not in fields:
                    fields.append(resolved)
        elif dto_class:
            all_dto_fields = get_dto_fields(dto_class)
            relationship_info = (
                dto_class._get_relationship_info()
                if hasattr(dto_class, "_get_relationship_info")
                else {}
            )
            for f in all_dto_fields:
                if f in relationship_info:
                    continue
                if get_field_safe(model, f) and f not in fields:
                    fields.append(f)
        else:
            for f in model._meta.get_fields():
                if not hasattr(f, "name"):
                    continue
                # Skip reverse relations (concrete=False) and M2M fields
                # implicit joins cause row multiplication
                if not getattr(f, "concrete", True) or getattr(f, "many_to_many", False):
                    continue
                if f.name not in fields:
                    fields.append(f.name)

        # Add FK attname (e.g. target_id) for each forward relation
        for relation_name in forward_relations:
            field_obj = get_field_safe(model, relation_name)
            if field_obj and hasattr(field_obj, "attname"):
                attname = field_obj.attname
                if attname not in fields:
                    fields.append(attname)

        # Add related fields via __ notation
        for relation_name, nested_intent in forward_relations.items():
            rel_fields = self._collect_related_fields(model, relation_name, nested_intent)
            fields.extend(rel_fields)

        return fields

    def _collect_related_fields(
        self,
        model,
        relation_name: str,
        nested_intent: QueryIntent,
    ) -> list[str]:
        """Collect 'relation__field' entries for a forward relation."""
        field_obj = get_field_safe(model, relation_name)
        if not field_obj or not hasattr(field_obj, "related_model"):
            return []

        related_model = field_obj.related_model
        expand_config = self._get_expand_config(relation_name)
        dto_class = expand_config.get("dto_class") if expand_config else None

        related_field_names: list[str] = []

        if nested_intent.select and nested_intent.select.has_fields():
            related_field_names = list(nested_intent.select.fields)
        elif dto_class:
            all_dto_fields = get_dto_fields(dto_class)
            relationship_info = (
                dto_class._get_relationship_info()
                if hasattr(dto_class, "_get_relationship_info")
                else {}
            )
            related_field_names = [f for f in all_dto_fields if f not in relationship_info]
        else:
            related_field_names = [
                f.name
                for f in related_model._meta.get_fields()
                if hasattr(f, "get_internal_type") and hasattr(f, "name")
            ]

        pk_name = related_model._meta.pk.name
        result = [f"{relation_name}__{pk_name}"]

        for fname in related_field_names:
            if get_field_safe(related_model, fname):
                prefixed = f"{relation_name}__{fname}"
                if prefixed not in result:
                    result.append(prefixed)

        return result

    def _unflatten_and_build(
        self,
        row: dict,
        dto_class: type[BaseODataDTO],
        intent: QueryIntent,
        forward_relations: dict[str, QueryIntent],
    ) -> BaseODataDTO:
        """Flat dict -> nested dict -> DTO(**dict) with nested DTOs."""
        data: dict[str, Any] = {}

        dto_fields = dto_class._get_dto_fields()
        relationship_info = dto_class._get_relationship_info()

        if intent.select and intent.select.has_fields():
            selected = set(intent.select.fields)
            # Resolve alias API names to model/DTO field names
            mapped_selected = {self.field_aliases.get(s, s) for s in selected}
            fields_to_populate = (dto_fields & mapped_selected) | (
                dto_fields & set(forward_relations.keys())
            )
        else:
            fields_to_populate = dto_fields

        # Populate regular fields from the flat row
        for field_name in fields_to_populate:
            if field_name in forward_relations:
                continue
            if field_name in relationship_info:
                continue

            if field_name in row:
                data[field_name] = row[field_name]
            else:
                # DTO field might be an alias for a model field
                model_field_name = self.field_aliases.get(field_name, field_name)
                if model_field_name in row:
                    data[field_name] = row[model_field_name]

        # Build nested DTOs for forward relations
        for relation_name, nested_intent in forward_relations.items():
            expand_config = self._get_expand_config(relation_name)
            nested_dto_class = expand_config.get("dto_class") if expand_config else None

            if not nested_dto_class:
                data[relation_name] = None
                continue

            data[relation_name] = self._extract_nested(
                row, relation_name, nested_dto_class, nested_intent
            )

        return dto_class(**data)

    @staticmethod
    def _extract_nested(
        row: dict,
        relation_name: str,
        dto_class: type[BaseODataDTO],
        nested_intent: QueryIntent,
    ) -> BaseODataDTO | None:
        """Extract nested DTO from flat row using __ prefix."""
        prefix = f"{relation_name}__"

        nested_raw: dict[str, Any] = {}
        for key, value in row.items():
            if key.startswith(prefix):
                nested_raw[key[len(prefix):]] = value

        if not nested_raw:
            return None

        # NULL FK: all values are None
        if all(v is None for v in nested_raw.values()):
            return None

        dto_fields = set(get_dto_fields(dto_class))
        relationship_info = (
            dto_class._get_relationship_info()
            if hasattr(dto_class, "_get_relationship_info")
            else {}
        )

        selected_nested = None
        if nested_intent.select and nested_intent.select.has_fields():
            selected_nested = set(nested_intent.select.fields)

        nested_data: dict[str, Any] = {}
        for field_name in dto_fields:
            if field_name in relationship_info:
                continue

            if selected_nested is not None and field_name not in selected_nested:
                continue

            if field_name in nested_raw:
                nested_data[field_name] = nested_raw[field_name]

        return dto_class(**nested_data)

    # ── Reverse FK support ──────────────────────────────────────────

    def _attach_reverse_fk_children(
        self,
        model,
        parent_dtos: list[BaseODataDTO],
        relations: dict[str, QueryIntent],
        *,
        _depth: int = 0,
    ) -> None:
        """Fetch and attach reverse FK children via 1 query per relation."""
        if _depth >= MAX_DTO_RECURSION_DEPTH:
            return

        pk_name = model._meta.pk.name
        parent_pks = [
            pk for dto in parent_dtos
            if (pk := getattr(dto, pk_name)) is not UNSET
        ]
        if not parent_pks:
            return

        for relation_name, nested_intent in relations.items():
            info = get_reverse_fk_info(model, relation_name)
            if not info:
                # Set empty list on all parents
                for dto in parent_dtos:
                    setattr(dto, relation_name, [])
                continue

            child_model, fk_attname = info
            expand_config = self._get_expand_config(relation_name)
            child_dto_class = expand_config.get("dto_class") if expand_config else None

            if not child_dto_class:
                for dto in parent_dtos:
                    setattr(dto, relation_name, [])
                continue

            # Classify nested expands for the child
            child_forward: dict[str, QueryIntent] = {}
            child_reverse_fk: dict[str, QueryIntent] = {}
            child_m2m: dict[str, QueryIntent] = {}
            if nested_intent.expand and nested_intent.expand.has_relations():
                child_expandable = self._get_nested_expandable_fields(relation_name)
                child_forward, child_reverse_fk, child_m2m = self.classify_relations(
                    child_model, nested_intent.expand, child_expandable
                )

            # Build child .values() fields
            child_fields = self._collect_values_fields(
                child_model, nested_intent, child_forward, dto_class=child_dto_class
            )
            # Always include the FK attname for grouping
            if fk_attname not in child_fields:
                child_fields.append(fk_attname)

            # Build child queryset
            child_qs = child_model.objects.filter(**{f"{fk_attname}__in": parent_pks})

            # Apply nested $filter
            if nested_intent.filter and nested_intent.filter.has_filter():
                child_qs = self._apply_child_filter(child_qs, nested_intent)

            # Apply nested $orderby
            if nested_intent.orderby and nested_intent.orderby.has_ordering():
                child_qs = self._apply_child_ordering(child_qs, nested_intent)

            # Apply select_related for forward expands within child
            if child_forward:
                child_qs = child_qs.select_related(*list(child_forward.keys()))

            child_qs = child_qs.values(*child_fields)
            child_qs = _apply_pagination(child_qs, nested_intent)
            child_rows = list(child_qs)

            # Group by parent FK and build child DTOs
            grouped: dict[Any, list[BaseODataDTO]] = defaultdict(list)
            for row in child_rows:
                parent_pk = row[fk_attname]
                child_dto = self._build_child_dto(
                    row, child_dto_class, nested_intent, child_forward, fk_attname
                )
                grouped[parent_pk].append(child_dto)

            # Attach to parent DTOs
            for dto in parent_dtos:
                pk = getattr(dto, pk_name)
                setattr(dto, relation_name, grouped.get(pk, []))

            # Recursive: handle nested reverse FK / M2M on child DTOs
            all_child_dtos = [dto for dtos in grouped.values() for dto in dtos]
            self._recurse_into_children(
                child_model, all_child_dtos, child_reverse_fk, child_m2m,
                relation_name, _depth,
            )

    # ── M2M support ─────────────────────────────────────────────────

    def _attach_m2m_children(
        self,
        model,
        parent_dtos: list[BaseODataDTO],
        relations: dict[str, QueryIntent],
        *,
        _depth: int = 0,
    ) -> None:
        """Fetch and attach M2M children via 2 queries per relation."""
        if _depth >= MAX_DTO_RECURSION_DEPTH:
            return

        pk_name = model._meta.pk.name
        parent_pks = [
            pk for dto in parent_dtos
            if (pk := getattr(dto, pk_name)) is not UNSET
        ]
        if not parent_pks:
            return

        for relation_name, nested_intent in relations.items():
            info = get_m2m_info(model, relation_name)
            if not info:
                for dto in parent_dtos:
                    setattr(dto, relation_name, [])
                continue

            through_model = info["through_model"]
            related_model = info["related_model"]
            source_fk = info["source_fk_attname"]
            target_fk = info["target_fk_attname"]

            expand_config = self._get_expand_config(relation_name)
            child_dto_class = expand_config.get("dto_class") if expand_config else None

            if not child_dto_class:
                for dto in parent_dtos:
                    setattr(dto, relation_name, [])
                continue

            # Query 1: through table -> parent-to-child PK mapping
            through_rows = list(
                through_model.objects.filter(
                    **{f"{source_fk}__in": parent_pks}
                ).values(source_fk, target_fk)
            )

            # Build mapping: parent_pk -> [child_pk, ...]
            parent_to_child_pks: dict[Any, list[Any]] = defaultdict(list)
            all_child_pks: set[Any] = set()
            for row in through_rows:
                parent_pk = row[source_fk]
                child_pk = row[target_fk]
                parent_to_child_pks[parent_pk].append(child_pk)
                all_child_pks.add(child_pk)

            if not all_child_pks:
                for dto in parent_dtos:
                    setattr(dto, relation_name, [])
                continue

            # Classify nested expands for the child
            child_forward: dict[str, QueryIntent] = {}
            child_reverse_fk: dict[str, QueryIntent] = {}
            child_m2m: dict[str, QueryIntent] = {}
            if nested_intent.expand and nested_intent.expand.has_relations():
                child_expandable = self._get_nested_expandable_fields(relation_name)
                child_forward, child_reverse_fk, child_m2m = self.classify_relations(
                    related_model, nested_intent.expand, child_expandable
                )

            # Build child .values() fields
            child_fields = self._collect_values_fields(
                related_model, nested_intent, child_forward, dto_class=child_dto_class
            )

            # Query 2: child data
            child_qs = related_model.objects.filter(pk__in=all_child_pks)

            # Apply nested $filter
            if nested_intent.filter and nested_intent.filter.has_filter():
                child_qs = self._apply_child_filter(child_qs, nested_intent)

            # Apply nested $orderby
            if nested_intent.orderby and nested_intent.orderby.has_ordering():
                child_qs = self._apply_child_ordering(child_qs, nested_intent)

            # Apply select_related for forward expands within child
            if child_forward:
                child_qs = child_qs.select_related(*list(child_forward.keys()))

            child_qs = child_qs.values(*child_fields)
            child_qs = _apply_pagination(child_qs, nested_intent)
            child_rows = list(child_qs)

            # Build child DTOs indexed by PK.
            # PK is always fetched by _collect_values_fields for indexing,
            # even if not in $select — it won't appear in the DTO itself.
            child_pk_name = related_model._meta.pk.name
            child_dto_by_pk: dict[Any, BaseODataDTO] = {}
            for row in child_rows:
                child_dto = self._build_child_dto(
                    row, child_dto_class, nested_intent, child_forward
                )
                child_dto_by_pk[row[child_pk_name]] = child_dto

            # Attach to parents using through mapping
            for dto in parent_dtos:
                pk = getattr(dto, pk_name)
                child_pks = parent_to_child_pks.get(pk, [])
                setattr(
                    dto,
                    relation_name,
                    [child_dto_by_pk[cpk] for cpk in child_pks if cpk in child_dto_by_pk],
                )

            # Recursive: handle nested reverse FK / M2M on child DTOs
            all_child_dtos = list(child_dto_by_pk.values())
            self._recurse_into_children(
                related_model, all_child_dtos, child_reverse_fk, child_m2m,
                relation_name, _depth,
            )

    # ── Shared helpers ──────────────────────────────────────────────

    def _recurse_into_children(
        self,
        child_model,
        child_dtos: list[BaseODataDTO],
        child_reverse_fk: dict[str, QueryIntent],
        child_m2m: dict[str, QueryIntent],
        relation_name: str,
        depth: int,
    ) -> None:
        """Recursively attach nested reverse FK / M2M children."""
        if not child_dtos or (not child_reverse_fk and not child_m2m):
            return

        child_expandable = self._get_nested_expandable_fields(relation_name)
        child_builder = HybridValuesBuilder(
            field_aliases=self.field_aliases,
            expandable_fields=child_expandable,
        )
        if child_reverse_fk:
            child_builder._attach_reverse_fk_children(
                child_model, child_dtos, child_reverse_fk, _depth=depth + 1
            )
        if child_m2m:
            child_builder._attach_m2m_children(
                child_model, child_dtos, child_m2m, _depth=depth + 1
            )

    def _build_child_dto(
        self,
        row: dict,
        dto_class: type[BaseODataDTO],
        nested_intent: QueryIntent,
        child_forward: dict[str, QueryIntent],
        exclude_field: str | None = None,
    ) -> BaseODataDTO:
        """Build a child DTO from a flat values row.

        Reuses _extract_nested for forward relations within the child.
        """
        data: dict[str, Any] = {}
        dto_fields = dto_class._get_dto_fields()
        relationship_info = dto_class._get_relationship_info()

        if nested_intent.select and nested_intent.select.has_fields():
            selected = set(nested_intent.select.fields)
            mapped_selected = {self.field_aliases.get(s, s) for s in selected}
            fields_to_populate = (dto_fields & mapped_selected) | (
                dto_fields & set(child_forward.keys())
            )
        else:
            fields_to_populate = dto_fields

        for field_name in fields_to_populate:
            if field_name in child_forward:
                continue
            if field_name in relationship_info:
                continue
            if field_name == exclude_field:
                continue

            if field_name in row:
                data[field_name] = row[field_name]
            else:
                model_field_name = self.field_aliases.get(field_name, field_name)
                if model_field_name in row:
                    data[field_name] = row[model_field_name]

        # Build nested DTOs for forward relations within child
        for rel_name, rel_intent in child_forward.items():
            expand_config = self._get_expand_config_nested(rel_name)
            nested_dto_class = expand_config.get("dto_class") if expand_config else None

            if not nested_dto_class:
                data[rel_name] = None
                continue

            data[rel_name] = self._extract_nested(
                row, rel_name, nested_dto_class, rel_intent
            )

        return dto_class(**data)

    def _get_expand_config(self, relation_name: str) -> dict | None:
        """Get expand configuration for a relation (same logic as DjangoExecutor)."""
        config = self.expandable_fields.get(relation_name)
        if not config:
            return None

        if isinstance(config, dict):
            return config

        return {"dto_class": config}

    def _get_expand_config_nested(self, relation_name: str) -> dict | None:
        """Get expand config for a nested relation within a child.

        Unlike _get_expand_config, this searches nested expandable_fields
        configs. Needed because _build_child_dto runs on the parent builder
        (with parent-level expandable_fields), not on a child builder.
        """
        # First try direct lookup
        config = self.expandable_fields.get(relation_name)
        if config:
            if isinstance(config, dict):
                return config
            return {"dto_class": config}

        # Search in nested expandable_fields of parent configs
        for _, parent_config in self.expandable_fields.items():
            if isinstance(parent_config, dict):
                nested = parent_config.get("expandable_fields", {})
                if relation_name in nested:
                    child_config = nested[relation_name]
                    if isinstance(child_config, dict):
                        return child_config
                    return {"dto_class": child_config}

        return None

    def _get_nested_expandable_fields(self, relation_name: str) -> dict:
        """Get the expandable_fields config for a child relation's own expands."""
        config = self.expandable_fields.get(relation_name)
        if isinstance(config, dict):
            return config.get("expandable_fields", {})
        return {}

    @staticmethod
    def _apply_child_filter(child_qs: QuerySet, nested_intent: QueryIntent) -> QuerySet:
        """Apply filter from nested intent to child queryset."""
        visitor = AstToDjangoQVisitor(child_qs.model)
        q_object = visitor.visit(nested_intent.filter.ast)
        return child_qs.filter(q_object)

    @staticmethod
    def _apply_child_ordering(child_qs: QuerySet, nested_intent: QueryIntent) -> QuerySet:
        """Apply ordering from nested intent to child queryset."""
        order_fields = []
        for f in nested_intent.orderby.fields:
            prefix = "-" if f.direction == "desc" else ""
            django_field = odata_path_to_django(f.field)
            order_fields.append(f"{prefix}{django_field}")
        return child_qs.order_by(*order_fields)


def _apply_pagination(queryset: QuerySet, intent: QueryIntent) -> QuerySet:
    """Apply limit/offset to the queryset."""
    if not intent.pagination or not intent.pagination.has_pagination():
        return queryset

    offset = intent.pagination.offset or 0
    limit = intent.pagination.limit

    if limit is not None:
        return queryset[offset: offset + limit]
    if offset > 0:
        return queryset[offset:]

    return queryset
