# Working with Selectors

## Creating a Selector

### Auto-generate from Model

The easiest way to create a selector is using the management command:

```bash
python manage.py generate_odata_selector myapp.BlogPost --single --force
```

Options:

- `--single` - Generate one file with all DTOs and selectors
- `--force` - Overwrite existing files

This generates:

```python
# myapp/selectors/blog_post.py
@dataclass
class BlogPostDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET
    content: str = UNSET
    author: Optional[AuthorDTO] = UNSET
    # ... all fields

class BlogPostSelector(ODataSelector):
    class Meta:
        model = BlogPost
        dto_class = BlogPostDTO
        expandable_fields = {
            'author': AuthorDTO,
        }
```

### Manual Definition

```python
from dataclasses import dataclass
from fc_selector.core.dtos import BaseODataDTO, UNSET
from fc_selector.django.selector import ODataSelector, QueryBuilder

@dataclass
class BlogPostDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET
    status: str = UNSET

class BlogPostSelector(ODataSelector):
    class Meta:
        model = BlogPost
        dto_class = BlogPostDTO
        expandable_fields = {}
```

## Selector Configuration

### Meta Options

```python
class BlogPostSelector(ODataSelector):
    class Meta:
        # Required: The Django model
        model = BlogPost

        # Required: The DTO class
        dto_class = BlogPostDTO

        # Optional: Relations that can be expanded
        expandable_fields = {
            'author': AuthorDTO,
            'categories': CategoryDTO,
        }

        # Optional: Field aliases for API-friendly names
        field_aliases = {
            'authorName': 'author__name',
            'createdAt': 'created_at',
        }
```

### Custom Base QuerySet

Override `get_queryset()` to customize the base query:

```python
class PublishedPostSelector(ODataSelector):
    class Meta:
        model = BlogPost
        dto_class = BlogPostDTO

    def get_queryset(self):
        # Only return published posts
        return BlogPost.objects.filter(status='published')
```

## Selector Methods

### get_many()

Get multiple DTOs matching a query.

```python
selector = BlogPostSelector()

# All posts
posts = selector.get_many()

# With filters
posts = selector.get_many(
    QueryBuilder()
    .filter("status eq 'published'")
    .orderby("created_at desc")
    .top(10)
)
```

### get_one()

Get a single DTO matching a query. Returns `None` if not found.

```python
post = selector.get_one(
    QueryBuilder()
    .filter("slug eq 'my-post'")
    .expand("author")
)
```

### get_by_pk()

Convenience method to get by primary key.

```python
post = selector.get_by_pk(1)

# With expand
post = selector.get_by_pk(
    1,
    QueryBuilder().expand("author", "categories")
)
```

### count_by()

Count matching records.

```python
count = selector.count_by(
    QueryBuilder().filter("status eq 'draft'")
)
```

### exists_by()

Check if any records match.

```python
exists = selector.exists_by(
    QueryBuilder().filter("slug eq 'my-post'")
)
```

## Raw Query Methods

These methods work with OData query strings directly:

### query()

Returns a Django QuerySet (not DTOs).

```python
queryset = selector.query("$filter=status eq 'published'&$top=10")
```

### query_as_dtos()

Returns a list of DTOs.

```python
dtos = selector.query_as_dtos(
    "$filter=status eq 'published'&$select=id,title"
)
```

### query_from_request()

Extract query string from a Django request.

```python
def my_view(request):
    queryset = selector.query_from_request(request)
```

## Query Optimization

FC Selector automatically optimizes queries:

### select_related()

Applied automatically for `$expand` on ForeignKey/OneToOne fields:

```python
# This query:
selector.get_many(
    QueryBuilder().expand("author")
)

# Generates:
BlogPost.objects.select_related('author')
```

### prefetch_related()

Applied automatically for `$expand` on ManyToMany fields:

```python
# This query:
selector.get_many(
    QueryBuilder().expand("categories")
)

# Generates:
BlogPost.objects.prefetch_related('categories')
```

### only()

Applied automatically for `$select`:

```python
# This query:
selector.get_many(
    QueryBuilder().select("id", "title")
)

# Generates:
BlogPost.objects.only('id', 'title')
```

## Field Restrictions

Control which fields can be filtered and sorted using a hybrid approach.

