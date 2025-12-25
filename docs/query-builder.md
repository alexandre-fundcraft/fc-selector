# Query Builder

The `QueryBuilder` provides a fluent API for constructing OData queries.

## Basic Usage

```python
from fc_selector.django.selector import QueryBuilder

query = QueryBuilder()
query.filter("status eq 'published'")
query.select("id", "title")
query.top(10)

# Get the query string
query_string = query.build_query_string()
# "$filter=status eq 'published'&$select=id,title&$top=10"
```

## Method Chaining

All methods return `self`, enabling fluent chaining:

```python
query = (
    QueryBuilder()
    .filter("status eq 'published'")
    .select("id", "title", "author")
    .expand("author")
    .orderby("created_at desc")
    .top(10)
    .skip(20)
)
```

## Initialize from Existing Query

Parse an existing OData query string:

```python
# From request query string
query = QueryBuilder(request.META['QUERY_STRING'])

# Add more filters
query.and_filter("featured eq true")
```

## Filter Methods

### filter()

Set or replace the `$filter`:

```python
query.filter("status eq 'published'")
# $filter=status eq 'published'
```

### and_filter()

Add an AND condition:

```python
query = QueryBuilder()
query.filter("status eq 'published'")
query.and_filter("featured eq true")
# $filter=(status eq 'published') and (featured eq true)
```

### or_filter()

Add an OR condition:

```python
query = QueryBuilder()
query.filter("status eq 'published'")
query.or_filter("status eq 'featured'")
# $filter=(status eq 'published') or (status eq 'featured')
```

## Select

Choose which fields to return:

```python
# Multiple arguments
query.select("id", "title", "status")

# Comma-separated string
query.select("id,title,status")

# Both produce: $select=id,title,status
```

## Expand

Include related entities:

```python
# Multiple arguments
query.expand("author", "categories")

# Comma-separated string
query.expand("author,categories")

# Both produce: $expand=author,categories
```

## Order By

Sort results:

```python
# Single field
query.orderby("created_at desc")

# Multiple fields
query.orderby("featured desc", "created_at desc")

# Comma-separated
query.orderby("featured desc,created_at desc")
```

## Pagination

### top()

Limit the number of results:

```python
query.top(10)
# $top=10
```

### skip()

Skip a number of results:

```python
query.skip(20)
# $skip=20
```

### Combined pagination

```python
# Page 3 with 10 items per page
query.top(10).skip(20)
# $top=10&$skip=20
```

## Count

Request total count:

```python
query.count(True)
# $count=true
```

## Output Methods

### build_query_string()

Get the OData query string:

```python
query = QueryBuilder().filter("status eq 'published'").top(10)
query.build_query_string()
# "$filter=status eq 'published'&$top=10"
```

### to_dict()

Get as dictionary:

```python
query = QueryBuilder().filter("status eq 'published'").top(10)
query.to_dict()
# {'$filter': "status eq 'published'", '$top': '10'}
```

### String representation

```python
str(query)  # Same as build_query_string()
repr(query) # "QueryBuilder('$filter=status eq 'published'&$top=10')"
```

## Common Patterns

### Build query from request and add filters

```python
def get_posts(request, author_id: int = None):
    query = QueryBuilder(request.META.get('QUERY_STRING', ''))

    # Always filter by published
    query.and_filter("status eq 'published'")

    # Optional author filter
    if author_id:
        query.and_filter(f"author/id eq {author_id}")

    return selector.get_many(query)
```

### Reusable query builders

```python
def published_posts_query():
    return QueryBuilder().filter("status eq 'published'")

def featured_query():
    return QueryBuilder().filter("featured eq true")

# Combine
query = published_posts_query()
query.and_filter("featured eq true")
```

### Dynamic field selection

```python
def get_posts(request, include_content: bool = False):
    query = QueryBuilder(request.META.get('QUERY_STRING', ''))

    fields = ["id", "title", "status"]
    if include_content:
        fields.append("content")

    query.select(*fields)
    return selector.get_many(query)
```

## Complete Example

```python
from fc_selector.django.selector import QueryBuilder

# Build a complex query
query = (
    QueryBuilder()
    .filter("status eq 'published' and rating gt 4.0")
    .select("id", "title", "rating", "author")
    .expand("author")
    .orderby("rating desc", "created_at desc")
    .top(10)
    .skip(0)
    .count(True)
)

# Use with selector
selector = BlogPostSelector()
posts = selector.get_many(query)

# Or get the query string for API
query_string = query.build_query_string()
# "$filter=status eq 'published' and rating gt 4.0&$select=id,title,rating,author&$expand=author&$orderby=rating desc,created_at desc&$top=10&$skip=0&$count=true"
```

---

## Type-Safe Fluent API

For better IDE support, type safety, and reduced errors, use the fluent API classes instead of strings.

### Imports

