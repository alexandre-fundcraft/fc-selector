"""
Converters between ODataQuery and QueryIntent.

These converters provide bidirectional transformation between the
OData-specific query representation (ODataQuery) and the protocol-agnostic
representation (QueryIntent).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fc_selector.core.intent import (
    ExpandIntent,
    FilterIntent,
    OrderIntent,
    PaginationIntent,
    QueryIntent,
    SelectIntent,
)

if TYPE_CHECKING:
    from fc_selector.protocols.odata.parsers.query.models import ODataQuery

# Security: Maximum allowed values for pagination to prevent DoS
MAX_TOP_VALUE = 10000
MAX_SKIP_VALUE = 1000000


def odata_query_to_intent(query: ODataQuery) -> QueryIntent:
    """
    Convert an ODataQuery to a QueryIntent.

    This enables code that uses ODataQuery to seamlessly work with
    the new QueryIntent-based APIs.

    Args:
        query: ODataQuery instance to convert

    Returns:
        Equivalent QueryIntent instance

    Example:
        from fc_selector.protocols.odata import parse_odata_query, odata_query_to_intent

        odata_query = parse_odata_query("$filter=status eq 'active'&$top=10")
        intent = odata_query_to_intent(odata_query)
    """
    intent = QueryIntent()

    # Convert filter
    if query.filter:
        intent.filter = FilterIntent(expression=query.filter.value, ast=query.filter.ast)

    # Convert select
    if query.select:
        intent.select = SelectIntent(fields=query.select.fields if query.select.fields else [])

    # Convert expand
    if query.expand:
        intent.expand = _convert_expand_to_intent(query.expand.nested_options)

    # Convert orderby
    if query.orderby:
        intent.orderby = OrderIntent.from_tuples(query.orderby.fields)

    # Convert pagination with security validation
    top_value = None
    skip_value = None

    if query.top:
        from fc_selector.core.exceptions import InvalidValueError

        try:
            top_value = int(query.top.value)
        except (ValueError, TypeError):
            raise InvalidValueError(query.top.value, "integer", "$top")

        if top_value < 0:
            raise InvalidValueError(query.top.value, "non-negative integer", "$top")
        if top_value > MAX_TOP_VALUE:
            raise InvalidValueError(
                query.top.value,
                f"integer <= {MAX_TOP_VALUE}",
                "$top",
            )

    if query.skip:
        from fc_selector.core.exceptions import InvalidValueError

        try:
            skip_value = int(query.skip.value)
        except (ValueError, TypeError):
            raise InvalidValueError(query.skip.value, "integer", "$skip")

        if skip_value < 0:
            raise InvalidValueError(query.skip.value, "non-negative integer", "$skip")
        if skip_value > MAX_SKIP_VALUE:
            raise InvalidValueError(
                query.skip.value,
                f"integer <= {MAX_SKIP_VALUE}",
                "$skip",
            )

    if top_value is not None or skip_value is not None or query.count:
        intent.pagination = PaginationIntent(limit=top_value, offset=skip_value, include_count=query.count or False)

    return intent


def _convert_expand_to_intent(
    nested_options: dict[str, dict[str, Any]],
) -> ExpandIntent:
    """
    Convert OData nested_options dict to ExpandIntent.

    Args:
        nested_options: Dict mapping relation names to nested query options

    Returns:
        ExpandIntent with converted nested QueryIntents
    """
    from fc_selector.protocols.odata.parsers.orderby import parse_orderby
    from fc_selector.protocols.odata.parsers.select import parse_select

    relations: dict[str, QueryIntent] = {}

    for relation_name, options in nested_options.items():
        nested_intent = QueryIntent()

        if "$filter" in options:
            nested_intent.filter = FilterIntent(expression=options["$filter"])

        if "$select" in options:
            select_value = options["$select"]
            if isinstance(select_value, str):
                fields = parse_select(select_value)
            else:
                fields = select_value
            nested_intent.select = SelectIntent(fields=fields)

        if "$orderby" in options:
            orderby_value = options["$orderby"]
            if isinstance(orderby_value, str):
                orderby_fields = parse_orderby(orderby_value)
                nested_intent.orderby = OrderIntent.from_tuples(orderby_fields)

        if "$top" in options:
            limit = int(options["$top"]) if options["$top"] else None
            offset = int(options.get("$skip", 0)) if options.get("$skip") else None
            nested_intent.pagination = PaginationIntent(limit=limit, offset=offset)

        if "$expand" in options:
            # Recursive expand
            expand_value = options["$expand"]
            if isinstance(expand_value, dict):
                nested_intent.expand = _convert_expand_to_intent(expand_value)
            elif isinstance(expand_value, str):
                # Simple expand without nested options
                nested_intent.expand = ExpandIntent(
                    relations={r.strip(): QueryIntent() for r in expand_value.split(",")}
                )

        relations[relation_name] = nested_intent

    return ExpandIntent(relations=relations)


def intent_to_odata_query(intent: QueryIntent) -> ODataQuery:
    """
    Convert a QueryIntent to an ODataQuery.

    This enables QueryIntent to be serialized to OData format
    for backward compatibility.

    Args:
        intent: QueryIntent instance to convert

    Returns:
        Equivalent ODataQuery instance

    Example:
        from fc_selector.core.intent import QueryIntent, FilterIntent
        from fc_selector.protocols.odata import intent_to_odata_query

        intent = QueryIntent(filter=FilterIntent(expression="status eq 'active'"))
        odata_query = intent_to_odata_query(intent)
    """
    from fc_selector.protocols.odata.parsers.query.models import (
        ExpandOption,
        FilterOption,
        ODataQuery,
        OrderByOption,
        SelectOption,
        SkipOption,
        TopOption,
    )

    query = ODataQuery()

    # Convert filter
    if intent.filter and intent.filter.has_filter():
        query.filter = FilterOption(value=intent.filter.expression or "", ast=intent.filter.ast)

    # Convert select
    if intent.select and intent.select.has_fields():
        query.select = SelectOption(value=",".join(intent.select.fields), fields=intent.select.fields)

    # Convert expand
    if intent.expand and intent.expand.has_relations():
        nested_options = _convert_expand_to_odata(intent.expand)
        query.expand = ExpandOption(
            value=",".join(intent.expand.get_relation_names()),
            nested_options=nested_options,
        )

    # Convert orderby
    if intent.orderby and intent.orderby.has_ordering():
        orderby_parts = [
            f"{of.field} {of.direction}" if of.direction != "asc" else of.field for of in intent.orderby.fields
        ]
        query.orderby = OrderByOption(
            value=",".join(orderby_parts),
            fields=[(of.field, of.direction) for of in intent.orderby.fields],
        )

    # Convert pagination
    if intent.pagination:
        if intent.pagination.limit is not None:
            query.top = TopOption(value=str(intent.pagination.limit))
        if intent.pagination.offset is not None:
            query.skip = SkipOption(value=str(intent.pagination.offset))
        query.count = intent.pagination.include_count or None

    return query


def _convert_expand_to_odata(expand: ExpandIntent) -> dict[str, dict[str, Any]]:
    """
    Convert ExpandIntent to OData nested_options dict.

    Args:
        expand: ExpandIntent to convert

    Returns:
        Dict in OData nested_options format
    """
    nested_options: dict[str, dict[str, Any]] = {}

    for relation_name, nested_intent in expand.relations.items():
        options: dict[str, Any] = {}

        if nested_intent.filter and nested_intent.filter.has_filter():
            options["$filter"] = nested_intent.filter.expression

        if nested_intent.select and nested_intent.select.has_fields():
            options["$select"] = ",".join(nested_intent.select.fields)

        if nested_intent.orderby and nested_intent.orderby.has_ordering():
            orderby_parts = [
                f"{of.field} {of.direction}" if of.direction != "asc" else of.field
                for of in nested_intent.orderby.fields
            ]
            options["$orderby"] = ",".join(orderby_parts)

        if nested_intent.pagination:
            if nested_intent.pagination.limit is not None:
                options["$top"] = str(nested_intent.pagination.limit)
            if nested_intent.pagination.offset is not None:
                options["$skip"] = str(nested_intent.pagination.offset)

        if nested_intent.expand and nested_intent.expand.has_relations():
            options["$expand"] = _convert_expand_to_odata(nested_intent.expand)

        nested_options[relation_name] = options

    return nested_options
