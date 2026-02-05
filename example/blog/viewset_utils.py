"""
Shared utilities for viewsets examples.

This module contains common patterns used across different viewset implementations
to reduce code duplication while keeping the examples readable.
"""

from fc_selector.django.drf.utils import build_odata_response
from rest_framework.response import Response


def build_stats_response(dto):
    """Build a standardized stats response from a blog post DTO.

    Args:
        dto: BlogPostDTO instance

    Returns:
        Dictionary containing post statistics
    """
    return {
        "id": dto.id,
        "title": dto.title,
        "view_count": dto.view_count,
        "word_count": dto.word_count,
        "status": dto.status,
        "is_published": dto.is_published,
        "created_at": dto.created_at,
        "published_at": dto.published_at,
    }


def build_related_items_response(request, dtos, serializer_class, entity_set_name, selector):
    """Build a standardized OData response for related items.

    Args:
        request: Django request object
        dtos: List of DTO instances
        serializer_class: Serializer class to use
        entity_set_name: OData entity set name
        selector: Selector instance for count queries

    Returns:
        Response object with OData-formatted data
    """
    query_string = request.META.get("QUERY_STRING", "")
    serializer = serializer_class(dtos, many=True)

    return Response(
        build_odata_response(
            request=request,
            serializer_data=serializer.data,
            query_string=query_string,
            entity_set_name=entity_set_name,
            selector=selector,
        )
    )
