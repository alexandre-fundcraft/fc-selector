"""Utilities for safe Django model introspection."""

from typing import TYPE_CHECKING, TypedDict, cast

from django.core.exceptions import FieldDoesNotExist
from django.db import models

from fc_selector.core.exceptions import InvalidFieldError
from fc_selector.core.utils import get_base_field, is_private_field

if TYPE_CHECKING:
    from django.db.models import Field


def get_field_safe(model: type[models.Model], field_name: str) -> "Field | None":
    """Safely get a field, returning None if not found."""
    try:
        return model._meta.get_field(field_name)  # noqa: W0212 - Django's public API
    except FieldDoesNotExist:
        return None


def get_related_model(model: type[models.Model], relation_name: str) -> type[models.Model] | None:
    """Get related model for forward or reverse relations."""
    # Try forward relation
    field = get_field_safe(model, relation_name)
    if field and hasattr(field, "related_model"):
        return cast(type[models.Model], field.related_model)

    # Try reverse relation
    for rel in model._meta.related_objects:  # noqa: W0212 - Django's public API
        if rel.get_accessor_name() == relation_name:
            return cast(type[models.Model], rel.related_model)

    return None


def is_forward_relation(model: type[models.Model], field_name: str) -> bool:
    """Check if field is a forward relation (ForeignKey/OneToOne)."""
    field = get_field_safe(model, field_name)
    if not field:
        return False
    return hasattr(field, "related_model") and (field.many_to_one or field.one_to_one)


def is_m2m_relation(model: type[models.Model], field_name: str) -> bool:
    """Check if field is a M2M relation (forward or reverse)."""
    field = get_field_safe(model, field_name)
    if field and getattr(field, "many_to_many", False):
        return True
    for rel in model._meta.related_objects:
        if rel.get_accessor_name() == field_name and rel.many_to_many:
            return True
    return False


def get_reverse_fk_info(
    model: type[models.Model], relation_name: str
) -> tuple[type[models.Model], str] | None:
    """Get (child_model, fk_attname) for a reverse FK relation.

    Returns None if not a reverse FK.
    """
    for rel in model._meta.related_objects:
        if rel.get_accessor_name() == relation_name and not rel.many_to_many:
            return rel.related_model, rel.field.attname
    return None


class M2MInfo(TypedDict):
    """Type-safe return value for get_m2m_info."""

    through_model: type[models.Model]
    related_model: type[models.Model]
    source_fk_attname: str
    target_fk_attname: str


def get_m2m_info(model: type[models.Model], relation_name: str) -> M2MInfo | None:
    """Get through model info for a M2M relation.

    Returns None if not M2M.
    """
    # Check forward M2M (e.g. tags = ManyToManyField(...))
    field = get_field_safe(model, relation_name)
    if field and isinstance(field, models.ManyToManyField):
        through_model = field.remote_field.through
        related_model = field.related_model
        source_fk, target_fk = _resolve_through_fks(through_model, model, related_model)
        if source_fk and target_fk:
            return {
                "through_model": through_model,
                "related_model": related_model,
                "source_fk_attname": source_fk,
                "target_fk_attname": target_fk,
            }

    # Check reverse M2M (e.g. tagged_items from the other side)
    for rel in model._meta.related_objects:
        if rel.get_accessor_name() == relation_name and rel.many_to_many:
            through_model = rel.through
            related_model = rel.related_model
            source_fk, target_fk = _resolve_through_fks(through_model, model, related_model)
            if source_fk and target_fk:
                return {
                    "through_model": through_model,
                    "related_model": related_model,
                    "source_fk_attname": source_fk,
                    "target_fk_attname": target_fk,
                }

    return None


def _resolve_through_fks(
    through_model: type[models.Model],
    source_model: type[models.Model],
    target_model: type[models.Model],
) -> tuple[str | None, str | None]:
    """Resolve FK attnames on a through model for source and target models.

    For self-referential M2M (source_model is target_model), uses positional
    ordering: the first FK match is source, the second is target. This matches
    Django's convention of from_X_id / to_X_id.
    """
    source_fk: str | None = None
    target_fk: str | None = None

    if source_model is target_model:
        # Self-referential M2M: assign by order (first=source, second=target)
        for f in through_model._meta.get_fields():
            if hasattr(f, "related_model") and hasattr(f, "attname"):
                if f.related_model is source_model:
                    if source_fk is None:
                        source_fk = f.attname
                    elif target_fk is None:
                        target_fk = f.attname
                        break
    else:
        for f in through_model._meta.get_fields():
            if hasattr(f, "related_model") and hasattr(f, "attname"):
                if f.related_model is source_model:
                    source_fk = f.attname
                elif f.related_model is target_model:
                    target_fk = f.attname

    return source_fk, target_fk


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
    exists = get_field_safe(model, field_name) is not None

    if not exists:
        if "__" in field_name:
            # It's a path. Simple validation fails for paths.
            pass
        elif allowed_fields is not None and field_name in allowed_fields:
            # It is allowed, maybe it's an annotation?
            return True

        if raise_exception:
            raise InvalidFieldError(field_name, model.__name__, reason="field does not exist on model")
        return False

    return True
