<!-- markdownlint-disable MD024 -->
# API Reference

## ODataSelector

Main class for querying data.

```python
from fc_selector.django.selector import ODataSelector
```

### Configuration

```python
class MySelector(ODataSelector):
    class Meta:
        model = MyModel                    # Required: Django model
        dto_class = MyDTO                  # Required: DTO class
        expandable_fields = {              # Optional: expandable relations
            'relation': RelationDTO,
        }
        field_aliases = {                  # Optional: field name aliases
            'apiName': 'internal__name',
        }

        # Field restrictions (hybrid approach)
        filterable_fields = ['status', 'created_at']  # Positive list (takes priority)
        non_filterable_fields = ['password']          # Negative list (if no positive list)
        sortable_fields = ['title', 'created_at']     # Positive list (takes priority)
        non_sortable_fields = ['content']             # Negative list (if no positive list)

        # Pagination defaults
        default_ordering = ['-created_at']  # Default sort order
        default_limit = 100                 # Default page size
        max_limit = 500                     # Maximum page size
```

### Meta Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `model` | Model | Yes | Django model class |
| `dto_class` | class | Yes | DTO class for serialization |
| `expandable_fields` | dict | No | Map relation name → DTO class |
| `field_aliases` | dict | No | Map API name → internal field path |
| `allowed_fields` | list | No | Fields available for $select |
| `filterable_fields` | list | No | Fields available for $filter (positive) |
| `non_filterable_fields` | list | No | Fields NOT available for $filter (negative) |
| `sortable_fields` | list | No | Fields available for $orderby (positive) |
| `non_sortable_fields` | list | No | Fields NOT available for $orderby (negative) |
| `default_ordering` | list | No | Default sort fields (e.g., `['-created_at']`) |
| `default_limit` | int | No | Default $top value (default: 100) |
| `max_limit` | int | No | Maximum $top value (default: 500) |
| `values_mode` | bool | No | Use `.values()` + hybrid mode (default: `True`). Set `False` for DTOs with `@property` fields. |

### Methods

#### get_many(query_builder=None) -> List[DTO]

Get multiple DTOs.

```python
posts = selector.get_many()
posts = selector.get_many(QueryBuilder().filter("status eq 'published'"))
```

#### get_one(query_builder) -> Optional[DTO]

Get a single DTO. Returns `None` if not found.

```python
post = selector.get_one(QueryBuilder().filter("slug eq 'my-post'"))
```

#### get_by_pk(pk, query_builder=None) -> Optional[DTO]

Get by primary key.

```python
post = selector.get_by_pk(1)
post = selector.get_by_pk(1, QueryBuilder().expand("author"))
```

#### count_by(query_builder=None) -> int

Count matching records.

```python
count = selector.count_by(QueryBuilder().filter("status eq 'draft'"))
```

#### exists_by(query_builder=None) -> bool

Check if any records match.

```python
exists = selector.exists_by(QueryBuilder().filter("slug eq 'my-post'"))
```

#### query(query_string, model_class=None, base_queryset=None) -> QuerySet

Execute raw query string, return QuerySet.

```python
queryset = selector.query("$filter=status eq 'published'")
```

#### query_as_dtos(query_string, model_class=None, base_queryset=None) -> List[DTO]

Execute raw query string, return DTOs. Uses hybrid values mode when available (faster).

```python
dtos = selector.query_as_dtos("$filter=status eq 'published'&$select=id,title")
```

#### query_as_dicts(query_string, model_class=None, base_queryset=None) -> list

Execute raw query string using `.values()`. Returns raw dicts (no expand) or DTOs (hybrid expand for any relation).

```python
dicts = selector.query_as_dicts("$filter=status eq 'published'&$select=id,title")
```

#### get_many_dicts(query_builder=None) -> list

Get results using `.values()`. Returns raw dicts (no expand) or DTOs (hybrid expand).

```python
results = selector.get_many_dicts(QueryBuilder().filter("status eq 'published'"))
```

#### get_queryset() -> QuerySet

Override to customize base QuerySet.

```python
def get_queryset(self):
    return MyModel.objects.filter(deleted_at__isnull=True)
```

---

## QueryBuilder

Fluent API for building OData queries.

```python
from fc_selector.django.selector import QueryBuilder
```

### Constructor

```python
# Empty
query = QueryBuilder()

# From existing query string
query = QueryBuilder("$filter=status eq 'published'")

# With custom filter parser (dependency injection)
def my_parser(expression: str) -> Node:
    # Custom parsing logic
    ...
query = QueryBuilder(filter_parser=my_parser)
```

### String API Methods

#### filter(expression) -> self

Set/replace $filter.

