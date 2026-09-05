"""
OData Parsers - Separated by Component.

This package contains specialized parsers for each OData query parameter:
- filter: $filter expression parser (AST-based, from odata-query)
- select: $select field list parser
- expand: $expand relationship parser
- orderby: $orderby clause parser
- query: Complete OData query parser (combines all)

Each parser is independent and can be used standalone.
"""

# Re-export main parsers for convenience
from .filter import ODataLexer, ODataParser
from .query import parse_odata_query

__all__ = [
    # Filter parser (AST)
    "ODataLexer",
    "ODataParser",
    # Query parser (complete)
    "parse_odata_query",
]
