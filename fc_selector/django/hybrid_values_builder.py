"""
Hybrid Values Builder.

Executes a QueryIntent using .values() with $expand support for forward relations
(FK, OneToOne). Returns DTO instances with nested DTOs for expanded relations.

For reverse relations (reverse FK, M2M), the caller should fall back to standard mode.
"""

import logging
from typing import Any

from django.db.models import QuerySet

from fc_selector.core.dtos.base import BaseODataDTO
from fc_selector.core.dtos.utils import get_dto_fields
from fc_selector.core.intent import QueryIntent
from fc_selector.django.utils import get_field_safe, is_forward_relation, resolve_field_alias

logger = logging.getLogger(__name__)


class HybridValuesBuilder:
    """
    Executes a QueryIntent using .values() with $expand support for forward relations.
    Returns DTO instances, not raw dicts.
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
        if intent.expand and intent.expand.has_relations():
            forward_relations, _ = self.classify_relations(
                model, intent.expand, self.expandable_fields
            )

        # Collect fields for .values()
        values_fields = self._collect_values_fields(model, intent, forward_relations)

        # Apply select_related for forward FK joins (required for .values() with __)
        if forward_relations:
            queryset = queryset.select_related(*list(forward_relations.keys()))

        # Apply .values() and pagination
        queryset = queryset.values(*values_fields)
        queryset = _apply_pagination(queryset, intent)

        # Unflatten and build DTOs
        rows = list(queryset)
        return [
            self._unflatten_and_build(row, dto_class, intent, forward_relations)
            for row in rows
        ]

    @staticmethod
    def classify_relations(
        model,
        expand_intent,
        expandable_fields,
    ) -> tuple[dict[str, QueryIntent], list[str]]:
        """Split expand into forward (FK/O2O) and reverse (M2M/reverse FK).

        Returns:
            (forward_dict, reverse_list) where forward_dict maps
            relation_name -> nested QueryIntent.
        """
        forward: dict[str, QueryIntent] = {}
        reverse: list[str] = []

        for relation_name, nested_intent in expand_intent.relations.items():
            if is_forward_relation(model, relation_name):
                forward[relation_name] = nested_intent
            else:
                reverse.append(relation_name)

        return forward, reverse

    def _collect_values_fields(
        self,
        model,
        intent: QueryIntent,
        forward_relations: dict[str, QueryIntent],
    ) -> list[str]:
        """Build field list for .values().

        Example output: ['id', 'title', 'target__id', 'target__name', 'target__code']
        """
        fields: list[str] = []
        pk_name = model._meta.pk.name

        if intent.select and intent.select.has_fields():
            fields.append(pk_name)
            for field_name in intent.select.fields:
                resolved = resolve_field_alias(field_name, self.field_aliases)
                if resolved in forward_relations:
                    continue
                if get_field_safe(model, resolved) and resolved not in fields:
                    fields.append(resolved)
        else:
            for f in model._meta.get_fields():
                if hasattr(f, "get_internal_type") and hasattr(f, "name"):
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
            # field_aliases maps alias -> model_field, e.g. {"heading": "title"}
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

    def _get_expand_config(self, relation_name: str) -> dict | None:
        """Get expand configuration for a relation (same logic as DjangoExecutor)."""
        config = self.expandable_fields.get(relation_name)
        if not config:
            return None

        if isinstance(config, dict):
            return config

        return {"dto_class": config}


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
