"""
ViewSets using the Type-Safe Fluent API.

This version demonstrates the new fluent API with Field, avoiding string-based filters.
Compare with viewsets.py for the string-based approach.

Benefits of fluent API:
- Type-safe: IDE autocomplete and error detection
- No string escaping issues
- Composable with Python operators (&, |, ~)
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from fc_selector.core import QueryBuilder
from fc_selector.core.filters import Field
from fc_selector.django.drf import ODATA_PARAMETERS, ODATA_RETRIEVE_PARAMETERS
from fc_selector.django.drf.viewsets import ODataSelectorViewSetMixin, build_odata_response

from .dto_serializers import (
    AuthorDTOSerializer,
    BlogPostDTOSerializer,
    CategoryDTOSerializer,
    UserDTOSerializer,
)
from .selectors.blog_post import (
    AuthorSelector,
    BlogPostSelector,
    CategorySelector,
    UserSelector,
)


@extend_schema_view(
    list=extend_schema(tags=["posts"], parameters=ODATA_PARAMETERS),
    retrieve=extend_schema(tags=["posts"], parameters=ODATA_RETRIEVE_PARAMETERS),
    published=extend_schema(tags=["posts"], parameters=ODATA_PARAMETERS),
    featured=extend_schema(tags=["posts"], parameters=ODATA_PARAMETERS),
    by_author=extend_schema(tags=["posts"], parameters=ODATA_PARAMETERS),
    stats=extend_schema(tags=["posts"]),
)
class BlogPostViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    """
    Read-only ViewSet for BlogPost with OData support.

    Uses the type-safe fluent API for filters.
    """

    serializer_class = BlogPostDTOSerializer
    permission_classes = [AllowAny]
    selector_class = BlogPostSelector
    odata_entity_set_name = "posts"

    @action(detail=False, methods=["get"], url_path="published")
    def published(self, request):
        """Get only published posts."""
        query_string = request.META.get("QUERY_STRING", "")

        selector = BlogPostSelector()
        # Fluent API: Field("status").eq("published")
        query = QueryBuilder(query_string).and_where(Field("status").eq("published"))
        dtos = selector.get_many(query)

        serializer = self.get_serializer(dtos, many=True)
        return Response(
            build_odata_response(
                request=request,
                serializer_data=serializer.data,
                query_string=query_string,
                entity_set_name=self.odata_entity_set_name,
                selector=selector,
            )
        )

    @action(detail=False, methods=["get"], url_path="featured")
    def featured(self, request):
        """Get featured posts."""
        query_string = request.META.get("QUERY_STRING", "")

        selector = BlogPostSelector()
        # Fluent API: Field("featured").eq(True)
        query = QueryBuilder(query_string).and_where(Field("featured").eq(True))
        dtos = selector.get_many(query)

        serializer = self.get_serializer(dtos, many=True)
        return Response(
            build_odata_response(
                request=request,
                serializer_data=serializer.data,
                query_string=query_string,
                entity_set_name=self.odata_entity_set_name,
                selector=selector,
            )
        )

    @action(detail=False, methods=["get"], url_path="by-author/(?P<author_id>[^/.]+)")
    def by_author(self, request, author_id=None):
        """Get posts by specific author."""
        query_string = request.META.get("QUERY_STRING", "")

        selector = BlogPostSelector()
        # Fluent API: Field("author.id").eq(author_id) - nested field
        query = QueryBuilder(query_string).and_where(Field("author.id").eq(int(author_id)))
        dtos = selector.get_many(query)

        serializer = self.get_serializer(dtos, many=True)
        return Response(
            build_odata_response(
                request=request,
                serializer_data=serializer.data,
                query_string=query_string,
                entity_set_name=self.odata_entity_set_name,
                selector=selector,
            )
        )

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        """Get post statistics."""
        selector = BlogPostSelector()
        # Fluent API with chaining
        query = (
            QueryBuilder()
            .select("id,title,view_count,word_count,status,is_published,created_at,published_at")
            .and_where(Field("id").eq(int(pk)))
        )

        dto = selector.get_one(query)

        if dto is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        from .viewset_utils import build_stats_response

        stats = build_stats_response(dto)

        return Response(stats)


@extend_schema_view(
    list=extend_schema(tags=["authors"], parameters=ODATA_PARAMETERS),
    retrieve=extend_schema(tags=["authors"], parameters=ODATA_RETRIEVE_PARAMETERS),
    posts=extend_schema(tags=["authors"], parameters=ODATA_PARAMETERS),
)
class AuthorViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    """ViewSet for Authors with OData support."""

    serializer_class = AuthorDTOSerializer
    permission_classes = [AllowAny]
    selector_class = AuthorSelector
    odata_entity_set_name = "authors"

    @action(detail=True, methods=["get"])
    def posts(self, request, pk=None):
        """Get all posts by this author."""
        # Verify author exists using fluent API
        if not AuthorSelector().exists_by(QueryBuilder().and_where(Field("id").eq(int(pk)))):
            return Response({"detail": "Author not found."}, status=status.HTTP_404_NOT_FOUND)

        from .viewset_utils import build_related_items_response

        query_string = request.META.get("QUERY_STRING", "")
        selector = BlogPostSelector()
        # Fluent API: nested field
        query = QueryBuilder(query_string).and_where(Field("author.id").eq(int(pk)))
        dtos = selector.get_many(query)

        return build_related_items_response(request, dtos, BlogPostDTOSerializer, "posts", selector)


@extend_schema_view(
    list=extend_schema(tags=["users"], parameters=ODATA_PARAMETERS),
    retrieve=extend_schema(tags=["users"], parameters=ODATA_RETRIEVE_PARAMETERS),
    active=extend_schema(tags=["users"], parameters=ODATA_PARAMETERS),
    me=extend_schema(tags=["users"], parameters=ODATA_RETRIEVE_PARAMETERS),
)
class UserViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    """ViewSet for Users with OData support."""

    serializer_class = UserDTOSerializer
    permission_classes = [IsAuthenticated]
    selector_class = UserSelector
    odata_entity_set_name = "users"

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get only active users."""
        from .viewset_utils import build_related_items_response

        query_string = request.META.get("QUERY_STRING", "")
        selector = UserSelector()
        # Fluent API: boolean field
        query = QueryBuilder(query_string).and_where(Field("is_active").eq(True))
        dtos = selector.get_many(query)

        return build_related_items_response(request, dtos, self.serializer_class, "users", selector)

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Get current authenticated user."""
        query_string = request.META.get("QUERY_STRING", "")

        selector = UserSelector()
        # Fluent API: dynamic value from request
        query = QueryBuilder(query_string).and_where(Field("id").eq(request.user.pk))
        dto = selector.get_one(query)

        if dto is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(dto)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(tags=["categories"], parameters=ODATA_PARAMETERS),
    retrieve=extend_schema(tags=["categories"], parameters=ODATA_RETRIEVE_PARAMETERS),
    posts=extend_schema(tags=["categories"], parameters=ODATA_PARAMETERS),
)
class CategoryViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    """Read-only ViewSet for Categories with OData support."""

    serializer_class = CategoryDTOSerializer
    permission_classes = [AllowAny]
    selector_class = CategorySelector
    odata_entity_set_name = "categories"

    @action(detail=True, methods=["get"])
    def posts(self, request, pk=None):
        """Get all posts in this category."""
        # Verify category exists
        if not CategorySelector().exists_by(QueryBuilder().and_where(Field("id").eq(int(pk)))):
            return Response({"detail": "Category not found."}, status=status.HTTP_404_NOT_FOUND)

        query_string = request.META.get("QUERY_STRING", "")

        selector = BlogPostSelector()
        # Note: Collection lambda operations (any/all) require OData string syntax.
        # The fluent API currently supports simple field operations but not lambda expressions.
        # This is a limitation of the current fluent API design.
        query = QueryBuilder(query_string).and_filter(f"categories/any(c: c/id eq {pk})")
        dtos = selector.get_many(query)

        serializer = BlogPostDTOSerializer(dtos, many=True)
        return Response(
            build_odata_response(
                request=request,
                serializer_data=serializer.data,
                query_string=query_string,
                entity_set_name="posts",
                selector=selector,
            )
        )
