"""
Django OData selector pattern.

Provides a clean selector interface for executing OData queries on Django models.
"""

from fc_selector.core.query_builder import ODataQueryBuilder

from .odata_selector import ODataSelector

__all__ = [
    "ODataSelector",
    "ODataQueryBuilder",
]
