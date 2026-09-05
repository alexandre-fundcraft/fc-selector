"""
Django-specific OData implementations.

This package contains Django ORM-specific implementations that apply OData queries
to Django QuerySets and provide selector pattern support.
"""

from .query import apply_odata_query_params
from .selector import ODataSelector
from .views import (
    ODataMetadataRegistry,
    ODataMetadataView,
    ODataServiceDocumentView,
)

__all__ = [
    "apply_odata_query_params",
    "ODataSelector",
    "ODataMetadataView",
    "ODataServiceDocumentView",
    "ODataMetadataRegistry",
]
