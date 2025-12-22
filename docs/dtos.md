# DTOs (Data Transfer Objects)

DTOs are the return type of selectors. They provide a clean, typed interface for your data.

## What are DTOs?

DTOs are simple data containers that:

- Hold only the data you requested
- Are decoupled from the ORM
- Are type-safe (using dataclasses)
- Use `UNSET` for fields not selected

## The UNSET Sentinel

```python
from fc_selector.core.dtos import UNSET

@dataclass
class BlogPostDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET
    content: str = UNSET  # Large field
```

When you query with `$select=id,title`:

```python
dto = selector.get_one(
    ODataQueryBuilder().filter("id eq 1").select("id", "title")
)

dto.id       # 1
dto.title    # "My Post"
dto.content  # UNSET (not fetched)
```

### Checking for UNSET

```python
from fc_selector.core.dtos import UNSET

if dto.content is not UNSET:
    print(dto.content)
```

## Creating DTOs

### Auto-generated

Use the management command:

```bash
python manage.py generate_odata_selector myapp.BlogPost --single
```

### Manual Definition

```python
from dataclasses import dataclass
from typing import Optional, List
from fc_selector.core.dtos import BaseODataDTO, UNSET

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
    author: Optional[AuthorDTO] = UNSET
    categories: Optional[List[CategoryDTO]] = UNSET
```

## BaseODataDTO

All DTOs inherit from `BaseODataDTO`, which provides:

### from_model()

Converts a Django model instance to a DTO:

```python
# Manual conversion (usually done by selector)
dto = BlogPostDTO.from_model(
    blog_post_instance,
    selected_fields={'id', 'title'},
    expanded_fields={'author'}
)
```

Parameters:

- `instance` - Django model instance
- `selected_fields` - Set of field names to populate (None = all)
- `expanded_fields` - Set of relation names to expand
- `expand_options` - Nested options for expanded fields

## Nested DTOs

For relations, use `Optional[DTOType]` or `Optional[List[DTOType]]`:

```python
@dataclass
class BlogPostDTO(BaseODataDTO):
    # ForeignKey / OneToOne
    author: Optional[AuthorDTO] = UNSET

    # ManyToMany / Reverse ForeignKey
    categories: Optional[List[CategoryDTO]] = UNSET
```

When expanded:

```python
post = selector.get_one(
    ODataQueryBuilder()
    .filter("id eq 1")
    .expand("author")
)

post.author.name  # "John Doe"
```

When not expanded:

```python
post = selector.get_one(
    ODataQueryBuilder().filter("id eq 1")
)

post.author  # UNSET
```

## Nested $select

You can select specific fields from expanded relations:

```python
# OData query: $expand=author($select=name)
post = selector.get_one(
    ODataQueryBuilder()
    .filter("id eq 1")
    .expand("author($select=name)")
)

post.author.name   # "John Doe"
post.author.email  # UNSET (not selected)
```

## Properties in DTOs

You can include model properties in DTOs:

```python
# Model
class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()

    @property
    def word_count(self):
        return len(self.content.split())

# DTO (auto-generated)
@dataclass
class BlogPostDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET
    content: str = UNSET
    word_count: str = UNSET  # @property
```

## DTO Serializers

For DRF, use `ODataDTOSerializer`:

```python
from fc_selector.django.drf.serializers import ODataDTOSerializer

class BlogPostDTOSerializer(ODataDTOSerializer):
    class Meta:
        dto_class = BlogPostDTO

class UserDTOSerializer(ODataDTOSerializer):
    class Meta:
        dto_class = UserDTO
        exclude = ['password']  # Never expose password
```

The serializer:

- Automatically handles UNSET fields (omits them from output)
- Handles nested DTOs
- Supports `exclude` for sensitive fields
- Works with DRF's standard features

## Best Practices

### 1. Keep DTOs simple

DTOs should only contain data, no business logic:

```python
# Good
@dataclass
class BlogPostDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET

# Bad - don't add methods
@dataclass
class BlogPostDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET

    def publish(self):  # Don't do this
        ...
```

### 2. Use UNSET defaults

Always use `UNSET` as the default value:

```python
# Good
@dataclass
class BlogPostDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET

# Bad - None conflates "not selected" with "actually null"
@dataclass
class BlogPostDTO(BaseODataDTO):
    id: int = None
    title: str = None
```

### 3. Type relations correctly

```python
# ForeignKey / OneToOne: Optional[DTOType]
author: Optional[AuthorDTO] = UNSET

# ManyToMany / Reverse FK: Optional[List[DTOType]]
categories: Optional[List[CategoryDTO]] = UNSET
```

### 4. Exclude sensitive fields in serializers

```python
class UserDTOSerializer(ODataDTOSerializer):
    class Meta:
        dto_class = UserDTO
        exclude = ['password', 'secret_token']
```
