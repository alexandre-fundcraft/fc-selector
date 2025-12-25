# DTOs (Data Transfer Objects)

## What is a DTO?

A **DTO** (Data Transfer Object) is a simple object that carries data between layers.

It has no business logic, no ORM methods - just data.

## Why Not Return Django Models?

### The Problem: Returning Models

```python
def get_posts():
    return Post.objects.filter(status='published')
```

**Issues:**

1. **ORM Coupling** - Callers depend on Django ORM
2. **Lazy Loading** - Can trigger N+1 queries unexpectedly
3. **Mutation Risk** - Callers can call `.save()`, `.delete()`
4. **Unclear Contract** - What fields are actually loaded?

```python
posts = get_posts()

for post in posts:
    # Surprise! Each access triggers a query (N+1)
    print(post.author.name)

    # Surprise! Caller can mutate data
    post.status = 'deleted'
    post.save()
```

### The Solution: Returning DTOs

```python
def get_posts():
    return selector.get_many(query)  # Returns List[BlogPostDTO]
```

**Benefits:**

1. **No ORM** - Pure Python dataclass
2. **No Lazy Loading** - Data is there or it's UNSET
3. **Immutable** - No `.save()`, `.delete()` methods
4. **Clear Contract** - Type hints show exactly what's available

```python
posts = get_posts()

for post in posts:
    print(post.author.name)  # Works if expanded, UNSET if not
    # post.save()  ← Doesn't exist, can't accidentally mutate
```

## DTO Structure in FC Selector

```python
from dataclasses import dataclass
from typing import Optional, List
from fc_selector.core.dtos import BaseODataDTO, UNSET

@dataclass
class BlogPostDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET
    content: str = UNSET
    status: str = UNSET
    author: Optional[AuthorDTO] = UNSET
    categories: Optional[List[CategoryDTO]] = UNSET
```

## The UNSET Sentinel

`UNSET` is a special value that means "this field was not selected".

### Why Not Use None?

```python
# Problem with None
dto.content = None

# Does this mean:
# A) Content was not selected ($select didn't include it)
# B) Content is actually null in the database
#
# You can't tell!
```

### UNSET Makes It Clear

```python
from fc_selector.django.selector import QueryBuilder

# UNSET = field was not selected
# None = field was selected, value is null

query = QueryBuilder().select("id", "title")
dto = selector.get_one(query)

dto.id       # 1 (selected, has value)
dto.title    # "My Post" (selected, has value)
dto.content  # UNSET (not selected - we didn't ask for it)
dto.excerpt  # UNSET (not selected)

query2 = QueryBuilder().select("id", "excerpt")
dto2 = selector.get_one(query2)

dto2.excerpt  # None (selected, but value is null in DB)
```

### Checking UNSET

```python
from fc_selector.core.dtos import UNSET

if dto.content is not UNSET:
    print(dto.content)
else:
    print("Content was not loaded")
```

## DTOs and Serialization

When serializing to JSON, UNSET fields are omitted:

```python
# Query: $select=id,title
dto = BlogPostDTO(id=1, title="Hello", content=UNSET, status=UNSET)

# Serialized JSON:
{
    "id": 1,
    "title": "Hello"
    // content and status not included - they're UNSET
}
```

## Nested DTOs

For relationships, use `Optional[DTOType]`:

```python
@dataclass
class AuthorDTO(BaseODataDTO):
    id: int = UNSET
    name: str = UNSET
    email: str = UNSET

@dataclass
class BlogPostDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET
    author: Optional[AuthorDTO] = UNSET  # ForeignKey
    categories: Optional[List[CategoryDTO]] = UNSET  # ManyToMany
```

When expanded:
```python
query = QueryBuilder().expand("author")
dto = selector.get_one(query)

dto.author.name  # "John Doe"
```

When not expanded:
```python
query = QueryBuilder()  # No expand
dto = selector.get_one(query)

dto.author  # UNSET
```

## Summary

| Aspect | Django Model | DTO |
|--------|-------------|-----|
| ORM methods | `.save()`, `.delete()`, etc. | None |
| Lazy loading | Yes (N+1 risk) | No |
| Mutation | Possible | Not possible |
| Unselected fields | Deferred (confusing) | UNSET (explicit) |
| Type safety | Runtime | Compile-time hints |
| Serialization | Complex | Simple |

DTOs give you:
- **Clear contracts** - What you see is what you get
- **No surprises** - No lazy loading, no mutations
- **Clean separation** - Persistence layer stays hidden
