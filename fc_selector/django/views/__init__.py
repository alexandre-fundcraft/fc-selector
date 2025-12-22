"""
Django views for OData endpoints.
"""

from .metadata import (
    ODataMetadataRegistry,
    ODataMetadataView,
    ODataServiceDocumentView,
    register_odata_entity,
)

__all__ = [
    "ODataMetadataView",
    "ODataServiceDocumentView",
    "ODataMetadataRegistry",
    "register_odata_entity",
]
