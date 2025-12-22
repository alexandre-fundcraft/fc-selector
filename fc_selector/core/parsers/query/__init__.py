"""
Core OData query parsing - Framework-agnostic.

This module contains parsing functions that don't depend on Django,
making them reusable across different frameworks or standalone usage.
"""

from .models import ODataQuery
from .parser import ODataQueryParser, parse_odata_query

__all__ = [
    "parse_odata_query",
    "ODataQueryParser",
    "ODataQuery",
]
