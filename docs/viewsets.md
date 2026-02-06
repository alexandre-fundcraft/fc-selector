<!-- markdownlint-disable MD024 -->
# ViewSets Integration

Expose your selectors as REST API endpoints using Django REST Framework.

## ODataSelectorViewSetMixin

The mixin provides `list()` and `retrieve()` actions with OData support:

```python
from rest_framework import viewsets
from fc_selector.django.drf.viewsets import ODataSelectorViewSetMixin
from fc_selector.django.drf.serializers import ODataDTOSerializer

class BlogPostDTOSerializer(ODataDTOSerializer):
    class Meta:
        dto_class = BlogPostDTO

class BlogPostViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    serializer_class = BlogPostDTOSerializer
    selector_class = BlogPostSelector
```

This enables:

```bash
GET /api/posts/                              # List all
GET /api/posts/1/                            # Get by ID
GET /api/posts/?$filter=status eq 'published' # Filter
GET /api/posts/?$select=id,title             # Select fields
GET /api/posts/?$expand=author               # Expand relations
GET /api/posts/?$orderby=created_at desc     # Sort
GET /api/posts/?$top=10&$skip=20             # Paginate
```

## Custom Actions

Add custom endpoints that combine OData with business logic:

```python
from rest_framework.decorators import action
from rest_framework.response import Response
from fc_selector.django.selector import QueryBuilder

class BlogPostViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    serializer_class = BlogPostDTOSerializer
    selector_class = BlogPostSelector

    @action(detail=False, methods=['get'])
    def published(self, request):
        """GET /api/posts/published/"""
        query = QueryBuilder(request.META.get('QUERY_STRING', ''))
        query.and_filter("status eq 'published'")

        dtos = BlogPostSelector().get_many(query)
        serializer = self.get_serializer(dtos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """GET /api/posts/featured/"""
        query = QueryBuilder(request.META.get('QUERY_STRING', ''))
        query.and_filter("featured eq true")
        query.orderby("created_at desc")

        dtos = BlogPostSelector().get_many(query)
        serializer = self.get_serializer(dtos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='by-author/(?P<author_id>[^/.]+)')
    def by_author(self, request, author_id=None):
        """GET /api/posts/by-author/1/"""
        query = QueryBuilder(request.META.get('QUERY_STRING', ''))
        query.and_filter(f"author/id eq {author_id}")

        dtos = BlogPostSelector().get_many(query)
        serializer = self.get_serializer(dtos, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """GET /api/posts/1/stats/"""
        query = (
            QueryBuilder()
            .select('id', 'title', 'view_count', 'word_count')
            .and_filter(f"id eq {pk}")
        )

        dto = BlogPostSelector().get_one(query)
        if not dto:
            return Response({'detail': 'Not found'}, status=404)

        return Response({
            'id': dto.id,
            'title': dto.title,
            'view_count': dto.view_count,
            'word_count': dto.word_count,
        })
```

## URL Configuration

```python
from rest_framework.routers import DefaultRouter
from .viewsets import BlogPostViewSet, AuthorViewSet

router = DefaultRouter()
router.register('posts', BlogPostViewSet, basename='posts')
router.register('authors', AuthorViewSet, basename='authors')

urlpatterns = [
    path('api/', include(router.urls)),
]
```

## Complete ViewSet Example

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from fc_selector.django.selector import QueryBuilder
from fc_selector.django.drf.viewsets import ODataSelectorViewSetMixin
from fc_selector.django.drf.serializers import ODataDTOSerializer

from .selectors.blog_post import BlogPostSelector, BlogPostDTO

class BlogPostDTOSerializer(ODataDTOSerializer):
    class Meta:
        dto_class = BlogPostDTO

class BlogPostViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    """
    Read-only ViewSet for BlogPost.

    Endpoints:
        GET /api/posts/              - List all posts
        GET /api/posts/{id}/         - Get single post
        GET /api/posts/published/    - Published posts only
        GET /api/posts/featured/     - Featured posts only
    """
    serializer_class = BlogPostDTOSerializer
    selector_class = BlogPostSelector
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def published(self, request):
        query = QueryBuilder(request.META.get('QUERY_STRING', ''))
        query.and_filter("status eq 'published'")
        dtos = BlogPostSelector().get_many(query)
        return Response(self.get_serializer(dtos, many=True).data)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        query = QueryBuilder(request.META.get('QUERY_STRING', ''))
        query.and_filter("featured eq true")
        dtos = BlogPostSelector().get_many(query)
        return Response(self.get_serializer(dtos, many=True).data)
