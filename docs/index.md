# FC Selector

**DDD Selector/Query pattern for Django with OData query language support.**

[:material-github: GitHub](https://github.com/alexandre-fundcraft/fc-selector){ .md-button }

FC Selector implements the **Selector pattern**, a recognized pattern in the Django community (see [HackSoft Django Styleguide](https://github.com/HackSoftware/Django-Styleguide), [ai-django-core](https://ai-django-core.readthedocs.io/en/latest/features/selectors.html)) that provides a clean, read-only interface for querying data. It uses **OData v4** as a dynamic, standardized query language.

## What is this?

Think of it as a **dynamic read-only repository** that:

- Uses **OData syntax** or a **type-safe fluent API** for flexible queries
- Returns **DTOs** (Data Transfer Objects), not Django models
- Works from **services**, **use cases**, or **ViewSets**
- Never exposes the ORM layer

## Two Ways to Query

### String API (OData)

```python
selector = BlogPostSelector()
posts = selector.get_many(
    QueryBuilder()
    .filter("status eq 'published'")
    .select("id", "title")
    .expand("author")
    .orderby("created_at desc")
    .top(10)
)
```

### Fluent API (Type-Safe)

```python
from fc_selector.core.filters import Field, Expand, OrderBy

selector = BlogPostSelector()
posts = selector.get_many(
    QueryBuilder()
    .where(
        Field("status").eq("published") &
        Field("rating").gt(4.0)
    )
    .select("id", "title", "rating")
    .expand(
        Expand("author").select("id", "name"),
        Expand("comments")
            .filter(Field("approved").eq(True))
            .top(5)
    )
    .orderby(OrderBy("rating").desc())
    .top(10)
)
```

Both APIs can be mixed and produce the same `QueryIntent` internally.

## Key Concepts

### Selector Pattern (DDD)

The Selector pattern separates **read operations** from write operations. Unlike repositories that handle both, selectors focus exclusively on queries, making them:

- **Simpler** - No write logic to maintain
- **Optimizable** - Can use different data sources for reads
- **Safer** - Read-only by design

### DTOs Instead of Models

Selectors return DTOs, not Django models. This:

- **Decouples** your domain from the ORM
- **Controls** exactly what data is exposed
- **Prevents** accidental lazy loading (N+1 queries)

## Features

- **Full OData v4 support**: `$filter`, `$select`, `$expand`, `$orderby`, `$top`, `$skip`, `$count`
- **Type-safe fluent API**: `Field("status").eq("published")`, `Expand("author").select("name")`, `OrderBy("created_at").desc()`
- **Hybrid values mode**: 2-5x faster queries using `.values()` with `$expand` support for forward relations
- **Automatic query optimization**: `select_related()`, `prefetch_related()`, `.only()` applied from query intent
- **Type-safe DTOs** with dataclasses and `UNSET` sentinel
- **Auto-generated selectors & DTOs** from Django models via management command
- **Field aliases** for API-friendly names
- **Field restrictions** with filterable/sortable positive and negative lists
- **DRF integration** with ViewSet mixins, serializers, and OpenAPI/Swagger parameters
- **Security**: field validation, private field blocking, query length limits

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

# Type-safe alternative
posts = selector.get_many(
    QueryBuilder()
    .where(Field("rating").gt(4.0) & Field("status").eq("published"))
    .select("id", "title", "rating")
    .orderby(OrderBy("rating").desc())
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
- [Query Builder](query-builder.md) - String API and fluent API reference
- [Hybrid Values Mode](HYBRID_VALUES_EXPAND.md) - Performance optimization
