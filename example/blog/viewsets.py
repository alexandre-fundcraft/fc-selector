"""
ViewSets using the String-Based API.

This version uses string-based filters like:
    QueryBuilder(query_string).and_filter("status eq 'published'")

See viewsets_fluent.py for the type-safe fluent API version:
    QueryBuilder(query_string).and_where(Field("status").eq("published"))
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from fc_selector.core import QueryBuilder
from fc_selector.django.drf import ODATA_PARAMETERS, ODATA_RETRIEVE_PARAMETERS
from fc_selector.django.drf.viewsets import ODataSelectorViewSetMixin, build_odata_response

from .dto_serializers import (
    AuthorDTOSerializer,
    BlogPostDTOSerializer,
    CategoryDTOSerializer,
    CommentDTOSerializer,
    TagDTOSerializer,
    UserDTOSerializer,
)
from .selectors.blog_post import (
    AuthorSelector,
    BlogPostSelector,
    CategorySelector,
    CommentSelector,
    TagSelector,
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

    Endpoints:
        GET    /api/posts/                         - List all posts
        GET    /api/posts/{id}/                    - Retrieve single post
        GET    /api/posts/published/               - List published posts
        GET    /api/posts/featured/                - List featured posts
        GET    /api/posts/by-author/{id}/          - Posts by author
        GET    /api/posts/{id}/stats/              - Post statistics

    Example OData requests:
        GET /api/posts/?$select=id,title,status
        GET /api/posts/?$expand=author,categories
        GET /api/posts/?$filter=status eq 'published' and featured eq true
        GET /api/posts/?$orderby=created_at desc
        GET /api/posts/?$top=10&$skip=20
    """

    serializer_class = BlogPostDTOSerializer
    permission_classes = [AllowAny]
    selector_class = BlogPostSelector
    odata_entity_set_name = "posts"

    @action(detail=False, methods=["get"], url_path="published")
    def published(self, request):
        """
        Get only published posts.

        Example:
            GET /api/posts/published/?$select=id,title&$orderby=published_at desc
        """
        query_string = request.META.get("QUERY_STRING", "")

        selector = BlogPostSelector()
        query = QueryBuilder(query_string).and_filter("status eq 'published'")
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
        """
        Get featured posts.

        Example:
            GET /api/posts/featured/?$top=5
        """
        query_string = request.META.get("QUERY_STRING", "")

        selector = BlogPostSelector()
        query = QueryBuilder(query_string).and_filter("featured eq true")
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
        """
        Get posts by specific author.

        Example:
            GET /api/posts/by-author/1/?$select=id,title&$orderby=created_at desc
        """
        query_string = request.META.get("QUERY_STRING", "")

        selector = BlogPostSelector()
        query = QueryBuilder(query_string).and_filter(f"author/id eq {author_id}")
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
        """
        Get post statistics.

        Example:
            GET /api/posts/1/stats/
        """
        selector = BlogPostSelector()
        # Select only fields needed for stats
        query = (
            QueryBuilder()
            .select("id,title,view_count,word_count,status,is_published,created_at,published_at")
            .and_filter(f"id eq {pk}")
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
    """
    ViewSet for Authors with OData support.

    Endpoints:
        GET /api/authors/                      - List all authors
        GET /api/authors/{id}/                 - Retrieve single author
        GET /api/authors/{id}/posts/           - Get author's posts

    Example requests:
        GET /api/authors/?$select=id,name,email
        GET /api/authors/?$expand=user
        GET /api/authors/1/?$expand=user
    """

    serializer_class = AuthorDTOSerializer
    permission_classes = [AllowAny]
    selector_class = AuthorSelector
    odata_entity_set_name = "authors"

    @action(detail=True, methods=["get"])
    def posts(self, request, pk=None):
        """
        Get all posts by this author.

        Example:
            GET /api/authors/1/posts/?$select=id,title,status&$filter=status eq 'published'
        """
        # Verify author exists
        if not AuthorSelector().exists_by(QueryBuilder().and_filter(f"id eq {pk}")):
            return Response({"detail": "Author not found."}, status=status.HTTP_404_NOT_FOUND)

        from .viewset_utils import build_related_items_response

        query_string = request.META.get("QUERY_STRING", "")
        selector = BlogPostSelector()
        query = QueryBuilder(query_string).and_filter(f"author/id eq {pk}")
        dtos = selector.get_many(query)

        return build_related_items_response(request, dtos, BlogPostDTOSerializer, "posts", selector)


@extend_schema_view(
    list=extend_schema(tags=["users"], parameters=ODATA_PARAMETERS),
    retrieve=extend_schema(tags=["users"], parameters=ODATA_RETRIEVE_PARAMETERS),
    active=extend_schema(tags=["users"], parameters=ODATA_PARAMETERS),
    me=extend_schema(tags=["users"], parameters=ODATA_RETRIEVE_PARAMETERS),
)
class UserViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    """
    ViewSet for Users with OData support.

    IMPORTANT: Password is automatically excluded by UserDTOSerializer!

    Endpoints:
        GET /api/users/                        - List all users
        GET /api/users/{id}/                   - Retrieve single user
        GET /api/users/active/                 - List active users
        GET /api/users/me/                     - Get current user

    Example requests:
        GET /api/users/?$select=id,username,email
        GET /api/users/?$filter=is_active eq true
    """

    serializer_class = UserDTOSerializer
    permission_classes = [IsAuthenticated]
    selector_class = UserSelector
    odata_entity_set_name = "users"

    @action(detail=False, methods=["get"])
    def active(self, request):
        """
        Get only active users.

        Example:
            GET /api/users/active/?$select=id,username
        """
        from .viewset_utils import build_related_items_response

        query_string = request.META.get("QUERY_STRING", "")
        selector = UserSelector()
        query = QueryBuilder(query_string).and_filter("is_active eq true")
        dtos = selector.get_many(query)

        return build_related_items_response(request, dtos, self.serializer_class, "users", selector)

    @action(detail=False, methods=["get"])
    def me(self, request):
        """
        Get current authenticated user.

        Example:
            GET /api/users/me/?$select=id,username,email
        """
        query_string = request.META.get("QUERY_STRING", "")

        selector = UserSelector()
        query = QueryBuilder(query_string).and_filter(f"id eq {request.user.pk}")
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
    """
    Read-only ViewSet for Categories with OData support.

    Endpoints:
        GET    /api/categories/              - List all categories
        GET    /api/categories/{id}/         - Retrieve category
        GET    /api/categories/{id}/posts/   - Get posts in category
    """

    serializer_class = CategoryDTOSerializer
    permission_classes = [AllowAny]
    selector_class = CategorySelector
    odata_entity_set_name = "categories"

    @action(detail=True, methods=["get"])
    def posts(self, request, pk=None):
        """
        Get all posts in this category.

        Example:
            GET /api/categories/1/posts/?$select=id,title&$filter=status eq 'published'
        """
        # Verify category exists
        if not CategorySelector().exists_by(QueryBuilder().and_filter(f"id eq {pk}")):
            return Response({"detail": "Category not found."}, status=status.HTTP_404_NOT_FOUND)

        query_string = request.META.get("QUERY_STRING", "")

        selector = BlogPostSelector()
        # Note: For M2M relationship, we need to filter differently
        # This assumes the OData parser supports this syntax
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


@extend_schema_view(
    list=extend_schema(tags=["comments"], parameters=ODATA_PARAMETERS),
    retrieve=extend_schema(tags=["comments"], parameters=ODATA_RETRIEVE_PARAMETERS),
    by_post=extend_schema(tags=["comments"], parameters=ODATA_PARAMETERS),
    approved=extend_schema(tags=["comments"], parameters=ODATA_PARAMETERS),
)
class CommentViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    """
    ViewSet for Comments with OData support.

    The 'post' expand uses BlogPostSummaryDTO (DB fields only),
    which enables hybrid values mode for faster queries.

    Endpoints:
        GET /api/comments/                      - List all comments
        GET /api/comments/{id}/                 - Retrieve single comment
        GET /api/comments/by-post/{id}/         - Comments on a specific post
        GET /api/comments/approved/             - List approved comments

    Example OData requests:
        GET /api/comments/?$expand=post
        GET /api/comments/?$select=id,author_name,content
        GET /api/comments/?$filter=is_approved eq true
        GET /api/comments/?$expand=post($select=id,title)
    """

    serializer_class = CommentDTOSerializer
    permission_classes = [AllowAny]
    selector_class = CommentSelector
    odata_entity_set_name = "comments"

    @action(detail=False, methods=["get"], url_path="by-post/(?P<post_id>[^/.]+)")
    def by_post(self, request, post_id=None):
        """
        Get comments for a specific post.

        Example:
            GET /api/comments/by-post/1/?$expand=post&$filter=is_approved eq true
        """
        query_string = request.META.get("QUERY_STRING", "")

        selector = CommentSelector()
        query = QueryBuilder(query_string).and_filter(f"post/id eq {post_id}")
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

    @action(detail=False, methods=["get"])
    def approved(self, request):
        """
        Get only approved comments.

        Example:
            GET /api/comments/approved/?$expand=post&$orderby=created_at desc
        """
        query_string = request.META.get("QUERY_STRING", "")

        selector = CommentSelector()
        query = QueryBuilder(query_string).and_filter("is_approved eq true")
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


@extend_schema_view(
    list=extend_schema(tags=["tags"], parameters=ODATA_PARAMETERS),
    retrieve=extend_schema(tags=["tags"], parameters=ODATA_RETRIEVE_PARAMETERS),
)
class TagViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    """
    Read-only ViewSet for Tags with OData support.

    Endpoints:
        GET /api/tags/              - List all tags
        GET /api/tags/{id}/         - Retrieve tag
    """

    serializer_class = TagDTOSerializer
    permission_classes = [AllowAny]
    selector_class = TagSelector
    odata_entity_set_name = "tags"
