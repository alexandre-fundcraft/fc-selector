"""
Django REST Framework OData integration.

This package contains DRF-specific implementations for OData support,
including mixins, viewsets, serializers, and schema documentation.
"""

from .mixins import ODataSerializerMixin
from .schema import ODataAutoSchema
from .spectacular import (
    ODATA_PARAMETERS,
    ODATA_RETRIEVE_PARAMETERS,
    get_odata_parameters,
    get_odata_retrieve_parameters,
)
from .viewsets import ODataSelectorViewSetMixin

__all__ = [
    "ODataSerializerMixin",
    "ODataAutoSchema",
    "ODataSelectorViewSetMixin",
    "get_odata_parameters",
    "get_odata_retrieve_parameters",
    "ODATA_PARAMETERS",
    "ODATA_RETRIEVE_PARAMETERS",
]
