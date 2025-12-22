"""
Django query application and optimization.

This module contains Django-specific implementations for applying OData queries
to Django QuerySets with optimization and caching support.
"""

from .applier import apply_odata_query_params

__all__ = [
    "apply_odata_query_params",
]
