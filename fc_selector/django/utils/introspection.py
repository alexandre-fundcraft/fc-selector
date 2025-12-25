"""Utilities for safe Django model introspection."""

from typing import TYPE_CHECKING, cast

from django.core.exceptions import FieldDoesNotExist
from django.db import models

if TYPE_CHECKING:
    from django.db.models import Field


def get_field_safe(model: type[models.Model], field_name: str) -> "Field | None":
    """Safely get a field, returning None if not found."""
    try:
        return model._meta.get_field(field_name)
    except FieldDoesNotExist:
        return None


def get_related_model(model: type[models.Model], relation_name: str) -> type[models.Model] | None:
    """Get related model for forward or reverse relations."""
    # Try forward relation
    field = get_field_safe(model, relation_name)
    if field and hasattr(field, "related_model"):
        return cast(type[models.Model], field.related_model)

    # Try reverse relation
    for rel in model._meta.related_objects:
        if rel.get_accessor_name() == relation_name:
            return cast(type[models.Model], rel.related_model)

    return None


def is_forward_relation(model: type[models.Model], field_name: str) -> bool:
    """Check if field is a forward relation (ForeignKey/OneToOne)."""
    field = get_field_safe(model, field_name)
    if not field:
        return False
    return hasattr(field, "related_model") and (field.many_to_one or field.one_to_one)


def validate_field_name(
    model: type[models.Model],
    field_name: str,
    allowed_fields: set[str] | None = None,
) -> bool:
    """Validate field name for security (no internal fields, must exist)."""
    if field_name.startswith("_"):
        return False
    if allowed_fields is not None and field_name not in allowed_fields:
        return False
    return get_field_safe(model, field_name) is not None
