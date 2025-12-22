# Getting Started - New System (Selector + QueryBuilder + DTO)

## ✅ New System Activated!

The example application now uses the **new system**: `ODataSelector` + `ODataQueryBuilder` + `DTOs` + `ODataDTOSerializer`.

## ⚠️ IMPORTANT: Read-Only Library

**This library is designed ONLY for reading data (Read-Only)**. It does not allow modification operations like POST, PUT, PATCH or DELETE. It's perfect for:
- OData query APIs
- Dashboards and reports
- Integrations that only need to read data
- Safely exposing data to external systems

## 🚀 Available Endpoints

### Blog Posts (Read-Only)
```
GET    http://localhost:8000/api/posts/                    - List with OData
GET    http://localhost:8000/api/posts/{id}/               - Retrieve

# Custom actions (read-only)
GET    http://localhost:8000/api/posts/published/          - Published only
GET    http://localhost:8000/api/posts/featured/           - Featured only
GET    http://localhost:8000/api/posts/by-author/{id}/     - By author
GET    http://localhost:8000/api/posts/{id}/stats/         - Statistics
```

### Authors (Read-Only)
```
GET    http://localhost:8000/api/authors/                  - List
GET    http://localhost:8000/api/authors/{id}/             - Retrieve
GET    http://localhost:8000/api/authors/{id}/posts/       - Author's posts
```

### Users (Read-Only)
```
GET    http://localhost:8000/api/users/                    - List (password excluded!)
GET    http://localhost:8000/api/users/{id}/               - Retrieve
GET    http://localhost:8000/api/users/active/             - Active only
GET    http://localhost:8000/api/users/me/                 - Current user
```

### Categories (Read-Only)
```
GET    http://localhost:8000/api/categories/               - List
GET    http://localhost:8000/api/categories/{id}/          - Retrieve
GET    http://localhost:8000/api/categories/{id}/posts/    - Category posts
```

## 📝 Usage Examples

### 1. List Posts with OData

```bash
# List all
curl http://localhost:8000/api/posts/

# Select specific fields
curl "http://localhost:8000/api/posts/?$select=id,title,status"

# Expand relationships
curl "http://localhost:8000/api/posts/?$expand=author,categories"

# Filter
curl "http://localhost:8000/api/posts/?$filter=status eq 'published'"

# Order by
curl "http://localhost:8000/api/posts/?$orderby=created_at desc"

# Pagination
curl "http://localhost:8000/api/posts/?$top=10&$skip=0"

# Complex query
curl "http://localhost:8000/api/posts/?$select=id,title,author&$expand=author&$filter=status eq 'published'&$orderby=created_at desc&$top=10"
```

### 2. Retrieve Post with Expand

```bash
# Get post with author and categories
curl "http://localhost:8000/api/posts/1/?$expand=author,categories"

# Response:
{
    "id": 1,
    "title": "My Post",
    "content": "...",
    "author": {
        "id": 1,
        "name": "John Doe",
        "email": "john@example.com"
    },
    "categories": [
        {"id": 1, "name": "Tech"},
        {"id": 2, "name": "Django"}
    ]
}
```

### 3. Custom Actions (Read-Only)

```bash
# Get published posts
curl "http://localhost:8000/api/posts/published/?$orderby=published_at desc&$top=10"

# Get posts by author
curl "http://localhost:8000/api/posts/by-author/1/?$filter=status eq 'published'"

# Get post stats
curl http://localhost:8000/api/posts/1/stats/
```

### 4. Users (Password Automatically Excluded!)

```bash
# List users (password NOT included!)
curl http://localhost:8000/api/users/

# Even if explicitly requested, it does NOT return it!
curl "http://localhost:8000/api/users/?$select=id,username,email,password"

# Response:
[
    {
        "id": 1,
        "username": "john",
        "email": "john@example.com"
        // NO "password" field!
    }
]

# Get current user
curl http://localhost:8000/api/users/me/ \
  -H "Authorization: Token YOUR_TOKEN"

# Get active users
curl "http://localhost:8000/api/users/active/?$select=id,username"
```

### 5. Authors with Posts

```bash
# Get author with posts
curl "http://localhost:8000/api/authors/1/posts/?$filter=status eq 'published'&$select=id,title"
```

## 🔧 Setup (if new project)

### 1. Generate DTOs and Selectors

```bash
cd /Users/alexandre.busquets/Repos/fc-selector/example
python manage.py generate_odata_selector blog.BlogPost --single --force
```

This creates:
- `/blog/selectors/blog_post.py` - DTOs and Selectors
- `/blog/dto_serializers.py` - Serializers (already created)

### 2. Create Test Data

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
from blog.models import Author, BlogPost, Category

# Create user
user = User.objects.create_user('john', 'john@example.com', 'password123')

# Create author
author = Author.objects.create(
    user=user,
    bio='Test author bio',
    website='https://example.com'
)

# Create category
tech = Category.objects.create(
    name='Technology',
    description='Tech posts'
)

django_cat = Category.objects.create(
    name='Django',
    description='Django framework'
)

# Create blog post
post = BlogPost.objects.create(
    title='My First Post',
    slug='my-first-post',
    content='This is the content of my first post...',
    excerpt='Short excerpt',
    status='published',
    author=author,
    featured=True
)

