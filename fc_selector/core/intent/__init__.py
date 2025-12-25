"""
Protocol-agnostic query intent module.

This module provides the QueryIntent abstraction layer that decouples
the internal query representation from OData-specific terminology.

Usage:
    from fc_selector.core.intent import QueryIntent, FilterIntent, SelectIntent

    # Build a query intent
    intent = QueryIntent(
        filter=FilterIntent(expression="status eq 'active'"),
        select=SelectIntent(fields=["id", "name"]),
        pagination=PaginationIntent(limit=10)
    )

    # Execute with selector
    results = selector.execute(intent)

For OData-specific converters, use:
    from fc_selector.protocols.odata import odata_query_to_intent, intent_to_odata_query
"""

from .models import (
    ExpandIntent,
    FilterIntent,
    OrderField,
    OrderIntent,
    PaginationIntent,
    QueryIntent,
    SelectIntent,
)

__all__ = [
    "QueryIntent",
    "FilterIntent",
    "SelectIntent",
    "ExpandIntent",
    "OrderIntent",
    "OrderField",
    "PaginationIntent",
]