```python
from fc_selector.django.selector import QueryBuilder
from fc_selector.core.filters import Field, Expand, OrderBy
```

### Field - Type-Safe Filters

Build filter expressions with full IDE autocompletion:

```python
# Comparisons
Field("name").eq("John")           # name eq 'John'
Field("age").gt(18)                # age gt 18
Field("price").ge(100)             # price ge 100
Field("count").lt(10)              # count lt 10
Field("rating").le(5)              # rating le 5
Field("status").ne("deleted")      # status ne 'deleted'

# Null checks
Field("deleted_at").is_null()      # deleted_at eq null
Field("email").is_not_null()       # email ne null

# String operations
Field("name").contains("john")     # contains(name, 'john')
Field("email").startswith("admin") # startswith(email, 'admin')
Field("email").endswith("@x.com")  # endswith(email, '@x.com')
Field("code").matches("^[A-Z]+$")  # matchesPattern(code, '^[A-Z]+$')

# Collections
Field("status").is_in(["active", "pending"])  # status in ('active', 'pending')
Field("role").not_in(["guest", "banned"])     # not (role in ('guest', 'banned'))

# Range
Field("price").between(10, 100)    # price ge 10 and price le 100

# Nested fields
Field("author.name").eq("John")    # author/name eq 'John'
Field("author").profile.city.eq("Barcelona")  # author/profile/city eq 'Barcelona'
```

### Logical Operators

Combine expressions with Python operators:

```python
# AND: use &
expr = Field("status").eq("active") & Field("age").gt(18)

# OR: use |
expr = Field("role").eq("admin") | Field("role").eq("superuser")

# NOT: use ~
expr = ~Field("deleted").eq(True)

# Complex expressions with parentheses
expr = (
    (Field("status").eq("active") & Field("age").gt(18))
    | Field("vip").eq(True)
)
```

### where() - Type-Safe Filter Method

Use `where()` instead of `filter()` for type-safe expressions:

```python
query = (
    QueryBuilder()
    .where(Field("status").eq("active") & Field("age").gt(18))
    .select("id", "name")
    .top(10)
)
```

### and_where() / or_where()

Add conditions to existing filters:

```python
# Combine with existing filter
query = (
    QueryBuilder("$filter=base eq 'value'")
    .and_where(Field("extra").gt(5))
    .or_where(Field("override").eq(True))
)
```

### Expand - Type-Safe Relations

Build expand expressions with nested options:

```python
# Simple expand
Expand("author")

# Expand with nested select
Expand("author").select("id", "name", "email")

# Expand with nested filter
Expand("comments").filter(Field("approved").eq(True))

# Expand with pagination and ordering
Expand("comments").top(5).skip(10).orderby(OrderBy("created_at").desc())

# Nested expand
Expand("author").expand(
    Expand("profile").select("avatar", "bio")
)

# Full example
Expand("comments")
    .select("id", "text", "created_at")
    .filter(Field("approved").eq(True))
    .orderby(OrderBy("created_at").desc())
    .top(5)
```

### OrderBy - Type-Safe Ordering

```python
# Ascending (default)
OrderBy("name")
OrderBy("name").asc()

# Descending
OrderBy("created_at").desc()

# Multiple in query
query.orderby(
    OrderBy("featured").desc(),
    OrderBy("created_at").desc(),
    OrderBy("title").asc()
)
```

### Complete Type-Safe Example

```python
from fc_selector.django.selector import QueryBuilder
from fc_selector.core.filters import Field, Expand, OrderBy

# Build a fully type-safe query
intent = (
    QueryBuilder()
    .where(
        Field("status").eq("published") &
        Field("rating").gt(4.0)
    )
    .select("id", "title", "rating")
    .expand(
        Expand("author").select("id", "name", "avatar"),
        Expand("comments")
            .filter(Field("approved").eq(True))
            .orderby(OrderBy("created_at").desc())
            .top(5)
    )
    .orderby(
        OrderBy("rating").desc(),
        OrderBy("created_at").desc()
    )
    .top(10)
    .build()
)

# Execute directly (protocol-agnostic)
selector = BlogPostSelector()
results = selector.execute(intent)
```

### QueryIntent - Protocol-Agnostic Output

The `build()` method returns a `QueryIntent` object instead of a string. This decouples your code from the OData protocol:

```python
# Build returns QueryIntent (not string)
intent = query.build()

# Execute directly without parsing
results = selector.execute(intent)

# Or convert to OData string if needed
odata_string = query.build_query_string()
```

### Mixing String and Fluent APIs

Both APIs can be combined:

```python
query = (
    QueryBuilder("$filter=legacy eq true")  # Parse existing query
    .and_where(Field("new_field").gt(5))         # Add type-safe filter
    .select("id", "name")                         # String-based select
    .expand(Expand("author").select("name"))      # Type-safe expand
    .orderby("created_at desc")                   # String-based orderby
    .top(10)
    .build()
)
```
