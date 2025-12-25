"""
OData serializer mixin for DRF serializers.

Provides OData-specific serialization logic for nested objects and field selection.
"""

from typing import Any, cast

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
        Adds @odata.context metadata if this is a single entity response.

        Args:
            instance: Model instance to serialize

        Returns:
            Dictionary representation of the instance
        """
        data: dict[str, Any] = cast(dict[str, Any], super().to_representation(instance))

        # Get OData parameters from context
        odata_params = self.context.get("odata_params", {})

        # Apply field selection if $select is specified
        if "$select" in odata_params:
            select_fields = odata_params["$select"]
            if isinstance(select_fields, str):
                select_fields = [f.strip() for f in select_fields.split(",")]

            # Filter data to only include selected fields
            data = {k: v for k, v in data.items() if k in select_fields}

        # Add @odata.context if this is a single entity response
        request = self.context.get("request")
        if request and hasattr(self, "Meta") and hasattr(self.Meta, "model"):
            # Handle both DRF requests and mock requests safely
            query_params = getattr(request, "query_params", getattr(request, "GET", {}))
            headers = getattr(request, "headers", getattr(request, "META", {}))

            include_context = query_params.get("$format") == "json" or headers.get(
                "Accept", headers.get("HTTP_ACCEPT", "")
            ).startswith("application/json")

            if include_context and hasattr(instance, "pk"):
                odata_context = self.get_odata_context()
                data["@odata.context"] = (
                    f"{odata_context['service_root']}$metadata#{odata_context['entity_set']}/$entity"
                )

        return data

    def get_odata_context(self) -> dict[str, Any]:
        """
        Get OData context for serializers.

        Returns:
            Dictionary with OData parameters and metadata
        """
        request = self.context.get("request")
        service_root = getattr(request, "build_absolute_uri", lambda x: x)("/odata/") if request else "/odata/"

        context = {
            "odata_version": "4.0",
            "service_root": service_root,
            # Preserve existing OData params if any (for nested serializers)
            "odata_params": self.context.get("odata_params", {}),
        }

        if hasattr(self, "Meta") and hasattr(self.Meta, "model"):
            context["entity_set"] = self.Meta.model.__name__.lower() + "s"
            context["entity_type"] = self.Meta.model.__name__

        return context
