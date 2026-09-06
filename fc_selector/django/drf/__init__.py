"""
Django REST Framework OData integration.

This package contains DRF-specific implementations for OData support,
including viewsets, serializers, and schema documentation.
"""

from .spectacular import ODATA_PARAMETERS, ODATA_RETRIEVE_PARAMETERS, postprocess_odata_schema
from .viewsets import ODataSelectorViewSetMixin

__all__ = [
    "ODataSelectorViewSetMixin",
    "ODATA_PARAMETERS",
    "ODATA_RETRIEVE_PARAMETERS",
    "postprocess_odata_schema",
]
