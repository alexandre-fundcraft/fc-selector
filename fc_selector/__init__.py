"""
Django OData - Framework-agnostic OData implementation for Django.

This package provides a clean, layered architecture for OData support:

1. Core Layer (django_odata.core):
   - Framework-agnostic AST, query parsing and filtering
   - Reusable in FastAPI, Flask, or any Python framework
   - NO Django dependencies

2. Django Layer (django_odata.django):
   - Django ORM-specific implementations
   - Query application, optimization, and selector pattern

3. DRF Layer (django_odata.drf):
   - Django REST Framework integration
   - Mixins, viewsets, and serializers with OData support

4. Utils Layer (django_odata.utils):
   - Shared utilities and exceptions

Example Usage:

    # Framework-agnostic AST (no Django required)
    from django_odata.core.parsers.filter.ast import nodes, visitor
    ast_node = nodes.Compare(comparator=nodes.Eq(), ...)

    # Framework-agnostic query parsing
    from django_odata.core.parsers.query import parse_odata_query
    query = parse_odata_query("$filter=status eq 'published'&$expand=author")

    # Django query application
    from django_odata.django.query import apply_odata_query_params
    queryset = apply_odata_query_params(BlogPost.objects.all(), query.to_dict())

    # DRF viewset integration
    from django_odata.drf.viewsets import ODataModelViewSet
    class BlogPostViewSet(ODataModelViewSet):
        queryset = BlogPost.objects.all()
        serializer_class = BlogPostSerializer

    # Selector pattern
    from django_odata.django.selector import ODataSelector
    selector = ODataSelector(BlogPost)
    posts = selector.query("$filter=status eq 'published'")

Note:
    This __init__.py intentionally does NOT import anything to keep the package
    framework-agnostic. Import only what you need from submodules:
    - django_odata.core.* (no Django required)
    - django_odata.django.* (requires Django)
    - django_odata.drf.* (requires Django REST Framework)
"""

__version__ = "2.0.0"

# NO imports here! Keep the package framework-agnostic.
# Users should import directly from submodules:
#   from django_odata.core.parsers.filter.ast import nodes
#   from django_odata.core.parsers.query import parse_odata_query
#   from django_odata.django.query import apply_odata_query_params
#   etc.

__all__: list[str] = []
