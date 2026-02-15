# FC Selector

**DDD Selector/Query pattern for Django with OData v4 query language support.**

A read-only data access library that implements the Selector pattern with type-safe DTOs, automatic query optimization, and OData v4 as the query protocol. Built on hexagonal architecture principles: protocol-agnostic core, swappable adapters.

## Features

- **OData v4 Query Support**: `$filter`, `$orderby`, `$top`, `$skip`, `$select`, `$expand`, `$count`
- **Selector + DTO Pattern**: Type-safe data access with Data Transfer Objects instead of raw models
- **Automatic Query Optimization**: `.only()`, `select_related()`, `prefetch_related()` applied automatically
- **Hybrid Values Mode**: High-performance execution using `.values()` (2-5x faster) with support for all relation types (Forward FK, Reverse FK, M2M)
- **Fluent Query Builder**: `Field("status").eq("published") & Field("rating").gt(4.0)`

## Performance: Hybrid Values Mode

FC Selector includes a specialized **HybridValuesBuilder** that executes queries using Django's `.values()` method instead of instantiating model objects. This is typically **2-5x faster** for read operations.

It supports `$expand` on **all relation types**:
*   **Forward Relations (FK/OneToOne)**: Fetched in a single query using `select_related` + `__` notation.
*   **Reverse Relations (Reverse FK)**: Fetched using a highly efficient 1+N query strategy (bulk fetch of children).
*   **ManyToMany Relations**: Fetched using a 1+N strategy (through table + child table).

This mode is enabled by default (`values_mode=True`) but can be disabled per selector if you need model methods or `@property` fields.
- **DRF Integration**: `ODataSelectorViewSetMixin` adds OData support to any ViewSet
- **OpenAPI Documentation**: Automatic schema generation via drf-spectacular
- **Security**: Field validation, private field blocking, query length limits, automatic password exclusion
- **Code Generation**: Management commands to generate selectors, DTOs, and serializers from models

## Installation

This package is not published to PyPI. Install directly from the repository:

```bash
git clone https://github.com/alexandre-fundcraft/fc-selector.git
cd fc-selector

# Using uv (recommended)
uv sync --group dev

# Using pip
pip install -e ".[dev]"
```

### Requirements

- **Python** >= 3.11 (tested on 3.11, 3.12, 3.13)
- **Django** >= 4.2
- **djangorestframework** >= 3.12.0
- **drf-spectacular** >= 0.29.0
- **python-dateutil** >= 2.8.2
- **sly** >= 0.5

## Quick Start

### 1. Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'drf_spectacular',
    'fc_selector',
]
```

### 2. Generate Selectors and DTOs from your models

```bash
python manage.py generate_odata_selector blog.BlogPost --single --force
python manage.py generate_odata_selector blog.Author --single --force
```

This creates DTOs, Selectors, and field mappings automatically under `blog/selectors/`.

### 3. Create DTO Serializers

```python
# blog/dto_serializers.py
from fc_selector.django.drf.serializers import ODataDTOSerializer
from .selectors.blog_post import BlogPostDTO

class BlogPostDTOSerializer(ODataDTOSerializer):
    class Meta:
        dto_class = BlogPostDTO
```

### 4. Create ViewSets

```python
# blog/viewsets.py
from rest_framework import viewsets
from fc_selector.django.drf.viewsets import ODataSelectorViewSetMixin
from .selectors.blog_post import BlogPostSelector
from .dto_serializers import BlogPostDTOSerializer

class BlogPostViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    selector_class = BlogPostSelector
    serializer_class = BlogPostDTOSerializer
    odata_entity_set_name = "posts"
```

### 5. Configure URLs

```python
# blog/urls.py
from rest_framework.routers import DefaultRouter
from .viewsets import BlogPostViewSet

router = DefaultRouter()
router.register(r'posts', BlogPostViewSet, basename='blogpost')

