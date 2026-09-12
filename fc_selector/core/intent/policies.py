"""Reusable query policies, independent of ORM and query language."""

from copy import deepcopy

from fc_selector.core.exceptions import InvalidValueError
from fc_selector.core.intent.models import OrderIntent, PaginationIntent, QueryIntent, SelectIntent


def selection_for_policy(selection: SelectIntent | None, allowed: list[str] | None) -> SelectIntent | None:
    if selection is not None and "*" not in selection.fields:
        return deepcopy(selection)
    return SelectIntent(list(allowed)) if allowed is not None else None


def collection_defaults(intent: QueryIntent, *, ordering: list[str], limit: int | None, maximum: int) -> QueryIntent:
    """Copy and bound materialized collections, leaving lazy adapter APIs alone."""
    result = deepcopy(intent)
    if ordering and (not result.orderby or not result.orderby.has_ordering()):
        result.orderby = OrderIntent.from_tuples(
            [(f.lstrip("-"), "desc" if f.startswith("-") else "asc") for f in ordering]
        )
    if result.pagination is None:
        result.pagination = PaginationIntent()
    effective = result.pagination.limit if result.pagination.limit is not None else limit
    if effective is not None:
        if type(effective) is not int or effective < 0:
            raise InvalidValueError(effective, "non-negative integer", "limit")
        result.pagination.limit = min(effective, maximum)
    return result
