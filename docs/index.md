# FC Selector

**DDD Selector/Query pattern for Django with OData query language support.**

FC Selector implements the **Selector pattern**, a recognized pattern in the Django community (see [HackSoft Django Styleguide](https://github.com/HackSoftware/Django-Styleguide), [ai-django-core](https://ai-django-core.readthedocs.io/en/latest/features/selectors.html)) that provides a clean, read-only interface for querying data. It uses **OData v4** as a dynamic, standardized query language.

## What is this?

Think of it as a **dynamic read-only repository** that:

- Uses **OData syntax** for flexible, expressive queries
- Returns **DTOs** (Data Transfer Objects), not Django models
- Works from **services**, **use cases**, or **ViewSets**
- Never exposes the ORM layer

```python
from fc_selector.django.selector import ODataSelector, QueryBuilder

# From a service or use case
selector = BlogPostSelector()
posts = selector.get_many(
    QueryBuilder()
    .filter("status eq 'published'")
    .select("id", "title", "author")
    .expand("author")
    .orderby("created_at desc")
    .top(10)
)
```

## Key Concepts

### Selector Pattern (DDD)

The Selector pattern separates **read operations** from write operations. Unlike repositories that handle both, selectors focus exclusively on queries, making them:

- **Simpler** - No write logic to maintain
- **Optimizable** - Can use different data sources for reads
- **Safer** - Read-only by design

### OData as Query Language

Instead of creating methods for every query variation (`get_published_posts()`, `get_posts_by_author()`, etc.), OData provides a standardized syntax:

```
$filter=status eq 'published' and author/id eq 5
$select=id,title,excerpt
$expand=author,categories
$orderby=created_at desc
$top=10
```

### DTOs Instead of Models

Selectors return DTOs, not Django models. This:

- **Decouples** your domain from the ORM
- **Controls** exactly what data is exposed
- **Prevents** accidental lazy loading (N+1 queries)

## Three Ways to Use FC Selector

### 1. From Services / Use Cases

```python
class GetPublishedPostsUseCase:
    def execute(self, author_id: int = None) -> List[BlogPostDTO]:
        selector = BlogPostSelector()
        query = QueryBuilder().filter("status eq 'published'")

        if author_id:
            query.and_filter(f"author/id eq {author_id}")

        return selector.get_many(query)
```

### 2. From ViewSets (REST API)

```python
class BlogPostViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    selector_class = BlogPostSelector
    serializer_class = BlogPostDTOSerializer

    # Automatic OData support via mixin
    # GET /api/posts/?$filter=status eq 'published'&$select=id,title
```

### 3. Direct Query String

```python
# Pass OData query string directly
selector = BlogPostSelector()
dtos = selector.query_as_dtos("$filter=featured eq true&$top=5")
```

## Features

- **Auto-generated Selectors & DTOs** from Django models
- **Full OData v4 support**: $filter, $select, $expand, $orderby, $top, $skip, $count
- **Query optimization**: Automatic `select_related()`, `prefetch_related()`, and `.only()`
- **Type-safe DTOs** with dataclasses
- **Field aliases** for API-friendly names
- **DRF integration** with ViewSet mixins and serializers

## Quick Example

```python
# 1. Define your selector (or auto-generate it)
class BlogPostSelector(ODataSelector):
    class Meta:
        model = BlogPost
        dto_class = BlogPostDTO
        expandable_fields = {
            'author': AuthorDTO,
            'categories': CategoryDTO,
        }

# 2. Use it anywhere
selector = BlogPostSelector()

# Get one
post = selector.get_by_pk(1, QueryBuilder().expand("author"))

# Get many with complex filter
posts = selector.get_many(
    QueryBuilder()
    .filter("rating gt 4.0 and status eq 'published'")
    .select("id", "title", "rating")
    .orderby("rating desc")
    .top(10)
)

# Check existence
exists = selector.exists_by(
    QueryBuilder().filter("slug eq 'my-post'")
)

# Count
count = selector.count_by(
    QueryBuilder().filter("status eq 'draft'")
)
```

## Installation

```bash
pip install fc-selector
```

See [Installation](installation.md) for detailed setup instructions.

## Next Steps

- [Quick Start](quickstart.md) - Get up and running in 5 minutes
- [Core Concepts](concepts.md) - Understand the architecture
- [Selectors Guide](selectors.md) - Deep dive into selectors
