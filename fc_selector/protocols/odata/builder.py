"""OData compatibility for the neutral fluent builder and legacy DTO options."""

from functools import lru_cache
from typing import Any
from urllib.parse import quote

from fc_selector.core.intent import ExpandIntent, OrderIntent, QueryIntent
from fc_selector.protocols.odata.parsers.expand import parse_expand
from fc_selector.protocols.odata.parsers.filter import parse_filter
from fc_selector.protocols.odata.parsers.query import parse_odata_query, parse_query_params
from fc_selector.protocols.odata.parsers.query.parser import _pagination_intent

__all__ = ["parse_filter"]


def populate_query_builder(builder, query_string):
    params = parse_query_params(query_string)
    _pagination_intent(params)
    for key, value in params.items():
        value = value.strip()
        method = {"$filter": "filter", "$select": "select", "$expand": "expand", "$orderby": "orderby"}.get(key)
        if method:
            getattr(builder, method)(value)
        elif key == "$top":
            builder.top(int(value))
        elif key == "$skip":
            builder.skip(int(value))
        elif key == "$count":
            builder.count(value.lower() == "true")


def parse_builder_options(expand, orderby):
    if isinstance(expand, str):
        expand = parse_odata_query({"$expand": expand}).expand if expand else None
    if isinstance(orderby, str):
        fields = []
        for spec in orderby.split(",") if orderby else ():
            parts = spec.strip().split()
            fields.append((parts[0], parts[1].lower() if len(parts) > 1 else "asc"))
        orderby = OrderIntent.from_tuples(fields) if fields else None
    return expand, orderby


def builder_to_params(builder) -> dict[str, str]:
    if (
        (builder._filter is not None and not isinstance(builder._filter, str))
        or isinstance(builder._expand, ExpandIntent)
        or isinstance(builder._orderby, OrderIntent)
    ):
        raise ValueError("Use build() for fluent queries; textual conversion would discard AST options")
    result = {}
    for key, value in (
        ("$filter", builder._filter),
        ("$select", ",".join(builder._select or ())),
        ("$expand", builder._expand),
        ("$orderby", builder._orderby),
    ):
        if value:
            result[key] = value
    for key, value in (("$top", builder._top), ("$skip", builder._skip)):
        if value is not None:
            result[key] = str(value)
    if builder._count is not None:
        result["$count"] = "true" if builder._count else "false"
    return result


def builder_to_query_string(builder) -> str:
    return "&".join(quote(f"{key}={value}", safe="=$ (),/;':") for key, value in builder_to_params(builder).items())


@lru_cache(maxsize=128)
def parse_nested_options(value: str) -> tuple[set[str], dict]:
    options = parse_expand(value)
    return set(options), options


def projection_intent(selected=None, expanded=None, options=None, *, depth=0):
    """Translate legacy DTO $select/$expand options at the protocol boundary."""
    from fc_selector.core.dtos.base import MAX_DTO_RECURSION_DEPTH, RecursionLimitExceededError
    from fc_selector.core.intent import QueryIntent, SelectIntent

    if depth > MAX_DTO_RECURSION_DEPTH:
        raise RecursionLimitExceededError(depth, "projection")
    relations = {}
    for name in expanded or ():
        nested = (options or {}).get(name, {})
        fields = nested.get("$select")
        if isinstance(fields, str):
            fields = {f.strip() for f in fields.split(",")}
        children = nested.get("$expand", {})
        if isinstance(children, str):
            children = parse_nested_options(children)[1]
        relations[name] = projection_intent(fields, set(children), children, depth=depth + 1)
    return QueryIntent(
        select=SelectIntent(list(selected)) if selected is not None else None,
        expand=ExpandIntent(relations) if relations else None,
    )


def dto_options(intent: QueryIntent) -> tuple[set[str] | None, dict]:
    """Projection options for DTO conversion, without reparsing protocol strings."""
    selected = set(intent.select.fields) if intent.select is not None else None
    options = {}
    if intent.expand:
        for name, nested in intent.expand.relations.items():
            nested_selected, nested_expand = dto_options(nested)
            opts: dict[str, Any] = {}
            if nested_selected is not None:
                opts["$select"] = nested_selected
            if nested_expand:
                opts["$expand"] = nested_expand
            options[name] = opts
    return selected, options
