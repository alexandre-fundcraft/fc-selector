# What is OData?

## OData in One Sentence

**OData** (Open Data Protocol) is a standard way to query data via URLs.

Instead of inventing your own query parameters, you use OData syntax that millions of developers already know.

## Why Not Invent Your Own?

### The Problem: Every API is Different

```bash
# Fictitious API A
GET /posts?fields=id,title&author_id=5&sort=-date&limit=10

# Fictitious API B
GET /posts?include=id,title&filter[author]=5&order=date:desc&per_page=10

# Fictitious API C
GET /posts?columns=id,title&where=author_id:5&orderby=date&dir=desc&take=10
```

**Problems:**
- Developers must learn a new syntax for each API
- Documentation burden for every project
- No tooling support
- Inconsistent error handling

### The Solution: OData Standard

```bash
# OData - same everywhere
GET /posts?$select=id,title&$filter=author/id eq 5&$orderby=date desc&$top=10
```

**Benefits:**
- Same syntax in Microsoft, SAP, Salesforce APIs
- Extensive documentation online
- Client libraries in every language
- Consistent, predictable behavior

## OData Query Parameters

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `$select` | Choose fields | `$select=id,title,status` |
| `$filter` | Filter results | `$filter=status eq 'published'` |
| `$expand` | Include relations | `$expand=author,categories` |
| `$orderby` | Sort results | `$orderby=created_at desc` |
| `$top` | Limit count | `$top=10` |
| `$skip` | Skip (offset) | `$skip=20` |
| `$count` | Include total | `$count=true` |

## $filter Syntax

### Comparison Operators

```bash
$filter=price eq 100      # Equal
$filter=price ne 100      # Not equal
$filter=price gt 100      # Greater than
$filter=price ge 100      # Greater or equal
$filter=price lt 100      # Less than
$filter=price le 100      # Less or equal
```

### Logical Operators

```bash
$filter=price gt 100 and status eq 'active'
$filter=status eq 'draft' or status eq 'review'
$filter=not (status eq 'deleted')
```

### String Functions

```bash
$filter=contains(title, 'Django')
$filter=startswith(name, 'John')
$filter=endswith(email, '@example.com')
```

### Nested Properties

```bash
$filter=author/name eq 'John'
$filter=author/company/country eq 'Spain'
```

### Collections (any/all)

```bash
$filter=categories/any(c: c/name eq 'Tech')
$filter=tags/all(t: t/active eq true)
```

## Real Examples

### Simple List
```bash
GET /posts?$top=10&$orderby=created_at desc
```

### Filtered with Field Selection
```bash
GET /posts?$filter=status eq 'published'&$select=id,title,excerpt
```

### With Related Data
```bash
GET /posts?$expand=author($select=name,email)&$filter=featured eq true
```

### Paginated with Count
```bash
GET /posts?$top=10&$skip=20&$count=true
```

### Complex Query
```bash
GET /posts?$filter=status eq 'published' and rating gt 4.0&$select=id,title,rating&$expand=author&$orderby=rating desc&$top=5
```

## Why FC Selector Uses OData

1. **No need to invent** - Standard already exists
2. **Documentation exists** - Microsoft, SAP docs apply
3. **Powerful** - Handles complex queries elegantly
4. **Familiar** - Many developers know it
5. **Tooling** - Client libraries, Swagger support

## OData is Just the Query Language

FC Selector uses OData as the **query syntax**, not as a full OData server.

```python
# OData query string
"$filter=status eq 'published'&$select=id,title"

# Parsed and converted to Django ORM
Post.objects.filter(status='published').only('id', 'title')
```

You get the expressive power of OData with the performance of Django ORM.
