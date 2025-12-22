"""
Core OData functionality - Framework-agnostic layer.

This package contains parsing and filtering logic that doesn't depend on Django,
making it reusable across different frameworks or standalone usage.
"""

from .parsers.query import ODataQueryParser, parse_odata_query
from .query_builder import ODataQueryBuilder

__all__ = [
    "parse_odata_query",
    "ODataQueryParser",
    "ODataQueryBuilder",
]
