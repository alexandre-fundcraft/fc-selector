<!-- markdownlint-disable MD024 -->
# The Selector Pattern

## What is a Selector?

A **Selector** is a read-only component that retrieves data using dynamic queries.

The Selector pattern is a recognized pattern in the Django community, popularized by the [HackSoft Django Styleguide](https://github.com/HackSoftware/Django-Styleguide) and implemented in libraries like [ai-django-core](https://ai-django-core.readthedocs.io/en/latest/features/selectors.html). It separates read operations from write operations, aligning with CQRS (Command Query Responsibility Segregation) principles.

Instead of creating dozens of repository methods for each query variation, a Selector provides one flexible interface.

## Problems It Solves

### Problem 1: Fetching More Data Than Needed

**Traditional approach:**
```python
# Repository always returns full entities
posts = repository.get_published()

# Each post has:
# - id, title, slug (needed)
# - content: 50KB of text (NOT needed for a list)
# - metadata, tags, timestamps (NOT needed)
# - author, categories (NOT needed)

# For 20 posts = 1MB+ of unnecessary data
```

**With Selector:**
```python
from fc_selector.django.selector import ODataSelector, QueryBuilder

posts = selector.get_many(
    QueryBuilder()
    .select("id", "title", "slug")  # Only what you need
    .filter("status eq 'published'")
)
# Database fetches ONLY id, title, slug
# ~1KB instead of 50KB per post
```

---

### Problem 2: N+1 Queries

**Traditional approach:**
```python
posts = repository.get_all()  # 1 query

for post in posts:
    print(post.author.name)    # +1 query (lazy load)
    print(post.categories)     # +1 query (lazy load)

# 20 posts = 1 + 20 + 20 = 41 queries!
```

**With Selector:**
```python
posts = selector.get_many(
    QueryBuilder()
    .expand("author", "categories")  # Eager load
)
# 1-2 queries total (JOIN or prefetch)
```

---

### Problem 3: Repository Method Explosion

**Traditional approach:**
```python
class PostRepository:
    def get_all(self): ...
    def get_by_id(self, id): ...
    def get_published(self): ...
    def get_drafts(self): ...
    def get_by_author(self, author_id): ...
    def get_published_by_author(self, author_id): ...
    def get_featured(self): ...
    def get_published_featured(self): ...
    def get_by_category(self, category_id): ...
    def get_recent(self, limit): ...
    def get_popular(self): ...
    def get_by_status(self, status): ...
    def get_by_date_range(self, start, end): ...
    # ... 30+ methods for every combination
```

**With Selector:**
```python
class BlogPostSelector(ODataSelector):
    class Meta:
        model = BlogPost
        dto_class = BlogPostDTO

# ONE selector handles ALL queries:
selector.get_many(query.filter("status eq 'published'"))
selector.get_many(query.filter("status eq 'draft'"))
selector.get_many(query.filter("author/id eq 5"))
selector.get_many(query.filter("status eq 'published' and author/id eq 5"))
selector.get_many(query.filter("featured eq true"))
selector.get_many(query.filter("categories/any(c: c/id eq 3)"))
selector.get_many(query.filter("created_at gt 2024-01-01"))
# Infinite combinations, zero new methods
```

---

### Problem 4: Inconsistent URL Parameters

**Traditional approach - every project invents its own:**
```bash
# Project A
GET /api/posts/?fields=id,title&author=5&sort=-created_at

# Project B
GET /api/posts/?include=id,title&filter[author]=5&order=created_at:desc

# Project C
GET /api/posts/?columns=id,title&author_id=5&orderby=created_at&dir=desc

# Developers must learn a new syntax for each API
```

**With Selector (OData standard):**
```bash
# Same syntax everywhere
GET /api/posts/?$select=id,title&$filter=author/id eq 5&$orderby=created_at desc

# OData is an industry standard:
# - Well documented
# - Same syntax in Microsoft, SAP, Salesforce APIs
# - Clients already know it
```

---

### Problem 5: Coupling API to ORM

**Traditional approach:**
```python
def get_posts():
    return Post.objects.filter(status='published')
    # Returns QuerySet - leaks Django ORM to callers
    # Callers can: .delete(), .update(), lazy load, etc.
```

**With Selector:**
```python
def get_posts():
    return selector.get_many(query)
    # Returns List[BlogPostDTO] - pure data
    # No ORM methods, no lazy loading, no mutations
```

---

### Problem 6: Manual Query Optimization

**Traditional approach:**
```python
# Developer must remember to optimize every query
posts = Post.objects.filter(
    status='published'
).select_related(
    'author'
).prefetch_related(
    'categories'
).only(
    'id', 'title', 'excerpt', 'author__name'
).order_by(
    '-created_at'
)[:20]

# Easy to forget .select_related() → N+1
# Easy to forget .only() → over-fetching
```

**With Selector:**
```python
posts = selector.get_many(
    QueryBuilder()
    .select("id", "title", "excerpt")
    .expand("author($select=name)")
    .filter("status eq 'published'")
    .orderby("created_at desc")
    .top(20)
)
# Automatic:
# - .only() from $select
# - .select_related() from $expand
# - .prefetch_related() for M2M
```

---

## Summary of Problems Solved

| Problem | Traditional | FC Selector |
|---------|------------|-------------|
| Over-fetching data | Fetch all fields always | `$select` fetches only needed |
| N+1 queries | Manual select_related | `$expand` auto-optimizes |
| Method explosion | 30+ methods per entity | 1 selector, infinite queries |
| URL syntax | Different per project | Standard OData |
| ORM coupling | QuerySet exposed | DTOs returned |
| Manual optimization | Remember .only(), etc. | Automatic |

## What is a Selector?

A Selector is simply:

1. **Read-only** - No create, update, delete
2. **Dynamic queries** - OData syntax for flexible filtering
3. **Returns DTOs** - Not ORM models
4. **Auto-optimized** - select_related, only, etc. applied automatically

```python
class BlogPostSelector(ODataSelector):
    class Meta:
        model = BlogPost           # Django model
        dto_class = BlogPostDTO    # What it returns
        expandable_fields = {      # Relations that can be expanded
            'author': AuthorDTO,
            'categories': CategoryDTO,
        }
```

That's it. One class, infinite queries, automatic optimization.
