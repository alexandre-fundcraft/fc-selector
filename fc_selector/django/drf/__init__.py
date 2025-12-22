"""
Django REST Framework OData integration.

This package contains DRF-specific implementations for OData support,
including mixins, viewsets, serializers, and schema documentation.
"""

from .mixins import ODataMixin, ODataSerializerMixin
from .schema import ODataAutoSchema
from .spectacular import (
    ODATA_PARAMETERS,
    ODATA_RETRIEVE_PARAMETERS,
    get_odata_parameters,
    get_odata_retrieve_parameters,
)
from .viewsets import ODataModelViewSet, ODataReadOnlyModelViewSet, ODataViewSet

__all__ = [
    "ODataMixin",
    "ODataSerializerMixin",
    "ODataAutoSchema",
    "ODataViewSet",
    "ODataModelViewSet",
    "ODataReadOnlyModelViewSet",
    "get_odata_parameters",
    "get_odata_retrieve_parameters",
    "ODATA_PARAMETERS",
    "ODATA_RETRIEVE_PARAMETERS",
]
