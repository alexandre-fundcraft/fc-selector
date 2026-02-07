"""
Blog app URL configuration.

Registers all blog-related viewsets and OData metadata.
"""

from rest_framework.routers import DefaultRouter

from fc_selector.django import ODataMetadataRegistry

from .selectors.blog_post import (
    AuthorSelector,
    BlogPostSelector,
    CategorySelector,
    CommentSelector,
    TagSelector,
    UserSelector,
)
from .viewsets_fluent import (
    AuthorViewSet,
    BlogPostViewSet,
    CategoryViewSet,
    CommentViewSet,
    TagViewSet,
    UserViewSet,
)

# Register selectors for automatic metadata generation
ODataMetadataRegistry.set_namespace("BlogService")
ODataMetadataRegistry.register("posts", BlogPostSelector)
ODataMetadataRegistry.register("authors", AuthorSelector)
ODataMetadataRegistry.register("users", UserSelector)
ODataMetadataRegistry.register("categories", CategorySelector)
ODataMetadataRegistry.register("comments", CommentSelector)
ODataMetadataRegistry.register("tags", TagSelector)

# Create router and register viewsets
router = DefaultRouter()
router.register(r"posts", BlogPostViewSet, basename="blogpost")
router.register(r"authors", AuthorViewSet, basename="author")
router.register(r"users", UserViewSet, basename="user")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"comments", CommentViewSet, basename="comment")
router.register(r"tags", TagViewSet, basename="tag")

urlpatterns = router.urls
