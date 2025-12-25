# Core Concepts

## The Selector Pattern

FC Selector implements the **Selector** (or **Query**) pattern from Domain-Driven Design (DDD), following the principles of **Hexagonal Architecture**.

### What is a Selector?

A Selector is a specialized component for **read-only data retrieval**. Unlike a Repository that handles both reads and writes, a Selector focuses exclusively on queries and returns Data Transfer Objects (DTOs) instead of database models.

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

## Protocol-Agnostic Queries

A key feature of FC Selector is the separation between **how you ask** (Protocol) and **what you want** (Intent).

### QueryIntent: The Canonical Representation

Internally, every query is converted into a `QueryIntent`. This is a framework-agnostic structure that describes:
- **Filter**: What conditions must be met (represented as an AST).
- **Select**: Which fields to retrieve.
- **Expand**: Which relations to eager load.
- **Order**: How to sort the results.
- **Pagination**: Limits and offsets.

Because the system works with `QueryIntent`, you can trigger the same query logic via OData, GraphQL, or direct Python calls using the `QueryBuilder`.

## OData as the Default Protocol

While the core is agnostic, FC Selector provides first-class support for **OData v4** as an interface language. Instead of creating a method for every possible query variation, you expose a flexible OData-powered endpoint.

```python
# FC Selector approach - one flexible method, many possibilities
selector = BlogPostSelector()

# These all generate different QueryIntents but use the same Selector logic
selector.get_many(QueryBuilder().filter("status eq 'published'"))
selector.get_many(QueryBuilder().filter("author/id eq 5"))
selector.get_many(QueryBuilder().top(10).orderby("created_at desc"))
```

## DTOs (Data Transfer Objects)

Selectors return **DTOs**, not Django models. This provides:
- **Decoupling**: The API consumer doesn't know about the underlying database structure.
- **Performance**: Prevents N+1 queries by disabling lazy loading.
- **Contract Safety**: Only specified fields are available.

### The UNSET Sentinel
DTOs use a special `UNSET` value for fields that weren't selected in the query, allowing for efficient partial updates and bandwidth optimization.

## Layered Architecture

FC Selector is organized into three decoupled layers:

### 1. Protocol Layer (`fc_selector/protocols`)
Responsible for translating external requests into the internal language.
- **OData Parser**: Converts OData strings to AST/QueryIntent.
- **Converters**: Bidirectional mapping between protocols.

### 2. Core Layer (`fc_selector/core`)
The "Domain" of the library. No dependencies on Django or DRF.
- **QueryIntent**: The central query model.
- **AST Nodes**: Abstract representation of logic.
- **QueryBuilder**: Fluent API for constructing queries. Supports dependency injection of custom filter parsers.
- **Exceptions**: Domain-level errors like `InvalidFieldError` for security validation.

### 3. Infrastructure Layer (`fc_selector/django`)
The implementation of the query logic for specific backends.
- **DjangoExecutor**: Recursively applies a `QueryIntent` to a Django QuerySet.
- **AstToDjangoQVisitor**: Translates the neutral AST into Django `Q()` objects.
- **ODataSelector**: The public interface combining all layers.

---

## Usage Patterns

### From Services/Use Cases (Direct Intent)
```python
from fc_selector.django.selector import ODataSelector, QueryBuilder
from fc_selector.core.filters import Field

intent = (
    QueryBuilder()
    .where(Field("status").eq("published"))
    .select("id", "title")
    .build()
)
dtos = selector.execute(intent)
```

### From ViewSets (OData Adapter)
```python
from rest_framework import viewsets
from fc_selector.django.drf.viewsets import ODataSelectorViewSetMixin

class BlogPostViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    # Automatically handles OData query params from the request
    selector_class = BlogPostSelector
    serializer_class = BlogPostDTOSerializer
```

---

## Security Features

FC Selector includes built-in security measures:

### Field Validation
The `AstToDjangoQVisitor` validates all field names:
- **Private fields blocked**: Fields starting with `_` cannot be accessed.
- **Field existence check**: Non-existent fields raise `InvalidFieldError`.
- **Allowed fields whitelist**: Optional restriction to specific fields.

```python
# These will raise InvalidFieldError
"$filter=_password eq 'secret'"  # Private field
"$filter=nonexistent eq 'value'"  # Invalid field
```

### Input Length Limits
The parser enforces `MAX_FILTER_LENGTH=4000` to prevent DoS attacks via overly complex queries.

---

## Performance Optimizations

### Parser Caching
Lexer and parser instances are cached in thread-local storage, avoiding repeated instantiation overhead.

### Automatic Query Optimization
The `DjangoExecutor` automatically:
- Uses `select_related()` for forward FK/OneToOne relations
- Uses `prefetch_related()` for reverse/ManyToMany relations
- Uses `only()` to limit fetched fields based on `$select`