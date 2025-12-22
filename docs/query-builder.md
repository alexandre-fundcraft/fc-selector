# Query Builder

The `ODataQueryBuilder` provides a fluent API for constructing OData queries.

## Basic Usage

```python
from fc_selector.core import ODataQueryBuilder

query = ODataQueryBuilder()
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
    ODataQueryBuilder()
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
query = ODataQueryBuilder(request.META['QUERY_STRING'])

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
query = ODataQueryBuilder()
query.filter("status eq 'published'")
query.and_filter("featured eq true")
# $filter=(status eq 'published') and (featured eq true)
```

### or_filter()

Add an OR condition:

```python
query = ODataQueryBuilder()
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
query = ODataQueryBuilder().filter("status eq 'published'").top(10)
query.build_query_string()
# "$filter=status eq 'published'&$top=10"
```

### to_dict()

Get as dictionary:

```python
query = ODataQueryBuilder().filter("status eq 'published'").top(10)
query.to_dict()
# {'$filter': "status eq 'published'", '$top': '10'}
```

### String representation

```python
str(query)  # Same as build_query_string()
repr(query) # "ODataQueryBuilder('$filter=status eq 'published'&$top=10')"
```

## Common Patterns

### Build query from request and add filters

```python
def get_posts(request, author_id: int = None):
    query = ODataQueryBuilder(request.META.get('QUERY_STRING', ''))

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
    return ODataQueryBuilder().filter("status eq 'published'")

def featured_query():
    return ODataQueryBuilder().filter("featured eq true")

# Combine
query = published_posts_query()
query.and_filter("featured eq true")
```

### Dynamic field selection

```python
def get_posts(request, include_content: bool = False):
    query = ODataQueryBuilder(request.META.get('QUERY_STRING', ''))

    fields = ["id", "title", "status"]
    if include_content:
        fields.append("content")

    query.select(*fields)
    return selector.get_many(query)
```

## Complete Example

```python
from fc_selector.core import ODataQueryBuilder

# Build a complex query
query = (
    ODataQueryBuilder()
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
