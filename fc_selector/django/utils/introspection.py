"""Utilities for safe Django model introspection."""

from typing import TYPE_CHECKING

from django.core.exceptions import FieldDoesNotExist
from django.db import models

if TYPE_CHECKING:
    from django.db.models import Field


def get_field_safe(model: type[models.Model], field_name: str) -> "Field | None":
    """Safely get a field, returning None if not found."""
    try:
        return model._meta.get_field(field_name)  # noqa: W0212 - Django's public API
    except FieldDoesNotExist:
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


def get_reverse_fk_info(model: type[models.Model], relation_name: str) -> tuple[type[models.Model], str] | None:
    """Get (child_model, fk_attname) for a reverse FK relation.

    Returns None if not a reverse FK.
    """
    for rel in model._meta.related_objects:
        if rel.get_accessor_name() == relation_name and not rel.many_to_many:
            return rel.related_model, rel.field.attname
    return None


def get_m2m_info(
    model: type[models.Model], relation_name: str
) -> tuple[type[models.Model], type[models.Model], str, str] | None:
    """Get through-table info for a M2M relation.

    Returns (through_model, related_model, source_fk_attname, target_fk_attname),
    or None if the relation is not M2M.
    """
    # Check forward M2M (e.g. tags = ManyToManyField(...))
    field = get_field_safe(model, relation_name)
    if field and isinstance(field, models.ManyToManyField):
        through_model = field.remote_field.through
        related_model = field.related_model
        source_fk, target_fk = _resolve_through_fks(through_model, model, related_model)
        if source_fk and target_fk:
            return through_model, related_model, source_fk, target_fk

    # Check reverse M2M (e.g. tagged_items from the other side)
    for rel in model._meta.related_objects:
        if rel.get_accessor_name() == relation_name and rel.many_to_many:
            through_model = rel.through
            related_model = rel.related_model
            source_fk, target_fk = _resolve_through_fks(through_model, model, related_model)
            if source_fk and target_fk:
                return through_model, related_model, source_fk, target_fk

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