```python
query.filter("status eq 'published'")
```

#### and_filter(expression) -> self

Add AND condition.

```python
query.and_filter("featured eq true")
```

#### or_filter(expression) -> self

Add OR condition.

```python
query.or_filter("status eq 'featured'")
```

#### select(*fields) -> self

Set $select.

```python
query.select("id", "title", "status")
query.select("id,title,status")
```

#### expand(*relations) -> self

Set $expand.

```python
query.expand("author", "categories")
query.expand("author,categories")
```

#### orderby(*fields) -> self

Set $orderby.

```python
query.orderby("created_at desc")
query.orderby("featured desc", "created_at desc")
```

#### top(count) -> self

Set $top (limit).

```python
query.top(10)
```

#### skip(count) -> self

Set $skip (offset).

```python
query.skip(20)
```

#### count(include=True) -> self

Set $count.

```python
query.count(True)
```

### Fluent API Methods

#### where(expression) -> self

Set filter using type-safe `Field` expressions.

```python
query.where(Field("status").eq("published") & Field("rating").gt(4.0))
```

#### and_where(expression) -> self

Add AND condition with type-safe expression.

```python
query.and_where(Field("featured").eq(True))
```

#### or_where(expression) -> self

Add OR condition with type-safe expression.

```python
query.or_where(Field("vip").eq(True))
```

#### expand(*expands) -> self

Set $expand using type-safe `Expand` objects.

```python
query.expand(
    Expand("author").select("id", "name"),
    Expand("comments").filter(Field("approved").eq(True)).top(5)
)
```

#### orderby(*fields) -> self

Set $orderby using type-safe `OrderBy` objects.

```python
query.orderby(OrderBy("rating").desc(), OrderBy("created_at").desc())
```

### Output Methods

#### build() -> QueryIntent

Build and return a `QueryIntent` object (protocol-agnostic).

```python
intent = query.build()
results = selector.execute(intent)
```

#### build_query_string() -> str

Build the OData query string.

```python
query_string = query.build_query_string()
```

#### to_dict() -> dict

Convert to dictionary.

```python
params = query.to_dict()
```

---

## Field

Type-safe filter expression builder.

```python
from fc_selector.core.filters import Field
```

### Comparison Methods

| Method | OData | Example |
|--------|-------|---------|
| `eq(value)` | `eq` | `Field("status").eq("published")` |
| `ne(value)` | `ne` | `Field("status").ne("deleted")` |
| `gt(value)` | `gt` | `Field("age").gt(18)` |
| `ge(value)` | `ge` | `Field("price").ge(100)` |
| `lt(value)` | `lt` | `Field("count").lt(10)` |
| `le(value)` | `le` | `Field("rating").le(5)` |

### String Methods

| Method | OData | Example |
|--------|-------|---------|
| `contains(value)` | `contains()` | `Field("name").contains("john")` |
| `startswith(value)` | `startswith()` | `Field("email").startswith("admin")` |
| `endswith(value)` | `endswith()` | `Field("email").endswith("@x.com")` |

### Null / Collection Methods

| Method | OData | Example |
|--------|-------|---------|
| `is_null()` | `eq null` | `Field("deleted_at").is_null()` |
| `is_not_null()` | `ne null` | `Field("email").is_not_null()` |
| `is_in(values)` | `in ()` | `Field("status").is_in(["active", "pending"])` |
| `not_in(values)` | `not (in ())` | `Field("role").not_in(["guest"])` |
| `between(low, high)` | `ge and le` | `Field("price").between(10, 100)` |

### Logical Operators

```python
# AND
Field("status").eq("active") & Field("age").gt(18)

# OR
Field("role").eq("admin") | Field("role").eq("superuser")

# NOT
~Field("deleted").eq(True)
```

### Nested Fields

```python
Field("author/name").eq("John")
```

---

## Expand

Type-safe relation expansion builder.

```python
from fc_selector.core.filters import Expand
```

### Methods

| Method | Description | Example |
|--------|-------------|---------|
| `select(*fields)` | Nested $select | `Expand("author").select("id", "name")` |
| `filter(expr)` | Nested $filter | `Expand("comments").filter(Field("approved").eq(True))` |
| `orderby(*fields)` | Nested $orderby | `Expand("comments").orderby(OrderBy("created_at").desc())` |
| `top(n)` | Nested $top | `Expand("comments").top(5)` |
| `skip(n)` | Nested $skip | `Expand("comments").skip(10)` |
| `expand(*expands)` | Deep nesting | `Expand("author").expand(Expand("profile"))` |

---

## OrderBy

Type-safe ordering builder.

```python
from fc_selector.core.filters import OrderBy
```

### Methods

