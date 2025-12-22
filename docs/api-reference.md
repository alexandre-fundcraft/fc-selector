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
```

### Methods

#### get_many(query_builder=None) -> List[DTO]

Get multiple DTOs.

```python
posts = selector.get_many()
posts = selector.get_many(ODataQueryBuilder().filter("status eq 'published'"))
```

#### get_one(query_builder) -> Optional[DTO]

Get a single DTO. Returns `None` if not found.

```python
post = selector.get_one(ODataQueryBuilder().filter("slug eq 'my-post'"))
```

#### get_by_pk(pk, query_builder=None) -> Optional[DTO]

Get by primary key.

```python
post = selector.get_by_pk(1)
post = selector.get_by_pk(1, ODataQueryBuilder().expand("author"))
```

#### count_by(query_builder=None) -> int

Count matching records.

```python
count = selector.count_by(ODataQueryBuilder().filter("status eq 'draft'"))
```

#### exists_by(query_builder=None) -> bool

Check if any records match.

```python
exists = selector.exists_by(ODataQueryBuilder().filter("slug eq 'my-post'"))
```

#### query(query_string, model_class=None, base_queryset=None) -> QuerySet

Execute raw query string, return QuerySet.

```python
queryset = selector.query("$filter=status eq 'published'")
```

#### query_as_dtos(query_string, model_class=None, base_queryset=None) -> List[DTO]

Execute raw query string, return DTOs.

```python
dtos = selector.query_as_dtos("$filter=status eq 'published'&$select=id,title")
```

#### get_queryset() -> QuerySet

Override to customize base QuerySet.

```python
def get_queryset(self):
    return MyModel.objects.filter(deleted_at__isnull=True)
```

---

## ODataQueryBuilder

Fluent API for building OData queries.

```python
from fc_selector.core import ODataQueryBuilder
```

### Constructor

```python
# Empty
query = ODataQueryBuilder()

# From existing query string
query = ODataQueryBuilder("$filter=status eq 'published'")
```

### Methods

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

```python
from fc_selector.exceptions import (
    ODataFilterError,
    ODataFieldNotFoundError,
    ODataInvalidFilterSyntaxError,
    ODataInvalidOperatorError,
    ODataInvalidValueError,
    ODataExpandError,
    ODataInvalidPaginationError,
)
```

All exceptions inherit from `ODataFilterError` and produce OData-compliant error responses.
