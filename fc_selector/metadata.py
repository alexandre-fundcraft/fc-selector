"""
OData metadata utilities for Django REST framework serializers.

This module provides functions to extract metadata and configuration
from DRF serializers for OData service generation.
"""

from typing import Any


def get_expandable_fields_from_serializer(serializer_class) -> dict[str, Any]:
    """
    Extract expandable fields configuration from a FlexFields serializer.

    Args:
        serializer_class: Serializer class to inspect

    Returns:
        Dictionary of expandable fields configuration
    """
    if hasattr(serializer_class, "Meta") and hasattr(
        serializer_class.Meta, "expandable_fields"
    ):
        return serializer_class.Meta.expandable_fields
    return {}


def build_odata_metadata(model_class, serializer_class) -> dict[str, Any]:
    """
    Build OData-style metadata for a model and its serializer.

    Args:
        model_class: Django model class
        serializer_class: DRF serializer class

    Returns:
        Dictionary containing metadata information
    """
    metadata = {
        "name": model_class.__name__,
        "namespace": model_class._meta.app_label,
        "properties": {},
        "navigation_properties": {},
    }

    # Get serializer fields
    serializer = serializer_class()
    fields = serializer.get_fields()

    for field_name, field in fields.items():
        field_type = type(field).__name__
        metadata["properties"][field_name] = {
            "type": field_type,
            "required": field.required,
            "read_only": field.read_only,
        }

    # Get expandable fields (navigation properties)
    expandable_fields = get_expandable_fields_from_serializer(serializer_class)
    for field_name, config in expandable_fields.items():
        metadata["navigation_properties"][field_name] = {
            "target_type": config[0] if isinstance(config, tuple) else str(config),
            "many": (
                config[1].get("many", False)
                if isinstance(config, tuple) and len(config) > 1
                else False
            ),
        }

    return metadata
