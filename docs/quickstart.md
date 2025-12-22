# Quick Start

Get FC Selector running in 5 minutes.

## 1. Define Your Models

```python
# models.py
from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[('draft', 'Draft'), ('published', 'Published')]
    )
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
```

## 2. Generate Selectors & DTOs

Run the management command to auto-generate selectors and DTOs:

```bash
python manage.py generate_odata_selector myapp.BlogPost --single --force
```

This creates `myapp/selectors/blog_post.py` with:

```python
from dataclasses import dataclass
from fc_selector.core.dtos import BaseODataDTO, UNSET
from fc_selector.django.selector import ODataSelector

@dataclass
class AuthorDTO(BaseODataDTO):
    id: int = UNSET
    name: str = UNSET
    email: str = UNSET

@dataclass
class BlogPostDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET
    content: str = UNSET
    status: str = UNSET
    created_at: str = UNSET
    author: AuthorDTO = UNSET

class BlogPostSelector(ODataSelector):
    class Meta:
        model = BlogPost
        dto_class = BlogPostDTO
        expandable_fields = {
            'author': AuthorDTO,
        }
```

## 3. Use the Selector

### From a Service or Use Case

```python
from fc_selector.core import ODataQueryBuilder
from myapp.selectors.blog_post import BlogPostSelector

def get_published_posts(limit: int = 10):
    selector = BlogPostSelector()
    return selector.get_many(
        ODataQueryBuilder()
        .filter("status eq 'published'")
        .orderby("created_at desc")
        .top(limit)
    )

def get_post_by_id(post_id: int):
    selector = BlogPostSelector()
    return selector.get_by_pk(
        post_id,
        ODataQueryBuilder().expand("author")
    )
```

### From a ViewSet

```python
# viewsets.py
from rest_framework import viewsets
from rest_framework.response import Response
from fc_selector.core import ODataQueryBuilder
from fc_selector.django.drf.viewsets import ODataSelectorViewSetMixin
from fc_selector.django.drf.serializers import ODataDTOSerializer

from .selectors.blog_post import BlogPostSelector, BlogPostDTO

class BlogPostDTOSerializer(ODataDTOSerializer):
    class Meta:
        dto_class = BlogPostDTO

class BlogPostViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    serializer_class = BlogPostDTOSerializer
    selector_class = BlogPostSelector

    # list() and retrieve() are provided by the mixin
    # They automatically support OData query parameters
```

```python
# urls.py
from rest_framework.routers import DefaultRouter
from .viewsets import BlogPostViewSet

router = DefaultRouter()
router.register('posts', BlogPostViewSet, basename='posts')

urlpatterns = router.urls
```

## 4. Query Your API

```bash
# Get all posts
curl "http://localhost:8000/api/posts/"

# Select specific fields
curl "http://localhost:8000/api/posts/?$select=id,title,status"

# Filter by status
curl "http://localhost:8000/api/posts/?$filter=status eq 'published'"

# Expand author relation
curl "http://localhost:8000/api/posts/?$expand=author"

# Combined query
curl "http://localhost:8000/api/posts/?$filter=status eq 'published'&$select=id,title&$expand=author&$orderby=created_at desc&$top=5"
```

## Next Steps

- [Core Concepts](concepts.md) - Understand the Selector pattern and architecture
- [Selectors Guide](selectors.md) - Learn all selector methods
- [Query Builder](query-builder.md) - Master the ODataQueryBuilder
- [OData Syntax](odata-syntax.md) - Full OData query reference
