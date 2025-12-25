# ViewSet Examples - Complete Guide

This guide shows complete examples of using ODataSelector + QueryBuilder + DTOs in ViewSets.

## Table of Contents
1. [Quick Start](#quick-start)
2. [QueryBuilder](#odataquerybuilder)
3. [Complete ViewSet Examples](#complete-viewset-examples)
4. [Custom Actions](#custom-actions)
5. [Request Examples](#request-examples)
6. [Response Examples](#response-examples)

---

## Quick Start

### 1. Setup (Already Done)

```bash
# Generate DTOs and Selectors
python manage.py generate_odata_selector blog.BlogPost --single --force
```

### 2. Register URLs

```python
# example/blog/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import BlogPostViewSet, AuthorViewSet

router = DefaultRouter()
router.register(r'blog-posts', BlogPostViewSet, basename='blogpost')
router.register(r'authors', AuthorViewSet, basename='author')

urlpatterns = [
    path('api/', include(router.urls)),
]
```

### 3. Include in Main URLs

```python
# example/urls.py
from django.urls import path, include

urlpatterns = [
    path('', include('blog.urls')),
]
```

---

## QueryBuilder

The `QueryBuilder` is a fluent builder for constructing OData queries programmatically. It's part of the core layer and has no framework dependencies.

### Basic Usage

```python
from fc_odata.core import QueryBuilder

# Build a query from scratch
query = (
    QueryBuilder()
    .filter("status eq 'published'")
    .select("id", "title", "author")
    .expand("author")
    .orderby("created_at desc")
    .top(10)
)

# Get the OData query string
print(query.build_query_string())
# Output: $filter=status eq 'published'&$select=id,title,author&$expand=author&$orderby=created_at desc&$top=10
```

### Parsing Existing Query Strings

When receiving a request with an OData query string, use `from_query_string()`:

```python
# Parse query string from request
query_string = request.META.get('QUERY_STRING', '')
query = QueryBuilder.from_query_string(query_string)

# Add additional filters programmatically
query.and_filter(f"id eq {pk}")
```

### Filter Methods

```python
# Set filter (replaces existing)
query.filter("status eq 'published'")

# Add AND condition
query.and_filter("featured eq true")
# Result: $filter=(status eq 'published') and (featured eq true)

# Add OR condition
query.or_filter("status eq 'draft'")
# Result: $filter=(previous) or (status eq 'draft')
```

### All Available Methods

| Method | Description | Example |
|--------|-------------|---------|
| `filter(expr)` | Set $filter | `query.filter("status eq 'active'")` |
| `and_filter(expr)` | Add AND condition | `query.and_filter("id eq 5")` |
| `or_filter(expr)` | Add OR condition | `query.or_filter("featured eq true")` |
| `select(*fields)` | Set $select | `query.select("id", "name")` |
| `expand(*relations)` | Set $expand | `query.expand("author", "categories")` |
| `orderby(*fields)` | Set $orderby | `query.orderby("created_at desc")` |
| `top(n)` | Set $top | `query.top(10)` |
| `skip(n)` | Set $skip | `query.skip(20)` |
| `count(bool)` | Set $count | `query.count(True)` |

---

## Complete ViewSet Examples

### Basic ViewSet (Read-Only)

```python
from rest_framework import viewsets
from rest_framework.response import Response

from fc_odata.core import QueryBuilder

from .selectors.blog_post import AuthorSelector
from .dto_serializers import AuthorDTOSerializer


class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    """Simple read-only ViewSet with OData support."""

    serializer_class = AuthorDTOSerializer

    def list(self, request, *args, **kwargs):
        """List all authors with OData support."""
        query_string = request.META.get('QUERY_STRING', '')

        selector = AuthorSelector()
        query = QueryBuilder.from_query_string(query_string)
        dtos = selector.get_many(query)

        serializer = self.get_serializer(dtos, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """Retrieve single author with OData support."""
        query_string = request.META.get('QUERY_STRING', '')

        selector = AuthorSelector()
        query = QueryBuilder.from_query_string(query_string).and_filter(f"id eq {pk}")
        dto = selector.get_one(query)

        if dto is None:
            return Response({'detail': 'Not found.'}, status=404)

        serializer = self.get_serializer(dto)
        return Response(serializer.data)
```

### Full CRUD ViewSet

```python
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from fc_odata.core import QueryBuilder


class BlogPostViewSet(viewsets.ModelViewSet):
    """Full CRUD ViewSet with OData support."""

    serializer_class = BlogPostDTOSerializer

    def get_queryset(self):
        return BlogPost.objects.all()

    def list(self, request, *args, **kwargs):
        """List with OData support."""
        query_string = request.META.get('QUERY_STRING', '')

        selector = BlogPostSelector()
        query = QueryBuilder.from_query_string(query_string)
        dtos = selector.get_many(query)

        serializer = self.get_serializer(dtos, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """Retrieve single post with OData support."""
        query_string = request.META.get('QUERY_STRING', '')

        selector = BlogPostSelector()
        query = QueryBuilder.from_query_string(query_string).and_filter(f"id eq {pk}")
        dto = selector.get_one(query)

        if dto is None:
            return Response({'detail': 'Not found.'}, status=404)

        serializer = self.get_serializer(dto)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Create new post."""
        data = request.data
        post = BlogPost.objects.create(
            title=data.get('title'),
            content=data.get('content'),
            status=data.get('status', 'draft'),
            author_id=data.get('author'),
        )

        selector = BlogPostSelector()
        dto = selector.get_by_pk(post.id)
        serializer = self.get_serializer(dto)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None, *args, **kwargs):
        """Update post (PUT)."""
        instance = get_object_or_404(BlogPost, pk=pk)

        data = request.data
        instance.title = data.get('title', instance.title)
        instance.content = data.get('content', instance.content)
        instance.status = data.get('status', instance.status)
        instance.save()

        selector = BlogPostSelector()
        dto = selector.get_by_pk(instance.id)
        serializer = self.get_serializer(dto)

        return Response(serializer.data)

    def partial_update(self, request, pk=None, *args, **kwargs):
        """Partial update (PATCH)."""
        instance = get_object_or_404(BlogPost, pk=pk)

        data = request.data
        for field, value in data.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        instance.save()

        selector = BlogPostSelector()
        dto = selector.get_by_pk(instance.id)
        serializer = self.get_serializer(dto)

        return Response(serializer.data)

    def destroy(self, request, pk=None, *args, **kwargs):
        """Delete post."""
        instance = get_object_or_404(BlogPost, pk=pk)
        instance.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
```

---

## Custom Actions

### Filter by Status

```python
from rest_framework.decorators import action

from fc_odata.core import QueryBuilder


class BlogPostViewSet(viewsets.ModelViewSet):

    @action(detail=False, methods=['get'], url_path='published')
    def published(self, request):
        """
        Get only published posts.

        Example: GET /api/blog-posts/published/
        """
        query_string = request.META.get('QUERY_STRING', '')

        selector = BlogPostSelector()
        # Parse existing query and add status filter
        query = QueryBuilder.from_query_string(query_string).and_filter("status eq 'published'")
        dtos = selector.get_many(query)

        serializer = self.get_serializer(dtos, many=True)
        return Response(serializer.data)
```

### Action with Path Parameter

```python
@action(detail=False, methods=['get'], url_path='by-author/(?P<author_id>[^/.]+)')
def by_author(self, request, author_id=None):
    """
    Get posts by specific author.

    Example: GET /api/blog-posts/by-author/1/
    """
    query_string = request.META.get('QUERY_STRING', '')

    selector = BlogPostSelector()
    query = QueryBuilder.from_query_string(query_string).and_filter(f"author/id eq {author_id}")
    dtos = selector.get_many(query)

    serializer = self.get_serializer(dtos, many=True)
    return Response(serializer.data)
```

### Action that Modifies Data

```python
@action(detail=True, methods=['post'])
def publish(self, request, pk=None):
    """
    Publish a draft post.

    Example: POST /api/blog-posts/1/publish/
    """
    from django.utils import timezone

    instance = get_object_or_404(BlogPost, pk=pk)

    if instance.status == 'published':
        return Response(
            {'detail': 'Post is already published.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    instance.status = 'published'
    instance.published_at = timezone.now()
    instance.save()

    selector = BlogPostSelector()
    dto = selector.get_by_pk(instance.id)
    serializer = self.get_serializer(dto)

    return Response(serializer.data)
```

### Related Objects Action

```python
@action(detail=True, methods=['get'])
def posts(self, request, pk=None):
    """
    Get all posts by this author.

    Example: GET /api/authors/1/posts/
    """
    # Verify author exists
    if not AuthorSelector().exists_by(QueryBuilder().and_filter(f"id eq {pk}")):
        return Response({'detail': 'Author not found.'}, status=404)

    query_string = request.META.get('QUERY_STRING', '')

    from .selectors.blog_post import BlogPostSelector
    from .dto_serializers import BlogPostDTOSerializer

    selector = BlogPostSelector()
    query = QueryBuilder.from_query_string(query_string).and_filter(f"author/id eq {pk}")
    dtos = selector.get_many(query)

    serializer = BlogPostDTOSerializer(dtos, many=True)
    return Response(serializer.data)
```

### Get Current User

```python
@action(detail=False, methods=['get'])
def me(self, request):
    """
    Get current authenticated user.

    Example: GET /api/users/me/?$select=id,username,email
    """
    query_string = request.META.get('QUERY_STRING', '')

    selector = UserSelector()
    query = QueryBuilder.from_query_string(query_string).and_filter(f"id eq {request.user.pk}")
    dto = selector.get_one(query)

    if dto is None:
        return Response({'detail': 'Not found.'}, status=404)

    serializer = self.get_serializer(dto)
    return Response(serializer.data)
```

---

## Selector Methods Reference

The `ODataSelector` provides these methods that accept `QueryBuilder` and return DTOs directly:

| Method | Returns | Description |
|--------|---------|-------------|
| `get_one(query)` | `DTO \| None` | Single DTO matching the query |
| `get_many(query)` | `List[DTO]` | List of DTOs matching the query |
| `get_by_pk(pk, query?)` | `DTO \| None` | DTO by primary key |
| `count_by(query?)` | `int` | Count of matching records |
| `exists_by(query?)` | `bool` | Whether any records match |

### Examples

```python
from fc_odata.core import QueryBuilder

selector = BlogPostSelector()

# Get one
query = QueryBuilder().and_filter(f"id eq {pk}")
dto = selector.get_one(query)

# Get many with complex query
query = (
    QueryBuilder()
    .filter("status eq 'published'")
    .and_filter("featured eq true")
    .select("id", "title")
    .top(10)
)
dtos = selector.get_many(query)

# Get by primary key
dto = selector.get_by_pk(1)

# Get by primary key with field selection
query = QueryBuilder().select("id", "title", "author").expand("author")
dto = selector.get_by_pk(1, query)

# Count
query = QueryBuilder().filter("status eq 'published'")
count = selector.count_by(query)

# Exists
query = QueryBuilder().filter("slug eq 'my-post'")
exists = selector.exists_by(query)
```

---

## Request Examples

### Basic Requests

```bash
# List all posts
GET /api/blog-posts/

# Get single post
GET /api/blog-posts/1/

# Create post
POST /api/blog-posts/
{
    "title": "New Post",
    "content": "Content...",
    "status": "draft",
    "author": 1
}

# Update post
PUT /api/blog-posts/1/
{
    "title": "Updated Title",
    "content": "Updated content...",
    "status": "published"
}

# Partial update
PATCH /api/blog-posts/1/
{
    "status": "published"
}

# Delete post
DELETE /api/blog-posts/1/
```

### OData Query Requests

```bash
# Select specific fields
GET /api/blog-posts/?$select=id,title,status

# Expand relationships
GET /api/blog-posts/?$expand=author,categories

# Filter by condition
GET /api/blog-posts/?$filter=status eq 'published'

# Multiple filters
GET /api/blog-posts/?$filter=status eq 'published' and featured eq true

# Order by
GET /api/blog-posts/?$orderby=created_at desc

# Pagination
GET /api/blog-posts/?$top=10&$skip=0

# Complex query
GET /api/blog-posts/?$select=id,title,author&$expand=author&$filter=status eq 'published'&$orderby=published_at desc&$top=10
```

### Custom Action Requests

```bash
# Get published posts
GET /api/blog-posts/published/

# Get published posts with OData
GET /api/blog-posts/published/?$select=id,title&$orderby=published_at desc&$top=5

# Get featured posts
GET /api/blog-posts/featured/?$expand=author

# Get posts by author
GET /api/blog-posts/by-author/1/?$select=id,title,status

# Publish a post
POST /api/blog-posts/1/publish/

# Get post stats
GET /api/blog-posts/1/stats/

# Get author's posts
GET /api/authors/1/posts/?$filter=status eq 'published'

# Get posts in category
GET /api/categories/1/posts/?$select=id,title&$orderby=created_at desc

# Get current user
GET /api/users/me/?$select=id,username,email

# Get active users
GET /api/users/active/?$select=id,username
```

---

## Response Examples

### List Response (with $select)

**Request:**
```bash
GET /api/blog-posts/?$select=id,title,status
```

**Response:**
```json
[
    {
        "id": 1,
        "title": "First Post",
        "status": "published"
    },
    {
        "id": 2,
        "title": "Second Post",
        "status": "draft"
    }
]
```

### Single Object Response (with $expand)

**Request:**
```bash
GET /api/blog-posts/1/?$expand=author
```

**Response:**
```json
{
    "id": 1,
    "title": "First Post",
    "slug": "first-post",
    "content": "Post content...",
    "status": "published",
    "featured": true,
    "view_count": 100,
    "created_at": "2024-01-15T10:30:00Z",
    "author": {
        "id": 1,
        "name": "John Doe",
        "email": "john@example.com",
        "bio": "Author bio..."
    }
}
```

### Response with Nested Collections

**Request:**
```bash
GET /api/blog-posts/1/?$expand=categories
```

**Response:**
```json
{
    "id": 1,
    "title": "First Post",
    "content": "Post content...",
    "status": "published",
    "categories": [
        {
            "id": 1,
            "name": "Technology",
            "description": "Tech posts"
        },
        {
            "id": 2,
            "name": "Django",
            "description": "Django framework"
        }
    ]
}
```

### User Response (Password Excluded)

**Request:**
```bash
GET /api/users/1/?$select=id,username,email
```

**Response:**
```json
{
    "id": 1,
    "username": "john",
    "email": "john@example.com"
}
```

---

## Best Practices

### 1. Always Use QueryBuilder

```python
# Good - use QueryBuilder
query = QueryBuilder.from_query_string(query_string).and_filter(f"id eq {pk}")
dto = selector.get_one(query)

# Bad - exposing queryset
queryset = selector.query(query_string)
instance = queryset.filter(pk=pk).first()
```

### 2. Use Selector Methods That Return DTOs

```python
# Good - get DTOs directly
dtos = selector.get_many(query)
dto = selector.get_one(query)
dto = selector.get_by_pk(pk)

# Bad - manual conversion
queryset = selector.query(query_string)
dtos = selector.to_dtos(list(queryset), ...)
```

### 3. Build Filters with OData Syntax

```python
# Good - OData filter syntax
query = QueryBuilder().filter("status eq 'published'").and_filter("featured eq true")

# Bad - mixing Django and OData
queryset = BlogPost.objects.filter(status='published')
```

### 4. Handle Not Found Gracefully

```python
# Good - check for None
dto = selector.get_one(query)
if dto is None:
    return Response({'detail': 'Not found.'}, status=404)

# Also good - use exists_by first
if not selector.exists_by(query):
    return Response({'detail': 'Not found.'}, status=404)
```

### 5. Use get_by_pk for Simple Lookups

```python
# Good - simple and clear
dto = selector.get_by_pk(pk)

# Also good - with field selection
query = QueryBuilder().select("id", "title").expand("author")
dto = selector.get_by_pk(pk, query)
```

---

## Summary

You now have:
- QueryBuilder for fluent query construction
- Selector methods that return DTOs directly (no queryset exposure)
- Complete ViewSet examples (read-only, CRUD, custom actions)
- OData query support in all endpoints
- Automatic password exclusion
- Nested DTO handling
- Production-ready patterns following hexagonal architecture

Use `example/blog/viewsets.py` as your reference implementation!
