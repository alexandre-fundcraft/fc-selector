"""
OData serializer mixin for DRF serializers.

Provides OData-specific serialization logic for nested objects and field selection.
"""

from typing import Any

from rest_framework import serializers


class ODataSerializerMixin(serializers.Serializer):
    """
    Mixin for DRF serializers to add OData support.

    Handles OData-specific representation logic and applies nested query options
    to expanded related objects.

    Example:
        class BlogPostSerializer(ODataSerializerMixin, serializers.ModelSerializer):
            class Meta:
                model = BlogPost
                fields = ['id', 'title', 'content', 'author']
    """

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """
        Convert instance to OData-formatted representation.

        Applies OData query options to nested serializers if provided in context.

        Args:
            instance: Model instance to serialize

        Returns:
            Dictionary representation of the instance
        """
        data = super().to_representation(instance)

        # Get OData parameters from context
        odata_params = self.context.get("odata_params", {})

        # Apply field selection if $select is specified
        if "$select" in odata_params:
            select_fields = odata_params["$select"]
            if isinstance(select_fields, str):
                select_fields = [f.strip() for f in select_fields.split(",")]

            # Filter data to only include selected fields
            data = {k: v for k, v in data.items() if k in select_fields}

        return data

    def get_odata_context(self) -> dict[str, Any]:
        """
        Get OData context for nested serializers.

        Returns:
            Dictionary with OData parameters for nested serializers
        """
        context = self.context.copy()
        odata_params = context.get("odata_params", {})

        # Pass OData parameters to nested serializers
        context["odata_params"] = odata_params

        return context
