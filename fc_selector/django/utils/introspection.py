"""Utilities for safe Django model introspection."""

from typing import TYPE_CHECKING, cast

from django.core.exceptions import FieldDoesNotExist
from django.db import models

from fc_selector.core.exceptions import InvalidFieldError
from fc_selector.core.utils import get_base_field, is_private_field

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
    raise_exception: bool = False,
) -> bool:
    """
    Validate field name for security (no internal fields, must exist).

    Args:
        model: The Django model to check against.
        field_name: The name of the field to validate.
        allowed_fields: Optional set of allowed field names.
        raise_exception: If True, raises InvalidFieldError with reason.

    Returns:
        True if valid, False otherwise (if raise_exception is False).

    Raises:
        InvalidFieldError: If validation fails and raise_exception is True.
    """
    # Block access to private/internal fields
    if is_private_field(field_name):
        if raise_exception:
            raise InvalidFieldError(field_name, model.__name__, reason="access to private fields is not allowed")
        return False

    # Extract base field name (before any __) for allowed_fields check
    base_field = get_base_field(field_name)

    # Check against allowed fields if specified
    if allowed_fields is not None and base_field not in allowed_fields:
        if raise_exception:
            raise InvalidFieldError(field_name, model.__name__, reason="field is not in allowed fields list")
        return False

    # Check existence on model (only for direct fields, not paths or if skipped via allowed_fields logic)
    # Note: Logic from visitor skipped check if base_field in allowed_fields AND it was complex path?
    # Visitor logic:
    # if "__" not in resolved_field and not (self.allowed_fields is not None and base_field in self.allowed_fields):
    #    check existence

    # We will keep it simple: strict check if requested.
    # But wait, validate_field_name in visitor was calling resolve_field_alias first.
    # Here we assume field_name is already resolved or we are checking the raw name?
    # The existing validate_field_name (simple) checked get_field_safe(model, field_name).

    exists = get_field_safe(model, field_name) is not None

    # If it's a path (contains __), get_field_safe returns None usually (unless using some traverse util, but get_field is shallow).
    # If it is a path, we might not want to validate full existence here without traversal logic.
    # The original simple validate_field_name returned False for paths that are not direct fields.

    if not exists:
        # If it's a path, or allowed, we might be lenient?
        # The visitor logic was: check existence UNLESS it's in allowed_fields (implies annotation?).

        if "__" in field_name:
            # It's a path. Simple validation fails for paths.
            # We should probably return False/Raise if strict.
            pass
        elif allowed_fields is not None and field_name in allowed_fields:
            # It is allowed, maybe it's an annotation?
            return True

        if raise_exception:
            raise InvalidFieldError(field_name, model.__name__, reason="field does not exist on model")
        return False

    return True
