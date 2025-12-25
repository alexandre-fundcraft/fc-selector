# Benefits of FC Selector

## Why Use FC Selector?

FC Selector solves a fundamental problem in Django/DDD applications:

> **When using repositories, you always fetch the entire entity even when you only need a few fields.**

This causes performance problems, unnecessary data transfer, and tight coupling.

---

## Key Benefits

### 1. Fetch Only What You Need

**The Problem:**
```python
# Traditional repository
posts = repository.get_published()
# Returns ALL 20+ fields per post
# Including 50KB content field you don't need for a list view
```

**With FC Selector:**
```python
from fc_selector.django.selector import ODataSelector, QueryBuilder

posts = selector.get_many(
    QueryBuilder()
    .select("id", "title", "excerpt")  # Only these 3 fields
    .filter("status eq 'published'")
)
# Database only fetches id, title, excerpt
# 50x less data transferred
```

**Benefit:** Reduced database load, faster queries, less memory usage.

---

### 2. No More N+1 Query Problems

**The Problem:**
```python
posts = repository.get_all()  # 1 query
for post in posts:
    print(post.author.name)   # +1 query per post = N+1!
```

**With FC Selector:**
```python
posts = selector.get_many(
    QueryBuilder()
    .expand("author")  # Automatic select_related
)
# Single query with JOIN - no N+1
```

**Benefit:** Predictable, optimized queries without manual optimization.

---

### 3. One Selector Instead of Dozens of Repository Methods

**The Problem:**
```python
class PostRepository:
    def get_all(self): ...
    def get_by_id(self, id): ...
    def get_published(self): ...
    def get_by_author(self, author_id): ...
    def get_published_by_author(self, author_id): ...
    def get_featured(self): ...
    def get_by_category(self, category_id): ...
    def get_recent(self, limit): ...
    # ... 20+ methods for every combination
```

**With FC Selector:**
```python
class BlogPostSelector(ODataSelector):
    class Meta:
        model = BlogPost
        dto_class = BlogPostDTO

# All queries through one interface:
selector.get_many(QueryBuilder().filter("status eq 'published'"))
selector.get_many(QueryBuilder().filter("author/id eq 5"))
selector.get_many(QueryBuilder().filter("featured eq true").top(5))
```

**Benefit:** Less code, easier maintenance, consistent API.

---

### 4. Client Controls What Data It Receives

**The Problem:**
```python
# API always returns everything
GET /api/posts/
# Response: 20 fields per post, 50KB content included
# Even for a mobile app that only shows titles
```

**With FC Selector:**
```python
# Client requests only what it needs
GET /api/posts/?$select=id,title&$top=10
# Response: Only id and title, minimal payload
```

**Benefit:** Flexible APIs, optimized for each client (web, mobile, etc.).

---

### 5. Clean Separation: DTOs Instead of ORM Models

**The Problem:**
```python
# Returning Django models exposes ORM internals
def get_posts():
    return Post.objects.all()  # QuerySet leaked to callers
    # Callers can call .delete(), lazy load relations, etc.
```

**With FC Selector:**
```python
def get_posts():
    return selector.get_many(query)  # Returns List[BlogPostDTO]
    # Pure data objects, no ORM methods
    # No accidental lazy loading
    # No mutation possible
```

**Benefit:** True separation between persistence and business logic.

---

### 6. Type-Safe with Clear Contracts

**The Problem:**
```python
# What fields does this QuerySet actually have?
posts = Post.objects.filter(status='published')
# Unclear what's loaded, deferred, or available
```

**With FC Selector:**
```python
@dataclass
class BlogPostDTO:
    id: int = UNSET
    title: str = UNSET
    content: str = UNSET

# UNSET clearly indicates what was/wasn't selected
dto = selector.get_one(query.select("id", "title"))
dto.id       # Has value
dto.title    # Has value
dto.content  # UNSET - clearly not fetched
```

**Benefit:** Explicit data contracts, no surprises.

---

### 7. Automatic Query Optimization

FC Selector automatically optimizes queries:

| You write | FC Selector generates |
|-----------|----------------------|
| `.select("id", "title")` | `.only('id', 'title')` |
| `.expand("author")` | `.select_related('author')` |
| `.expand("categories")` | `.prefetch_related('categories')` |

**Benefit:** Optimal queries without manual Django ORM tuning.

---

### 8. Standard OData Syntax

Instead of inventing custom query parameters:

```python
# Custom (inconsistent across projects)
GET /api/posts/?fields=id,title&author_id=5&sort=-created_at

# OData (standard, well-documented)
GET /api/posts/?$select=id,title&$filter=author/id eq 5&$orderby=created_at desc
```

**Benefit:** Industry standard, consistent, self-documenting.

---

## Summary: Before vs After

| Aspect | Traditional Repository | FC Selector |
|--------|----------------------|-------------|
| Data fetched | All fields always | Only requested fields |
| N+1 queries | Manual optimization needed | Automatic |
| Methods needed | 20+ per entity | 1 selector per entity |
| API flexibility | Fixed responses | Client-controlled |
| Return type | QuerySet (ORM coupled) | DTO (pure data) |
| Type safety | Runtime errors | Compile-time + UNSET |
| Query syntax | Custom per project | Standard OData |

---

## When to Use FC Selector

**Use FC Selector when:**

- You have read-heavy APIs (dashboards, lists, reports)
- Different clients need different data subsets
- You want to avoid N+1 queries automatically
- You follow DDD/Clean Architecture
- You want consistent, standard query APIs

**Don't use FC Selector when:**

- You always need the full entity (rare)
- Write operations (use repositories for that)
- Simple CRUD without complex queries
