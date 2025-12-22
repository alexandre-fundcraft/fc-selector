# OData Query Syntax

FC Selector uses OData v4 query syntax. This page covers all supported operators and functions.

## Query Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `$filter` | Filter results | `$filter=status eq 'published'` |
| `$select` | Select specific fields | `$select=id,title,author` |
| `$expand` | Include related entities | `$expand=author,categories` |
| `$orderby` | Sort results | `$orderby=created_at desc` |
| `$top` | Limit results | `$top=10` |
| `$skip` | Skip results | `$skip=20` |
| `$count` | Include total count | `$count=true` |

## $filter

### Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal | `status eq 'published'` |
| `ne` | Not equal | `status ne 'draft'` |
| `gt` | Greater than | `rating gt 4.0` |
| `ge` | Greater than or equal | `rating ge 4.0` |
| `lt` | Less than | `price lt 100` |
| `le` | Less than or equal | `price le 100` |

```bash
# Examples
$filter=status eq 'published'
$filter=rating gt 4.0
$filter=created_at ge 2024-01-01
```

### Logical Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `and` | Logical AND | `status eq 'published' and featured eq true` |
| `or` | Logical OR | `status eq 'draft' or status eq 'review'` |
| `not` | Logical NOT | `not featured` |

```bash
# Combined filters
$filter=status eq 'published' and rating gt 4.0
$filter=status eq 'published' and (featured eq true or rating gt 4.5)
$filter=not (status eq 'draft')
```

### String Functions

| Function | Description | Example |
|----------|-------------|---------|
| `contains` | Contains substring | `contains(title, 'Python')` |
| `startswith` | Starts with | `startswith(title, 'How')` |
| `endswith` | Ends with | `endswith(email, '@example.com')` |
| `tolower` | Convert to lowercase | `tolower(title) eq 'hello'` |
| `toupper` | Convert to uppercase | `toupper(status) eq 'PUBLISHED'` |

```bash
# String function examples
$filter=contains(title, 'Django')
$filter=startswith(title, 'Getting Started')
$filter=tolower(status) eq 'published'
```

### Null Checks

```bash
$filter=published_at eq null
$filter=published_at ne null
```

### Boolean Fields

```bash
$filter=featured eq true
$filter=is_active eq false
$filter=featured  # Shorthand for featured eq true
```

### Date/Time

```bash
$filter=created_at gt 2024-01-01
$filter=created_at ge 2024-01-01T00:00:00Z
$filter=created_at lt 2024-12-31
```

### Nested Properties

Access related entity properties with `/`:

```bash
$filter=author/name eq 'John'
$filter=author/email eq 'john@example.com'
$filter=author/profile/bio ne null
```

### Collection Operators

For ManyToMany and reverse ForeignKey relations:

```bash
# Any: at least one item matches
$filter=categories/any(c: c/name eq 'Python')
$filter=tags/any(t: contains(t/name, 'tutorial'))

# All: all items match
$filter=comments/all(c: c/approved eq true)
```

## $select

Choose which fields to return:

```bash
$select=id,title,status
$select=id,title,author
```

### Nested $select

Select fields from expanded relations:

```bash
$expand=author($select=name,email)
$expand=categories($select=id,name)
```

## $expand

Include related entities:

```bash
# Single relation
$expand=author

# Multiple relations
$expand=author,categories

# Nested expand
$expand=author($expand=profile)

# With nested $select
$expand=author($select=name,email)

# Combined
$expand=author($select=name;$expand=profile($select=bio))
```

## $orderby

Sort results:

```bash
# Ascending (default)
$orderby=title
$orderby=title asc

# Descending
$orderby=created_at desc

# Multiple fields
$orderby=featured desc,created_at desc

# Nested property
$orderby=author/name asc
```

## $top and $skip

Pagination:

```bash
# First 10 results
$top=10

# Skip first 20, take next 10 (page 3)
$top=10&$skip=20
```

## $count

Include total count in response:

```bash
$count=true
```

## Complex Examples

### Blog posts query

```bash
# Published posts with author, sorted by date, first 10
$filter=status eq 'published'&$select=id,title,excerpt,author&$expand=author($select=name)&$orderby=created_at desc&$top=10
```

### Search with filters

```bash
# Posts containing "Django" in title, published, high rating
$filter=contains(title, 'Django') and status eq 'published' and rating gt 4.0&$orderby=rating desc
```

### Nested relations

```bash
# Posts by specific author with categories
$filter=author/name eq 'John Doe'&$expand=author,categories&$select=id,title,author,categories
```

### Pagination with count

```bash
# Page 3 (10 items per page) with total count
$top=10&$skip=20&$count=true
```

## URL Encoding

Special characters must be URL-encoded:

| Character | Encoded |
|-----------|---------|
| Space | `%20` or `+` |
| `'` | `%27` |
| `"` | `%22` |
| `&` | `%26` |

```bash
# Original
$filter=title eq 'Hello World'

# URL encoded
$filter=title%20eq%20%27Hello%20World%27
```

Most HTTP clients handle encoding automatically.