# Add categories
post.categories.add(tech, django_cat)

print(f"✓ Created: {post.title}")
```

### 3. Run Server

```bash
python manage.py runserver
```

### 4. Test Endpoints

```bash
# Basic list
curl http://localhost:8000/api/posts/

# With OData
curl "http://localhost:8000/api/posts/?$select=id,title&$expand=author"
```

## 🎯 New System Features

### ✅ What Works Now

1. **OData Query Support** - $select, $expand, $filter, $orderby, $top, $skip
2. **Automatic Field Selection** - Only returns selected fields
3. **Automatic Expansion** - Nested DTOs automatically
4. **Password Exclusion** - Password ALWAYS excluded (even if you request it!)
5. **Custom Read Actions** - published, by-author, stats, etc.
6. **Read-Only Operations** - List and Retrieve (NO Create, Update, Delete)
7. **Permissions** - Configurable per endpoint
8. **Nested DTOs** - author, categories, etc. automatic

### 🔄 Complete Flow

```
HTTP Request with OData query
         ↓
ViewSet method (list, retrieve, etc.)
         ↓
ODataQueryBuilder.from_query_string(query_string)
         ↓
ODataSelector.get_one(query) / get_many(query)
         ↓
DTOs (with field selection, no queryset exposed)
         ↓
ODataDTOSerializer (with field exclusion: password!)
         ↓
JSON Response
```

### Key Principle: No ORM Exposure

The new architecture follows hexagonal/clean architecture principles:

```python
# Good - using ODataQueryBuilder (pure OData, no ORM exposure)
query = ODataQueryBuilder.from_query_string(query_string).and_filter(f"id eq {pk}")
dto = selector.get_one(query)

# Bad - exposing queryset (old pattern)
queryset = selector.query(query_string)
instance = queryset.filter(pk=pk).first()
```

### 🆚 Comparison: Old vs New System

| Feature | Old | New |
|---------|-----|-----|
| Query Building | Query string parsing | ODataQueryBuilder (fluent API) |
| Data Access | Exposes QuerySet | Returns DTOs directly |
| Models → JSON | ODataModelSerializer | Selector → DTO → DTOSerializer |
| Field Selection | DRF fields | DTO with UNSET sentinel |
| Password | Manual exclusion | **AUTOMATIC** |
| Nested Objects | Manual config | **AUTOMATIC** (type hints) |
| OData Support | ✅ | ✅ |
| Custom Actions | ✅ | ✅ (read-only) |
| Type Safety | ❌ | ✅ (DTOs) |
| ORM Exposure | QuerySet exposed | **NO** (hexagonal) |
| Write Operations | ❌ Not supported | ❌ Not supported (read-only) |

## 📚 Additional Documentation

- **ViewSets**: `blog/viewsets.py` - Complete implementation
- **DTOs**: `blog/selectors/blog_post.py` - Generated DTOs
- **Serializers**: `blog/dto_serializers.py` - Customization
- **URLs**: `example/urls.py` - OData metadata registration
- **Guide**: `VIEWSET_EXAMPLES.md` - Complete guide

## 🔧 Automatic OData Metadata

The library provides automatic `$metadata` generation. Register your selectors in `urls.py`:

```python
from fc_odata.django import (
    ODataMetadataView,
    ODataServiceDocumentView,
    ODataMetadataRegistry,
)

# Register selectors for automatic metadata generation
ODataMetadataRegistry.set_namespace("MyService")
ODataMetadataRegistry.register("posts", BlogPostSelector)
ODataMetadataRegistry.register("authors", AuthorSelector)

urlpatterns = [
    # ... your other urls ...
    path("odata/$metadata", ODataMetadataView.as_view(), name="odata-metadata"),
    path("odata/", ODataServiceDocumentView.as_view(), name="odata-service"),
]
```

Now `GET /odata/$metadata` returns auto-generated EDM schema.

## 🐛 Troubleshooting

### Error: "cannot import name 'BlogPostSelector'"

Solution: Generate the selectors:
```bash
python manage.py generate_odata_selector blog.BlogPost --single --force
```

### Error: "cannot import name 'BlogPostDTOSerializer'"

Solution: The file already exists at `blog/dto_serializers.py`. Verify it's correct.

### Password still visible

Impossible! The `UserDTOSerializer` has `exclude = ['password']`. If you see it, check that you're using `UserDTOSerializer`, not another serializer.

### $expand not working

Make sure:
1. The field exists in the DTO
2. The field is in `expandable_fields` of the Selector
3. You're making the query correctly: `?$expand=author`

## 🎉 Done!

You now have a complete system running with:
- ✅ ODataQueryBuilder for fluent query construction
- ✅ OData queries ($select, $filter, $expand, $orderby, $top, $skip)
- ✅ DTOs with type safety
- ✅ No ORM/QuerySet exposure (hexagonal architecture)
- ✅ Automatic password exclusion
- ✅ Automatic nested objects
- ✅ Custom read-only actions
- ✅ Read-Only API (List + Retrieve)

Try it:
```bash
curl "http://localhost:8000/api/posts/?$select=id,title&$expand=author&$filter=status eq 'published'"
```
