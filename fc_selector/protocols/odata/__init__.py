"""
OData protocol implementation.

Parses OData query strings ($filter, $select, $expand, $orderby, $top, $skip,
$count) into the protocol-agnostic QueryIntent.

Usage:
    from fc_selector.protocols.odata import parse_odata_query

    intent = parse_odata_query("$filter=status eq 'active'&$top=10")
"""

from .parsers.query import parse_odata_query

__all__ = [
    "parse_odata_query",
]