```

## Cross-Entity Queries

Query related entities from parent endpoints:

```python
class AuthorViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    serializer_class = AuthorDTOSerializer
    selector_class = AuthorSelector

    @action(detail=True, methods=['get'])
    def posts(self, request, pk=None):
        """GET /api/authors/1/posts/"""
        # Verify author exists
        if not AuthorSelector().exists_by(
            QueryBuilder().and_filter(f"id eq {pk}")
        ):
            return Response({'detail': 'Author not found'}, status=404)

        # Get author's posts with OData support
        query = QueryBuilder(request.META.get('QUERY_STRING', ''))
        query.and_filter(f"author/id eq {pk}")

        dtos = BlogPostSelector().get_many(query)
        serializer = BlogPostDTOSerializer(dtos, many=True)
        return Response(serializer.data)


class CategoryViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    serializer_class = CategoryDTOSerializer
    selector_class = CategorySelector

    @action(detail=True, methods=['get'])
    def posts(self, request, pk=None):
        """GET /api/categories/1/posts/"""
        # ManyToMany: use any() in filter
        query = QueryBuilder(request.META.get('QUERY_STRING', ''))
        query.and_filter(f"categories/any(c: c/id eq {pk})")

        dtos = BlogPostSelector().get_many(query)
        serializer = BlogPostDTOSerializer(dtos, many=True)
        return Response(serializer.data)
```

## OpenAPI / Swagger Documentation

FC Selector provides pre-defined OData parameters for `drf-spectacular` to document your API.

### Setup

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'My API',
    'VERSION': '1.0.0',
}
```

### Adding OData Parameters to Swagger

Import and use `ODATA_PARAMETERS` with `@extend_schema`:

```python
from drf_spectacular.utils import extend_schema, extend_schema_view
from fc_selector.django.drf import ODATA_PARAMETERS, ODATA_RETRIEVE_PARAMETERS

@extend_schema_view(
    list=extend_schema(parameters=ODATA_PARAMETERS),
    retrieve=extend_schema(parameters=ODATA_RETRIEVE_PARAMETERS),
)
class BlogPostViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    serializer_class = BlogPostDTOSerializer
    selector_class = BlogPostSelector
```

### Available Parameter Sets

| Import | Parameters | Use for |
|--------|------------|---------|
| `ODATA_PARAMETERS` | All 7 parameters | `list` actions |
| `ODATA_RETRIEVE_PARAMETERS` | `$select`, `$expand` | `retrieve` actions |

### Custom Actions

Add OData parameters to custom actions:

```python
from drf_spectacular.utils import extend_schema
from fc_selector.django.drf import ODATA_PARAMETERS

class BlogPostViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):

    @extend_schema(parameters=ODATA_PARAMETERS)
    @action(detail=False, methods=['get'])
    def published(self, request):
        ...
```

### Complete Example with Swagger

```python
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from fc_selector.django.selector import QueryBuilder
from fc_selector.django.drf.viewsets import ODataSelectorViewSetMixin
from fc_selector.django.drf import ODATA_PARAMETERS, ODATA_RETRIEVE_PARAMETERS

@extend_schema_view(
    list=extend_schema(
        parameters=ODATA_PARAMETERS,
        description="List posts with OData filtering, sorting, and pagination.",
    ),
    retrieve=extend_schema(
        parameters=ODATA_RETRIEVE_PARAMETERS,
        description="Get a single post. Supports $select and $expand.",
    ),
)
class BlogPostViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    serializer_class = BlogPostDTOSerializer
    selector_class = BlogPostSelector

    @extend_schema(parameters=ODATA_PARAMETERS)
    @action(detail=False, methods=['get'])
    def published(self, request):
        """List published posts only."""
        query = QueryBuilder(request.META.get('QUERY_STRING', ''))
        query.and_filter("status eq 'published'")
        dtos = self.selector_class().get_many(query)
        return Response(self.get_serializer(dtos, many=True).data)
```

### Documented Parameters in Swagger

Each parameter includes:

- **$filter** - OData filter syntax with operators and examples
- **$select** - Comma-separated field list
- **$expand** - Relations to eager load
- **$orderby** - Sort fields with asc/desc
- **$top** - Limit results
- **$skip** - Offset for pagination
- **$count** - Include total count

## Read-Only by Design

ViewSets using `ODataSelectorViewSetMixin` are **read-only**:

- No `create()`, `update()`, `partial_update()`, `destroy()` methods
- Write operations should use repositories, not selectors
- This follows the Selector pattern from DDD

If you need write operations, use a separate repository:

```python
class BlogPostViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    # Read operations via selector
    selector_class = BlogPostSelector

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        # Write via repository (not selector)
        repository = BlogPostRepository()
        repository.update(pk, status='published')

        # Return updated data via selector
        dto = BlogPostSelector().get_by_pk(pk)
        return Response(self.get_serializer(dto).data)
```
