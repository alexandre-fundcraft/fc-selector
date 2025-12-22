"""
Utility functions for OData query parsing and Django ORM integration.

This module provides backward-compatible re-exports from the refactored modules.
For new code, consider importing directly from the specific modules:
- django_odata.parsers.odata_query_parser (framework-agnostic parsing)
- django_odata.parsers.django_query_parser (Django-specific filtering)
- django_odata.builders.query_builder (programmatic query building)
- django_odata.metadata (serializer metadata utilities)
"""

# Re-exports for backward compatibility
from .builders.query_builder import ODataQueryBuilder
from .metadata import build_odata_metadata, get_expandable_fields_from_serializer
from .parsers.django_query_parser import (
    apply_odata_query_params,
    clear_odata_cache,
    odata_cache_context,
)
from .parsers.odata_query_parser import parse_expand_fields_v2, parse_odata_query

__all__ = [
    # Query parsing (framework-agnostic)
    "parse_expand_fields_v2",
    "parse_odata_query",
    # Filter application (Django-specific)
    "apply_odata_query_params",
    "clear_odata_cache",
    "odata_cache_context",
    # Query building
    "ODataQueryBuilder",
    # Metadata utilities
    "get_expandable_fields_from_serializer",
    "build_odata_metadata",
]
