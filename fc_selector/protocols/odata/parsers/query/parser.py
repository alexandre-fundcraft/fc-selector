"""
Framework-agnostic OData query parser.

Parses OData query strings and dictionaries straight into ``QueryIntent``, the
protocol-agnostic representation the rest of the library executes.
"""

from typing import Any
from urllib.parse import parse_qsl

from fc_selector.core.exceptions import InvalidValueError
from fc_selector.core.intent import (
    ExpandIntent,
    FilterIntent,
    OrderIntent,
    PaginationIntent,
    QueryIntent,
    SelectIntent,
)

from ..expand import parse_expand
from ..orderby import parse_orderby
from ..select import parse_select

# Security: Maximum allowed values for pagination to prevent DoS
MAX_TOP_VALUE = 10000
MAX_SKIP_VALUE = 1000000


def parse_query_params(query_string: str) -> dict[str, str]:
    """Split a raw OData query string into a parameter dictionary."""
    if not query_string or not query_string.strip():
        return {}

    return dict(parse_qsl(query_string.removeprefix("?")))


def parse_odata_query(query_params: dict[str, Any] | str) -> QueryIntent:
    """
    Parse OData query parameters into a QueryIntent.

    Args:
        query_params: Dictionary of query parameters or a raw query string
            (e.g. ``"$filter=status eq 'active'&$top=10"``).

    Returns:
        QueryIntent with filter, select, expand, ordering and pagination set
        for whichever parameters were present.
    """
    if isinstance(query_params, str):
        query_params = parse_query_params(query_params)
    elif not query_params:
        return QueryIntent()

    intent = QueryIntent()

    if "$filter" in query_params:
        from ..filter import parse_filter

        expression = query_params["$filter"]
        intent.filter = FilterIntent(expression=expression, ast=parse_filter(expression))

    if "$select" in query_params:
        intent.select = SelectIntent(fields=parse_select(query_params["$select"]))

    if "$expand" in query_params:
        intent.expand = _expand_intent(parse_expand(query_params["$expand"]))

    if "$orderby" in query_params:
        intent.orderby = OrderIntent.from_tuples(parse_orderby(query_params["$orderby"]))

    intent.pagination = _pagination_intent(query_params)

    return intent


def _bounded_int(value: Any, param: str, maximum: int) -> int:
    """Parse a pagination value, rejecting non-integers, negatives and DoS-sized values."""
    try:
        parsed = int(value)
    except (ValueError, TypeError) as exc:
        raise InvalidValueError(value, "integer", param) from exc

    if parsed < 0:
        raise InvalidValueError(value, "non-negative integer", param)
    if parsed > maximum:
        raise InvalidValueError(value, f"integer <= {maximum}", param)

    return parsed


def _pagination_intent(params: dict[str, Any]) -> PaginationIntent | None:
    """Build the pagination intent from $top / $skip / $count."""
    top = _bounded_int(params["$top"], "$top", MAX_TOP_VALUE) if params.get("$top") not in (None, "") else None
    skip = _bounded_int(params["$skip"], "$skip", MAX_SKIP_VALUE) if params.get("$skip") not in (None, "") else None

    count = params.get("$count")
    include_count = count.lower() == "true" if isinstance(count, str) else bool(count)

    if top is None and skip is None and not include_count:
        return None

    return PaginationIntent(limit=top, offset=skip, include_count=include_count)


def _expand_intent(nested_options: dict[str, dict[str, Any]]) -> ExpandIntent:
    """Convert parsed $expand options into nested QueryIntents."""
    relations: dict[str, QueryIntent] = {}

    for relation_name, options in nested_options.items():
        nested = QueryIntent()

        if "$filter" in options:
            from ..filter import parse_filter

            expression = options["$filter"]
            nested.filter = FilterIntent(expression=expression, ast=parse_filter(expression))

        if "$select" in options:
            value = options["$select"]
            nested.select = SelectIntent(fields=parse_select(value) if isinstance(value, str) else value)

        if "$orderby" in options and isinstance(options["$orderby"], str):
            nested.orderby = OrderIntent.from_tuples(parse_orderby(options["$orderby"]))

        # Same bounds as the top level: nested $top/$skip are user input too
        nested.pagination = _pagination_intent(options)

        if "$expand" in options:
            value = options["$expand"]
            if isinstance(value, dict):
                nested.expand = _expand_intent(value)
            elif isinstance(value, str):
                nested.expand = ExpandIntent(relations={r.strip(): QueryIntent() for r in value.split(",")})

        relations[relation_name] = nested

    return ExpandIntent(relations=relations)
