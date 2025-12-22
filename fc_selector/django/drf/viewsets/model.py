"""
OData model viewsets for Django REST Framework.

Provides OData-enabled viewsets for Django model viewsets.
"""

from rest_framework import viewsets

from fc_selector.django.drf.mixins import ODataMixin
from fc_selector.django.drf.schema import ODataAutoSchema


class ODataModelViewSet(ODataMixin, viewsets.ReadOnlyModelViewSet):
    """
    OData-enabled ModelViewSet for READ-ONLY operations with OData support.

    **IMPORTANT: This viewset is READ-ONLY by design. It does NOT support write operations
    (POST, PUT, PATCH, DELETE). For read-only operations, use ODataReadOnlyModelViewSet for clarity.**

    Provides:
    - OData query parameter parsing and application
    - Read-only operations (List, Retrieve ONLY - NO Create, Update, Delete)
    - OData-formatted responses
    - Automatic queryset filtering based on OData parameters

    ## Supported OData Query Parameters

    - `$filter` - Filter: `?$filter=status eq 'published'`
    - `$select` - Select fields: `?$select=id,title`
    - `$expand` - Expand relations: `?$expand=author`
    - `$orderby` - Sort: `?$orderby=created_at desc`
    - `$top` - Limit: `?$top=10`
    - `$skip` - Offset: `?$skip=20`
    - `$count` - Count: `?$count=true`

    Example:
        class BlogPostViewSet(ODataModelViewSet):
            queryset = BlogPost.objects.all()
            serializer_class = BlogPostSerializer

            # Now supports OData queries:
            # GET /api/posts/?$filter=status eq 'published'&$orderby=created_at desc
            # GET /api/posts/?$select=id,title&$top=10&$count=true
            # GET /api/posts/?$expand=author($select=id,name)

    Note: This extends ReadOnlyModelViewSet, so POST, PUT, PATCH, DELETE are not available.
    """

    schema = ODataAutoSchema()


class ODataReadOnlyModelViewSet(ODataMixin, viewsets.ReadOnlyModelViewSet):
    """
    OData-enabled ReadOnlyModelViewSet for read-only operations with OData support.

    Provides:
    - OData query parameter parsing and application
    - Read-only operations (List, Retrieve)
    - OData-formatted responses
    - Automatic queryset filtering based on OData parameters

    ## Supported OData Query Parameters

    - `$filter` - Filter: `?$filter=status eq 'published'`
    - `$select` - Select fields: `?$select=id,title`
    - `$expand` - Expand relations: `?$expand=author`
    - `$orderby` - Sort: `?$orderby=created_at desc`
    - `$top` - Limit: `?$top=10`
    - `$skip` - Offset: `?$skip=20`
    - `$count` - Count: `?$count=true`

    Example:
        class BlogPostReadOnlyViewSet(ODataReadOnlyModelViewSet):
            queryset = BlogPost.objects.all()
            serializer_class = BlogPostSerializer

            # Now supports OData queries:
            # GET /api/posts/?$filter=status eq 'published'&$expand=author
            # GET /api/posts/{id}/?$select=id,title,content
            # GET /api/posts/?$top=10&$skip=20&$count=true
    """

    schema = ODataAutoSchema()