urlpatterns = router.urls
```

### 6. Query your API

```bash
# Get published posts, sorted by date, with author info
GET /odata/posts/?$filter=status eq 'published'&$orderby=created_at desc&$top=10&$select=id,title&$expand=author($select=name)
```

## OData Query Reference

### Query Options

| Option | Description | Example |
|--------|-------------|---------|
| `$filter` | Filter results | `$filter=status eq 'published'` |
| `$orderby` | Sort results | `$orderby=created_at desc` |
| `$top` | Limit results | `$top=10` |
| `$skip` | Skip results | `$skip=20` |
| `$select` | Choose fields | `$select=id,title,status` |
| `$expand` | Include relations | `$expand=author($select=name)` |
| `$count` | Include total count | `$count=true` |

### Filter Operators

| Operator | Example |
|----------|---------|
| `eq`, `ne` | `status eq 'published'` |
| `gt`, `ge`, `lt`, `le` | `rating gt 4.0` |
| `and`, `or`, `not` | `status eq 'published' and featured eq true` |
| `contains` | `contains(title,'django')` |
| `startswith`, `endswith` | `startswith(title,'How')` |
| `year`, `month`, `day` | `year(created_at) eq 2024` |

## Fluent Query Builder (Python)

Build queries programmatically with type safety:

```python
from fc_selector.core.query_builder import QueryBuilder
from fc_selector.core.filters import Field, Expand, OrderBy

intent = (
    QueryBuilder()
    .where(
        Field("status").eq("published") &
        Field("rating").gt(4.0)
    )
    .select("id", "title", "rating")
    .expand(
        Expand("author").select("id", "name"),
        Expand("comments").filter(Field("approved").eq(True)).top(5)
    )
    .orderby(OrderBy("created_at").desc())
    .top(10)
    .build()
)

selector = BlogPostSelector()
results = selector.execute(intent)
```

### Initialize from a Query String

`QueryBuilder` accepts a full OData query string, making it easy to forward client requests and add server-side logic:

```python
from fc_selector.core.query_builder import QueryBuilder

# Parse a raw query string
query = QueryBuilder("$filter=status eq 'published'&$select=id,title&$top=10")

# Or directly from a Django request
query = QueryBuilder(request.META.get('QUERY_STRING', ''))

# Then add server-side filters, enforce pagination, etc.
query.and_filter(f"author/id eq {author_id}")
query.top(25)

results = selector.get_many(query)
```

See [Query Builder Documentation](docs/query-builder.md) for the full API reference.

## Example Project

A complete example is available in `example/`:

```bash
make dev-setup      # Install deps + setup example DB
make example-run    # Start server at localhost:8000
```

Available endpoints:

- `http://localhost:8000/odata/posts/` - Blog posts with OData support
- `http://localhost:8000/odata/authors/` - Authors
- `http://localhost:8000/odata/$metadata` - OData service metadata (EDMX)
- `http://localhost:8000/api/docs/` - Swagger UI
- `http://localhost:8000/api/redoc/` - ReDoc
- `http://localhost:8000/admin/` - Django admin

Test credentials: `test@test.com` / `test`

## Development

```bash
make sync             # Sync dependencies with uv
make test             # Run all tests (unit + integration + e2e)
make test-unit        # Run unit tests only
make test-coverage    # Run tests with coverage report
make lint             # Run ruff + mypy
make format           # Auto-format code
make docs-serve       # Serve MkDocs documentation locally
```

Run `make help` for all available commands.

## Architecture

```
Protocol Layer (OData)          Core Layer                    Django Layer
+-----------------+     +--------------------+     +---------------------+
| OData Parsers   |---->| QueryIntent (AST)  |---->| DjangoExecutor      |
| (SLY grammar)   |     | QueryBuilder       |     | ODataSelector       |
| $filter, $select|     | Field, Expand,     |     | select_related()    |
| $expand, ...    |     | OrderBy filters    |     | prefetch_related()  |
+-----------------+     +--------------------+     +---------------------+
                              DTOs                      Django ORM
```

The core layer is protocol-agnostic. OData is one adapter; the `QueryIntent` model can be built from any source (fluent API, custom parsers, etc.).

## Documentation

Full documentation: **https://alexandre-fundcraft.github.io/fc-selector/**

To serve locally:

```bash
make docs-serve  # http://localhost:9999
```

## License

**AGPL-3.0-or-later** - See [LICENSE](LICENSE) for the full text.

You can use, modify, and distribute this software freely. If you deploy it (including as a web service), you must make your source code available under AGPL-3.0.