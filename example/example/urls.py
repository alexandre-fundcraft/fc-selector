"""
Example project URL configuration.

Uses ODataSelector + ODataQueryBuilder + DTOs with automatic metadata generation.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from example.blog.selectors.blog_post import (
    AuthorSelector,
    BlogPostSelector,
    CategorySelector,
    UserSelector,
)
from example.blog.viewsets import (
    AuthorViewSet,
    BlogPostViewSet,
    CategoryViewSet,
    UserViewSet,
)
from fc_selector.django import (
    ODataMetadataRegistry,
    ODataMetadataView,
    ODataServiceDocumentView,
)

# Register selectors for automatic metadata generation
ODataMetadataRegistry.set_namespace("BlogService")
ODataMetadataRegistry.register("posts", BlogPostSelector)
ODataMetadataRegistry.register("authors", AuthorSelector)
ODataMetadataRegistry.register("users", UserSelector)
ODataMetadataRegistry.register("categories", CategorySelector)

# Create router and register viewsets
router = DefaultRouter()
router.register(r"posts", BlogPostViewSet, basename="blogpost")
router.register(r"authors", AuthorViewSet, basename="author")
router.register(r"users", UserViewSet, basename="user")
router.register(r"categories", CategoryViewSet, basename="category")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),

    # OpenAPI schema and documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # OData endpoints (automatic metadata generation)
    path("odata/$metadata", ODataMetadataView.as_view(), name="odata-metadata"),
    path("odata/", ODataServiceDocumentView.as_view(), name="odata-service-document"),
    path("odata/", include(router.urls)),

    path("api-auth/", include("rest_framework.urls")),
]
