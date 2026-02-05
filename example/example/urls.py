"""
Example project URL configuration.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from fc_selector.django import ODataMetadataView, ODataServiceDocumentView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Blog API
    path("api/", include("example.blog.urls")),
    # OpenAPI schema and documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # OData endpoints
    path("odata/$metadata", ODataMetadataView.as_view(), name="odata-metadata"),
    path("odata/", ODataServiceDocumentView.as_view(), name="odata-service-document"),
    path("odata/", include("example.blog.urls")),
    # DRF auth
    path("api-auth/", include("rest_framework.urls")),
]
