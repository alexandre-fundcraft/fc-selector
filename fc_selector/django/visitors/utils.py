from django.core.exceptions import FieldDoesNotExist
from django.db.models import Model

from fc_selector.core import exceptions as core_ex


def reverse_relationship(relationship_expr: str, root_model: type[Model]) -> tuple[str, type[Model]]:
    """
    Reverses a relationship expression relative to root_model.

    Args:
        relationship_expr: The Django relationship string, with underscores to
            represent relationship traversal.
        root_model: The model to which relationship_expr is relative.

    Returns:
        str: The django relationship string in reverse, so from the last joined
            relationship back to the root model.
        Type[Model]: The model to which the returned expression is relative.

    Raises:
        InvalidFieldError: If the relationship expression is invalid or contains
            fields that don't exist or aren't relations.
    """
    if not relationship_expr or not relationship_expr.strip():
        raise core_ex.InvalidFieldError(
            relationship_expr or "(empty)",
            root_model.__name__,
            reason="empty relationship expression",
        )

    relation_steps = relationship_expr.split("__")
    related_model = root_model
    path_to_outerref_parts = []

    for step in relation_steps:
        if not step:
            raise core_ex.InvalidFieldError(
                relationship_expr,
                root_model.__name__,
                reason="relationship expression contains empty segments",
            )

        try:
            related_field = related_model._meta.get_field(step)  # noqa: W0212 - Django's public API
        except FieldDoesNotExist:
            raise core_ex.FieldNotFoundError(step, related_model.__name__)

        if not hasattr(related_field, "related_model") or related_field.related_model is None:
            raise core_ex.InvalidFieldError(
                step,
                related_model.__name__,
                reason="field is not a relation",
            )

        if not hasattr(related_field, "remote_field") or related_field.remote_field is None:
            raise core_ex.InvalidFieldError(
                step,
                related_model.__name__,
                reason="relation has no remote_field (may be a reverse relation without explicit related_name)",
            )

        related_model = related_field.related_model
        path_to_outerref_parts.append(related_field.remote_field.name)

    path_to_outerref = "__".join(reversed(path_to_outerref_parts))

    return (path_to_outerref, related_model)
