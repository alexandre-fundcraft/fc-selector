"""
OData protocol implementation.

This module provides OData-specific parsing and conversion:
- parsers: Parse OData query strings ($filter, $select, $expand, etc.)
- converters: Convert between ODataQuery and QueryIntent

Usage:
    from fc_selector.protocols.odata import parse_odata_query
    from fc_selector.protocols.odata.converters import odata_query_to_intent

    # Parse OData query string
    odata_query = parse_odata_query("$filter=status eq 'active'&$top=10")

    # Convert to protocol-agnostic QueryIntent
    intent = odata_query_to_intent(odata_query)
"""

from .converters import intent_to_odata_query, odata_query_to_intent
from .parsers.query import parse_odata_query

__all__ = [
    "parse_odata_query",
    "odata_query_to_intent",
    "intent_to_odata_query",
]
