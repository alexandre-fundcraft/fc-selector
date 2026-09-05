"""
Django views for OData endpoints.
"""

from .metadata import (
    ODataMetadataRegistry,
    ODataMetadataView,
    ODataServiceDocumentView,
)

__all__ = [
    "ODataMetadataView",
    "ODataServiceDocumentView",
    "ODataMetadataRegistry",
]
