"""
FC Selector - DDD Selector/Query pattern for Django with OData query support.

The package is layered so that only the last layer knows about Django:

1. Core (fc_selector.core):
   - AST, QueryIntent, fluent filters, QueryBuilder and DTOs
   - Framework-agnostic: importing it never loads Django

2. Protocols (fc_selector.protocols):
   - OData query language: parses query strings into a QueryIntent
   - Framework-agnostic

3. Django (fc_selector.django):
   - Executes a QueryIntent on Django QuerySets, selector pattern,
     DRF viewset mixin, DTO serializer and $metadata views

Example Usage:

    # Parse an OData query string (no Django required)
    from fc_selector.protocols.odata import parse_odata_query
    intent = parse_odata_query("$filter=status eq 'published'&$expand=author")

    # Build the same intent programmatically
    from fc_selector.core import QueryBuilder
    from fc_selector.core.filters import Field
    intent = QueryBuilder().where(Field("status").eq("published")).expand("author").build()

    # Selector pattern
    from fc_selector.django.selector import ODataSelector
    class BlogPostSelector(ODataSelector):
        class Meta:
            model = BlogPost
            dto_class = BlogPostDTO
    posts = BlogPostSelector().query_as_dtos("$filter=status eq 'published'")

    # DRF viewset integration
    from fc_selector.django.drf.viewsets import ODataSelectorViewSetMixin

Note:
    This __init__.py intentionally imports nothing, so that fc_selector.core and
    fc_selector.protocols stay importable without Django installed.
"""

__version__ = "1.0.1"

__all__: list[str] = []
