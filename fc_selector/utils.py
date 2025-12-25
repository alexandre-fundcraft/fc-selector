"""
Utility functions for OData query parsing and Django ORM integration.

This module provides backward-compatible re-exports from the refactored modules.
"""

# Re-exports for backward compatibility
from fc_selector.core.query_builder import QueryBuilder
from fc_selector.django.query.applier import apply_odata_query_params
from fc_selector.protocols.odata.parsers.expand import parse_expand as parse_expand_fields_v2

# Parsing functions
from fc_selector.protocols.odata.parsers.query.parser import parse_odata_query

__all__ = [
    # Query parsing (framework-agnostic)
    "parse_expand_fields_v2",
    "parse_odata_query",
    # Filter application (Django-specific)
    "apply_odata_query_params",
    # Query building
    "QueryBuilder",
]
