# Core Concepts

## The Selector Pattern

FC Selector implements the **Selector** (or **Query**) pattern from Domain-Driven Design (DDD).

### What is a Selector?

A Selector is a specialized component for **read-only data retrieval**. Unlike a Repository that handles both reads and writes, a Selector focuses exclusively on queries.

```
┌─────────────────────────────────────────────────────────┐
│                    Your Application                      │
├─────────────────────────────────────────────────────────┤
│  Use Cases / Services                                    │
│     │                                                    │
│     ├── Write Operations ──► Repository ──► Database    │
│     │                                                    │
│     └── Read Operations ───► Selector ───► Database     │
│                                   │                      │
│                                   ▼                      │
│                                 DTOs                     │
└─────────────────────────────────────────────────────────┘
```

### Why Separate Reads from Writes?

1. **Different optimization strategies** - Reads can use denormalized views, caching, or different databases
2. **Simpler code** - No write logic in selectors, no read logic in repositories
3. **CQRS-ready** - Natural fit for Command Query Responsibility Segregation
4. **Safer** - Read-only by design, no accidental mutations

## OData as Query Language

Instead of creating a method for every possible query:

```python
# Traditional approach - explosion of methods
class PostRepository:
    def get_all(self): ...
    def get_by_id(self, id): ...
    def get_published(self): ...
    def get_by_author(self, author_id): ...
    def get_published_by_author(self, author_id): ...
    def get_featured(self): ...
    def get_featured_published(self): ...
    def get_by_category(self, category_id): ...
    # ... endless variations
```

FC Selector uses **OData** as a standardized query language:

```python
# FC Selector approach - one flexible method
selector = BlogPostSelector()

# All these queries use the same method
selector.get_many(ODataQueryBuilder().filter("status eq 'published'"))
selector.get_many(ODataQueryBuilder().filter("author/id eq 5"))
selector.get_many(ODataQueryBuilder().filter("status eq 'published' and author/id eq 5"))
selector.get_many(ODataQueryBuilder().filter("featured eq true"))
selector.get_many(ODataQueryBuilder().filter("categories/any(c: c/id eq 3)"))
```

### What is OData?

OData (Open Data Protocol) is a standard for building RESTful APIs. FC Selector uses its query syntax:

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `$filter` | Filter results | `status eq 'published'` |
| `$select` | Choose fields | `id,title,author` |
| `$expand` | Include relations | `author,categories` |
| `$orderby` | Sort results | `created_at desc` |
| `$top` | Limit results | `10` |
| `$skip` | Skip results (pagination) | `20` |
| `$count` | Include total count | `true` |

## DTOs (Data Transfer Objects)

Selectors return **DTOs**, not Django models.

### Why DTOs?

```python
# Problem with returning models
def get_posts():
    return BlogPost.objects.filter(status='published')
    # Returns QuerySet - can access ANY field
    # Can trigger lazy loading (N+1)
    # Couples consumers to Django ORM

# Solution with DTOs
def get_posts():
    return selector.get_many(
        ODataQueryBuilder()
        .filter("status eq 'published'")
        .select("id", "title")
    )
    # Returns List[BlogPostDTO]
    # Only requested fields are populated
    # No lazy loading possible
    # Decoupled from ORM
```

### The UNSET Sentinel

DTOs use a special `UNSET` value for fields that weren't selected:

```python
@dataclass
class BlogPostDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET
    content: str = UNSET  # Large field

# Query with $select=id,title
dto = selector.get_one(
    ODataQueryBuilder()
    .filter("id eq 1")
    .select("id", "title")
)

dto.id      # 1
dto.title   # "My Post"
dto.content # UNSET (not fetched from database)
```

This enables:

- **Efficient queries** - Only fetch what you need
- **Clear contracts** - Know exactly what data is available
- **Serialization control** - UNSET fields are omitted from JSON

## Architecture

FC Selector has three layers:

```
┌─────────────────────────────────────────────────────────┐
│  DRF Layer (Optional)                                    │
│  ViewSets, Serializers, Mixins                          │
│  - ODataSelectorViewSetMixin                            │
│  - ODataDTOSerializer                                   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  Django Layer                                            │
│  - ODataSelector (main class)                           │
│  - Query optimization (select_related, prefetch_related)│
│  - AST to Django Q transformation                       │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  Core Layer (Framework-agnostic)                         │
│  - ODataQueryBuilder                                    │
│  - OData parsers ($filter, $select, $expand, etc.)      │
│  - BaseODataDTO                                         │
│  - AST nodes                                            │
└─────────────────────────────────────────────────────────┘
```

### Core Layer

Framework-agnostic code that could work with any ORM:

- `ODataQueryBuilder` - Fluent API for building queries
- Parsers - Convert OData strings to AST
- `BaseODataDTO` - Base class for DTOs

### Django Layer

Django-specific implementation:

- `ODataSelector` - Main selector class
- Query optimization
- AST to Django Q objects transformation

### DRF Layer

Django REST Framework integration:

- `ODataSelectorViewSetMixin` - ViewSet mixin
- `ODataDTOSerializer` - Serializer for DTOs

## Usage Patterns

### Pattern 1: From Services/Use Cases

```python
class PublishPostUseCase:
    def __init__(self):
        self.selector = BlogPostSelector()
        self.repository = BlogPostRepository()

    def execute(self, post_id: int) -> BlogPostDTO:
        # Read with selector
        post = self.selector.get_by_pk(post_id)
        if not post:
            raise NotFound()

        # Write with repository
        self.repository.update(post_id, status='published')

        # Return updated data
        return self.selector.get_by_pk(post_id)
```

### Pattern 2: From ViewSets

```python
class BlogPostViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    selector_class = BlogPostSelector
    serializer_class = BlogPostDTOSerializer

    @action(detail=False)
    def featured(self, request):
        query = ODataQueryBuilder(request.META['QUERY_STRING'])
        query.and_filter("featured eq true")
        dtos = self.selector_class().get_many(query)
        return Response(self.get_serializer(dtos, many=True).data)
```

### Pattern 3: Direct Query String

```python
# Useful for internal APIs or testing
dtos = selector.query_as_dtos(
    "$filter=status eq 'published'&$select=id,title&$top=10"
)
```
