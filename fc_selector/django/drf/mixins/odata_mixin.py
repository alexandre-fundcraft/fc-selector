"""
OData mixin for DRF viewsets.

Provides OData query parameter parsing and application to DRF viewsets.
"""

from typing import Any

from django.db.models import QuerySet
from rest_framework.request import Request

from fc_selector.core.parsers.query import parse_odata_query
from fc_selector.django.query import apply_odata_query_params


class ODataMixin:
    """
    Mixin for DRF viewsets to add OData query support.

    Automatically parses OData query parameters from the request and applies them
    to the queryset. Supports $filter, $select, $expand, $orderby, $top, $skip.

    Example:
        class BlogPostViewSet(ODataMixin, viewsets.ModelViewSet):
            queryset = BlogPost.objects.all()
            serializer_class = BlogPostSerializer
    """

    def get_odata_query_params(self) -> dict[str, Any]:
        """
        Extract OData query parameters from request.

        Returns:
            Dictionary of OData query parameters
        """
        request: Request = self.request
        query_params = {}

        # Extract OData parameters from query string
        odata_options = [
            "$filter",
            "$select",
            "$expand",
            "$orderby",
            "$top",
            "$skip",
            "$count",
        ]

        for param in odata_options:
            if param in request.query_params:
                query_params[param] = request.query_params[param]

        return query_params

    def apply_odata_query(self, queryset: QuerySet) -> QuerySet:
        """
        Apply OData query parameters to the queryset.

        Args:
            queryset: Base queryset to filter

        Returns:
            Filtered queryset with OData parameters applied
        """
        query_params = self.get_odata_query_params()

        if not query_params:
            return queryset

        # Parse OData query
        parsed_query = parse_odata_query(query_params)

        # Apply to queryset
        return apply_odata_query_params(queryset, parsed_query.to_dict())

    def get_queryset(self) -> QuerySet:
        """
        Get queryset with OData parameters applied.

        Returns:
            Filtered queryset
        """
        queryset = super().get_queryset()
        return self.apply_odata_query(queryset)

    def get_serializer_context(self) -> dict[str, Any]:
        """
        Get serializer context with OData parameters.

        Returns:
            Serializer context dictionary
        """
        context = super().get_serializer_context()
        context["odata_params"] = self.get_odata_query_params()
        return context
