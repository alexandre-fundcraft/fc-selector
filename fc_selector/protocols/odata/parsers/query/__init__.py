"""
OData query parsing - Framework-agnostic.

Parses complete OData queries into the protocol-agnostic QueryIntent.
"""

from .parser import MAX_SKIP_VALUE, MAX_TOP_VALUE, parse_odata_query, parse_query_params

__all__ = [
    "parse_odata_query",
    "parse_query_params",
    "MAX_TOP_VALUE",
    "MAX_SKIP_VALUE",
]