```python
OrderBy("name")             # ascending (default)
OrderBy("name").asc()       # explicit ascending
OrderBy("created_at").desc() # descending
```

### Usage in QueryBuilder

```python
query.orderby(
    OrderBy("featured").desc(),
    OrderBy("created_at").desc(),
    OrderBy("title").asc()
)
```

---

## BaseODataDTO

Base class for DTOs.

```python
from fc_selector.core.dtos import BaseODataDTO, UNSET
```

### Definition

```python
from dataclasses import dataclass

@dataclass
class MyDTO(BaseODataDTO):
    id: int = UNSET
    name: str = UNSET
    relation: Optional[RelationDTO] = UNSET
```

### Class Methods

#### from_model(instance, selected_fields=None, expanded_fields=None, expand_options=None) -> DTO

Convert model instance to DTO.

```python
dto = MyDTO.from_model(instance, selected_fields={'id', 'name'})
```

---

## UNSET

Sentinel value for unselected fields.

```python
from fc_selector.core.dtos import UNSET

# Check if field was selected
if dto.content is not UNSET:
    print(dto.content)
```

---

## ODataSelectorViewSetMixin

ViewSet mixin for DRF integration.

```python
from fc_selector.django.drf.viewsets import ODataSelectorViewSetMixin
```

### Configuration

```python
class MyViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    serializer_class = MyDTOSerializer
    selector_class = MySelector
```

### Provided Actions

- `list(request)` - GET /resource/
- `retrieve(request, pk)` - GET /resource/{pk}/

---

## ODataDTOSerializer

Serializer for DTOs.

```python
from fc_selector.django.drf.serializers import ODataDTOSerializer
```

### Configuration

```python
class MyDTOSerializer(ODataDTOSerializer):
    class Meta:
        dto_class = MyDTO
        exclude = ['password']        # Optional: fields to exclude
        read_only_fields = ['id']     # Optional: read-only fields
```

---

## OpenAPI / Swagger Parameters

Pre-defined OData parameters for `drf-spectacular`.

```python
from fc_selector.django.drf import ODATA_PARAMETERS, ODATA_RETRIEVE_PARAMETERS
```

### ODATA_PARAMETERS

List of all 7 OData `OpenApiParameter` objects for list endpoints:

| Parameter | Type | Description |
|-----------|------|-------------|
| `$filter` | string | OData filter expression |
| `$select` | string | Comma-separated fields |
| `$expand` | string | Relations to expand |
| `$orderby` | string | Sort fields |
| `$top` | integer | Limit results |
| `$skip` | integer | Offset |
| `$count` | boolean | Include total count |

### ODATA_RETRIEVE_PARAMETERS

Subset for retrieve endpoints (only `$select` and `$expand`).

### Usage

```python
from drf_spectacular.utils import extend_schema, extend_schema_view
from fc_selector.django.drf import ODATA_PARAMETERS, ODATA_RETRIEVE_PARAMETERS

@extend_schema_view(
    list=extend_schema(parameters=ODATA_PARAMETERS),
    retrieve=extend_schema(parameters=ODATA_RETRIEVE_PARAMETERS),
)
class MyViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
    ...
```

---

## Management Commands

### generate_odata_selector

Generate selectors and DTOs from Django models.

```bash
python manage.py generate_odata_selector myapp.MyModel [options]
```

Options:

| Option | Description |
|--------|-------------|
| `--single` | Generate one combined file |
| `--force` | Overwrite existing files |
| `--output` | Custom output directory |

---

## Exceptions

### Core Exceptions

```python
from fc_selector.core.exceptions import (
    SelectorError,        # Base class
    QueryError,           # Query processing errors
    FieldNotFoundError,   # Field doesn't exist
    InvalidFieldError,    # Field access denied (security)
    InvalidValueError,    # Invalid value for type
    TypeMismatchError,    # Type mismatch in operation
    UnsupportedFunctionError,  # Unsupported function
)
```

Core exceptions are framework-agnostic and are translated to OData exceptions at the protocol layer.

---

## Security

### Field Validation

The `AstToDjangoQVisitor` validates field names:

```python
# Constructor with optional allowed fields
visitor = AstToDjangoQVisitor(
    root_model=MyModel,
    allowed_fields={'id', 'name', 'status'}  # Optional whitelist
)
```

**Automatic protections:**
- Private fields (starting with `_`) are blocked
- Non-existent fields raise `InvalidFieldError`
- Fields not in `allowed_fields` (if specified) are rejected

### Parser Limits

```python
from fc_selector.protocols.odata.parsers.filter import MAX_FILTER_LENGTH

# Default: 4000 characters
# Exceeding this raises ODataSyntaxError
```