### Positive List (Secure by Default)

Explicitly list which fields are allowed:

```python
class BlogPostSelector(ODataSelector):
    class Meta:
        model = BlogPost
        dto_class = BlogPostDTO

        # Only these fields can be used in $filter
        filterable_fields = ["status", "created_at", "author_id"]

        # Only these fields can be used in $orderby
        sortable_fields = ["title", "created_at", "status"]
```

This is the **recommended approach** for security - new fields added to the model won't be exposed automatically.

### Negative List (Permissive)

Alternatively, allow all fields except specific exclusions:

```python
class BlogPostSelector(ODataSelector):
    class Meta:
        model = BlogPost
        dto_class = BlogPostDTO

        # All fields filterable EXCEPT these
        non_filterable_fields = ["password_hash", "internal_notes"]

        # All fields sortable EXCEPT these
        non_sortable_fields = ["content"]  # Long text, no sense sorting
```

### Priority Rules

1. If `filterable_fields` is defined → only those fields are filterable (ignores `non_filterable_fields`)
2. If only `non_filterable_fields` is defined → all fields except those are filterable
3. If neither is defined → all fields are filterable

Same logic applies to `sortable_fields`/`non_sortable_fields`.

### OData Metadata

These restrictions are automatically exposed in the `$metadata` endpoint following the OData Capabilities vocabulary:

```xml
<Annotation Target="ODataService.Container/posts"
            Term="Org.OData.Capabilities.V1.FilterRestrictions">
  <Record>
    <PropertyValue Property="Filterable" Bool="true"/>
    <PropertyValue Property="NonFilterableProperties">
      <Collection>
        <PropertyPath>password_hash</PropertyPath>
        <PropertyPath>internal_notes</PropertyPath>
      </Collection>
    </PropertyValue>
  </Record>
</Annotation>

<Annotation Target="ODataService.Container/posts"
            Term="Org.OData.Capabilities.V1.SortRestrictions">
  <Record>
    <PropertyValue Property="Sortable" Bool="true"/>
    <PropertyValue Property="NonSortableProperties">
      <Collection>
        <PropertyPath>content</PropertyPath>
      </Collection>
    </PropertyValue>
  </Record>
</Annotation>
```

This allows OData clients to discover which fields support filtering and sorting before making requests.

## Field Aliases

Map API-friendly names to internal field paths:

```python
class BlogPostSelector(ODataSelector):
    class Meta:
        model = BlogPost
        dto_class = BlogPostDTO
        field_aliases = {
            'authorName': 'author__name',
            'authorEmail': 'author__email',
            'createdAt': 'created_at',
        }
```

Now you can query with aliases:

```python
# API request
GET /api/posts/?$filter=authorName eq 'John'&$select=id,title,authorName

# Internally translates to
$filter=author__name eq 'John'&$select=id,title,author__name
```

## Complete Example

```python
from dataclasses import dataclass
from typing import Optional, List
from fc_selector.core.dtos import BaseODataDTO, UNSET
from fc_selector.django.selector import ODataSelector, QueryBuilder

# DTOs
@dataclass
class AuthorDTO(BaseODataDTO):
    id: int = UNSET
    name: str = UNSET
    email: str = UNSET

@dataclass
class CategoryDTO(BaseODataDTO):
    id: int = UNSET
    name: str = UNSET

@dataclass
class BlogPostDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET
    content: str = UNSET
    status: str = UNSET
    created_at: str = UNSET
    author: Optional[AuthorDTO] = UNSET
    categories: Optional[List[CategoryDTO]] = UNSET

# Selector
class BlogPostSelector(ODataSelector):
    class Meta:
        model = BlogPost
        dto_class = BlogPostDTO
        expandable_fields = {
            'author': AuthorDTO,
            'categories': CategoryDTO,
        }
        field_aliases = {
            'authorName': 'author__name',
        }

    def get_queryset(self):
        # Exclude soft-deleted posts
        return BlogPost.objects.filter(deleted_at__isnull=True)

# Usage
selector = BlogPostSelector()

# Get published posts with author
posts = selector.get_many(
    QueryBuilder()
    .filter("status eq 'published'")
    .select("id", "title", "authorName")
    .expand("author")
    .orderby("created_at desc")
    .top(10)
)
```
