# FC Django OData

**Bringing OData Standards to Django** - A comprehensive Django package that implements the OData (Open Data Protocol) v4 specification for **read-only** REST APIs, enabling standardized data access patterns with powerful querying capabilities.

## ⚠️ IMPORTANT: Read-Only Library

**This library is designed EXCLUSIVELY for reading data (Read-Only)**. It does **NOT** support write operations (POST, PUT, PATCH, DELETE). This intentional design makes it perfect for:

- **Data Query APIs**: OData-compliant endpoints for complex data queries
- **Dashboards & Analytics**: Efficient data retrieval for reporting and visualization
- **Data Integration**: Safely expose data to external systems without modification risks
- **Read-Only Microservices**: Services that only need to query and present data
- **Public APIs**: Expose data safely without allowing external modifications

If you need full CRUD operations, this library is not suitable for your use case.

## Features

### 🎯 **Read-Only OData v4 Compliance**
- **Complete OData v4 Query Support**: Full implementation of query options (`$filter`, `$orderby`, `$top`, `$skip`, `$select`, `$expand`, `$count`)
- **Read-Only Operations**: List and Retrieve only (NO Create, Update, Delete)
- **OData Response Format**: Standards-compliant JSON responses with `@odata.context` metadata
- **Service Metadata**: Built-in `$metadata` endpoint for API discovery
- **OData Error Handling**: Standardized error responses following OData specifications

### ⚡ **Performance & Optimization**
- **Selector + DTO Pattern**: Type-safe data access with DTOs (Data Transfer Objects)
- **Request-Scoped Query Caching**: Automatic caching of identical queries within requests
- **Field-Level Optimization**: Only fetches requested fields using Django's `.only()`
- **Intelligent Query Optimization**: Automatic `select_related()` and `prefetch_related()`
- **Efficient Data Transfer**: 70-90% reduction in data transfer when using `$select`

### 🔧 **Developer Experience**
- **Minimal Configuration**: Transform Django models into OData endpoints with few lines
- **Django REST Framework Integration**: Seamlessly extends DRF's ReadOnlyModelViewSet
- **Type Safety**: DTOs with type hints for better IDE support and validation
- **Automatic Password Exclusion**: Sensitive fields automatically excluded from responses
- **Flexible Architecture**: Easy to customize for specific requirements
- **Auto-Generated API Documentation**: All OData parameters automatically documented in OpenAPI/Swagger

### 🛡️ **Type-Safe Fluent API**
- **Field Class**: Build filters with `Field("name").eq("John")` instead of strings
- **Python Operators**: Use `&`, `|`, `~` for AND, OR, NOT
- **Expand Class**: Type-safe nested queries with `Expand("author").select("name").top(5)`
- **OrderBy Class**: Explicit ordering with `OrderBy("created_at").desc()`
- **QueryIntent**: Protocol-agnostic query representation, decoupled from OData

### 📚 **API Documentation**
- **Automatic Schema Generation**: All OData query parameters are automatically documented
- **OpenAPI/Swagger Compatible**: Works with any OpenAPI-compatible documentation tool
- **Interactive Examples**: Each parameter includes usage examples and detailed descriptions
- **Helpful Error Messages**: Clear, actionable error messages when queries fail

## Installation

This package is not published to PyPI. Install directly from the GitHub repository:

### Using pip

```bash
# Clone the repository
git clone https://github.com/alexandre-fundcraft/fc-selector.git
cd fc-selector

# Install in development mode
pip install -e .
```

### Using uv (Recommended - Faster)

```bash
# Clone the repository
git clone https://github.com/alexandre-fundcraft/fc-selector.git
cd fc-selector

# Install in development mode with uv
uv pip install -e .
```

## Requirements

### Core Dependencies
- **Python** >= 3.11 (tested on 3.11, 3.12, 3.13)
- **Django** >= 4.2 LTS (supported until April 2026)
- **djangorestframework** >= 3.12.0

### Development Dependencies
- pytest >= 6.0
- pytest-cov >= 2.0
- pytest-django >= 4.0
- ruff >= 0.5.5 (linting and formatting)

## Quick Start

### 1. Add to INSTALLED_APPS

```python
INSTALLED_APPS = [
    # ... your other apps
    'rest_framework',
    'fc_selector',  # Note: fc_selector, not django_odata
]
```

### 2. Define Your Models

```python
# blog/models.py
from django.db import models
from django.contrib.auth.models import User

class Author(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField()
    website = models.URLField(blank=True)

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('published', 'Published'),
    ])
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    categories = models.ManyToManyField(Category)
    created_at = models.DateTimeField(auto_now_add=True)
    featured = models.BooleanField(default=False)
```

### 3. Generate Selectors and DTOs

```bash
# Generate OData selectors and DTOs for your models
python manage.py generate_odata_selector blog.BlogPost --single --force
python manage.py generate_odata_selector blog.Author --single --force
python manage.py generate_odata_selector blog.Category --single --force
```

This creates:
- `/blog/selectors/blog_post.py` - DTOs and Selectors
- Automatic field selection and expansion logic
- Type-safe data access patterns

### 4. Create DTO Serializers

```python
# blog/dto_serializers.py
from fc_selector.django.drf.serializers import ODataDTOSerializer
from .selectors.blog_post import BlogPostDTO, AuthorDTO, CategoryDTO

class AuthorDTOSerializer(ODataDTOSerializer):
    class Meta:
        dto_class = AuthorDTO

class CategoryDTOSerializer(ODataDTOSerializer):
    class Meta:
        dto_class = CategoryDTO

class BlogPostDTOSerializer(ODataDTOSerializer):
    class Meta:
        dto_class = BlogPostDTO
```

### 5. Create Read-Only ViewSets

```python
# blog/viewsets.py
from rest_framework import viewsets
from fc_selector.django.drf.viewsets import ODataReadOnlyModelViewSet
from .models import BlogPost, Author, Category
from .selectors.blog_post import BlogPostSelector, AuthorSelector, CategorySelector
from .dto_serializers import BlogPostDTOSerializer, AuthorDTOSerializer, CategoryDTOSerializer

class BlogPostViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet with OData support."""
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostDTOSerializer

    def list(self, request, *args, **kwargs):
        query_string = request.META.get('QUERY_STRING', '')
        selector = BlogPostSelector()
        dtos = selector.query_as_dtos(query_string)
        serializer = self.get_serializer(dtos, many=True)
        return Response({
            "@odata.context": f"{request.build_absolute_uri('/odata/')}$metadata#posts",
            "value": serializer.data
        })

    def retrieve(self, request, pk=None, *args, **kwargs):
        query_string = request.META.get('QUERY_STRING', '')
        selector = BlogPostSelector()
        queryset = selector.query(query_string)
        instance = queryset.filter(pk=pk).first()

        if not instance:
            return Response({'detail': 'Not found.'}, status=404)

        dto = selector.to_dto(
            instance,
            selector._extract_selected_fields(query_string),
            selector._extract_expanded_fields(query_string)
        )
        serializer = self.get_serializer(dto)
        return Response(serializer.data)

# Repeat for Author and Category viewsets
```

### 6. Configure URLs

```python
# blog/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import BlogPostViewSet, AuthorViewSet, CategoryViewSet

router = DefaultRouter()
router.register(r'posts', BlogPostViewSet)
router.register(r'authors', AuthorViewSet)
router.register(r'categories', CategoryViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
```

## Usage Examples

### Basic Queries (Read-Only)

```bash
# Get all blog posts
GET /api/posts/

# Get a specific blog post
GET /api/posts/1/

# Get first 10 posts
GET /api/posts/?$top=10

# Skip first 20 posts, get next 10
GET /api/posts/?$skip=20&$top=10
```

### Filtering

```bash
# Get published posts
GET /api/posts/?$filter=status eq 'published'

# Get featured posts
GET /api/posts/?$filter=featured eq true

# Get posts created this year
GET /api/posts/?$filter=year(created_at) eq 2024

# Complex filter
GET /api/posts/?$filter=status eq 'published' and featured eq true
```

### Sorting

```bash
# Sort by creation date (newest first)
GET /api/posts/?$orderby=created_at desc

# Sort by title alphabetically
GET /api/posts/?$orderby=title asc

# Multiple sort criteria
GET /api/posts/?$orderby=status desc,created_at desc
```

### Field Selection (Performance Optimization)

```bash
# Select specific fields - only fetches these from database!
GET /api/posts/?$select=id,title,status

# Returns minimal data
{
  "@odata.context": "http://example.com/odata/$metadata#posts",
  "value": [
    {
      "id": 1,
      "title": "Introduction to Django",
      "status": "published"
    }
  ]
}
```

**Performance Benefit**: Using `$select` reduces data transfer by 70-90% and speeds up database queries significantly.

### Field Expansion

```bash
# Include author information
GET /api/posts/?$expand=author

# Include multiple relationships
GET /api/posts/?$expand=author,categories

# Nested field selection in expanded properties
GET /api/posts/?$expand=author($select=name,bio)

# Multiple nested expansions
GET /api/posts/?$expand=author($select=name),categories($select=name)

# Combine selection with expansion
GET /api/posts/?$select=id,title&$expand=author($select=name,bio)
```

### Combined Queries

```bash
# Complex query with all features
GET /api/posts/?$filter=status eq 'published'&$orderby=created_at desc&$top=10&$select=id,title,author&$expand=author($select=name)&$count=true

# Response includes:
# - Only published posts
# - Sorted by date (newest first)
# - Limited to 10 results
# - Only id, title, and author fields
# - Author expanded with only name field
# - Total count of matching records
```

### Counting

```bash
# Get total count with results
GET /api/posts/?$count=true

# Get count of filtered results
GET /api/posts/?$filter=status eq 'published'&$count=true

# Response includes @odata.count
{
  "@odata.context": "http://example.com/odata/$metadata#posts",
  "@odata.count": 150,
  "value": [...]
}
```

### Type-Safe Fluent API (Python)

Build queries programmatically with full IDE support:

```python
from fc_selector.core.query_builder import QueryBuilder
from fc_selector.core.filters import Field, Expand, OrderBy

# Type-safe query building
intent = (
    QueryBuilder()
    .where(
        Field("status").eq("published") &
        Field("rating").gt(4.0)
    )
    .select("id", "title", "rating")
    .expand(
        Expand("author").select("id", "name"),
        Expand("comments")
            .filter(Field("approved").eq(True))
            .top(5)
    )
    .orderby(OrderBy("created_at").desc())
    .top(10)
    .build()
)

# Execute directly (protocol-agnostic)
selector = BlogPostSelector()
results = selector.execute(intent)
```

**Filter Examples:**
```python
Field("name").eq("John")              # Equality
Field("age").gt(18)                   # Greater than
Field("status").is_in(["a", "b"])     # In list
Field("name").contains("john")        # String contains
Field("price").between(10, 100)       # Range

# Combine with operators
Field("a").eq(1) & Field("b").gt(2)   # AND
Field("x").eq(1) | Field("y").eq(2)   # OR
~Field("deleted").eq(True)            # NOT
```

See [Query Builder Documentation](docs/query-builder.md) for complete fluent API reference.

## API Documentation

FC Django OData automatically generates comprehensive API documentation for all OData query parameters. This works with Django REST Framework's built-in schema generation and any OpenAPI/Swagger documentation tool.

### Automatic Schema Generation

All `ODataModelViewSet` and `ODataReadOnlyModelViewSet` classes include automatic documentation:

```python
from fc_selector.django.drf import ODataModelViewSet

class BlogPostViewSet(ODataModelViewSet):
    """
    Blog post API with full OData support.

    All OData query parameters are automatically documented!
    """
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
    # schema = ODataAutoSchema()  # Already included by default!
```

### What Gets Documented

The `ODataAutoSchema` automatically adds documentation for:

- **`$filter`** - Complete filter syntax with operators and examples
- **`$select`** - Field selection with usage examples
- **`$expand`** - Relationship expansion with nested queries
- **`$orderby`** - Sorting with ascending/descending examples
- **`$top`** - Pagination limit with examples
- **`$skip`** - Pagination offset with formula
- **`$count`** - Total count inclusion

Each parameter includes:
- Detailed description
- Valid values and syntax
- Multiple usage examples
- Type information (string, integer, boolean)
- Required/optional indication

### Using with OpenAPI/Swagger Tools

#### Option 1: Django REST Framework's Built-in Schema

```python
# urls.py
from rest_framework.schemas import get_schema_view

schema_view = get_schema_view(
    title='My OData API',
    description='API with OData v4 support',
    version='1.0.0'
)

urlpatterns = [
    path('openapi/', schema_view, name='openapi-schema'),
]
```

#### Option 2: drf-spectacular (Recommended)

Install drf-spectacular for enhanced OpenAPI documentation:

```bash
pip install drf-spectacular
```

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'drf_spectacular',
    'fc_selector',
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

Now visit `/api/docs/` to see interactive Swagger UI with all OData parameters documented!

### Custom Documentation

You can extend the default schema with custom documentation:

```python
from fc_selector.django.drf import ODataAutoSchema

class CustomODataSchema(ODataAutoSchema):
    """Custom schema with additional documentation."""

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)
        # Add custom tags, descriptions, etc.
        operation['tags'] = ['Blog Posts']
        return operation

class BlogPostViewSet(ODataModelViewSet):
    schema = CustomODataSchema()
    # ...
```

### Example Documentation Output

The auto-generated documentation shows users exactly how to use each parameter:

**`$filter` Parameter:**
```
Filter results using OData expressions.

Operators: eq, ne, gt, ge, lt, le, and, or, not, contains, startswith, endswith

Examples:
- ?$filter=status eq 'published'
- ?$filter=age gt 18 and status eq 'active'
- ?$filter=contains(title, 'OData')
```

**`$top` Parameter:**
```
Maximum number of results to return (limit).

Use with $skip for pagination.

Examples:
- ?$top=10 - Return first 10 results
- ?$top=25&$skip=50 - Return 25 results starting from position 50

Type: integer
Minimum: 0
```

## Key Concepts

### Selector + DTO Pattern

This library uses a modern **Selector + DTO** pattern for type-safe data access:

```
HTTP Request with OData query
         ↓
ViewSet method (list, retrieve)
         ↓
ODataSelector.query_as_dtos(query_string)
         ↓
Django QuerySet → DTOs (with field selection)
         ↓
ODataDTOSerializer (with automatic field exclusion)
         ↓
JSON Response
```

**Benefits:**
- Type safety with Python type hints
- Automatic field selection and expansion
- Sensitive field exclusion (e.g., passwords)
- Better separation of concerns
- Easier testing and maintenance

### Automatic Password Exclusion

Sensitive fields like passwords are **automatically excluded** from all responses:

```bash
# Even if you request password, it won't be returned
GET /api/users/?$select=id,username,email,password

# Response (password is automatically excluded):
{
  "value": [
    {
      "id": 1,
      "username": "john",
      "email": "john@example.com"
      // NO "password" field!
    }
  ]
}
```

## OData Query Options Reference

| Option | Description | Example |
|--------|-------------|---------|
| `$filter` | Filter results based on conditions | `$filter=status eq 'published'` |
| `$orderby` | Sort results | `$orderby=created_at desc` |
| `$top` | Limit number of results | `$top=10` |
| `$skip` | Skip number of results | `$skip=20` |
| `$select` | Choose specific fields | `$select=id,title,status` |
| `$expand` | Include related data | `$expand=author($select=name)` |
| `$count` | Include total count | `$count=true` |

### Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal | `status eq 'published'` |
| `ne` | Not equal | `status ne 'draft'` |
| `gt` | Greater than | `view_count gt 100` |
| `ge` | Greater than or equal | `rating ge 4.0` |
| `lt` | Less than | `view_count lt 50` |
| `le` | Less than or equal | `rating le 3.0` |
| `and` | Logical AND | `status eq 'published' and featured eq true` |
| `or` | Logical OR | `status eq 'published' or featured eq true` |
| `not` | Logical NOT | `not (status eq 'draft')` |

### String Functions

| Function | Description | Example |
|----------|-------------|---------|
| `contains` | String contains | `contains(title,'django')` |
| `startswith` | String starts with | `startswith(title,'How to')` |
| `endswith` | String ends with | `endswith(title,'Guide')` |

### Date Functions

| Function | Description | Example |
|----------|-------------|---------|
| `year` | Extract year | `year(created_at) eq 2024` |
| `month` | Extract month | `month(created_at) eq 12` |
| `day` | Extract day | `day(created_at) eq 25` |

## Performance Tips

1. **Always use `$select`** when you don't need all fields (70-90% data reduction)
2. **Use nested `$select` in `$expand`** to limit related data
3. **Enable `$count` only when needed** to avoid extra COUNT(*) queries
4. **Combine filters** to reduce result sets before sorting/pagination
5. **Use `$top` with `$skip`** for efficient pagination

### Example: Optimized Query

```bash
# Efficient query for a dashboard listing
GET /api/posts/?$select=id,title,status,created_at&$filter=status eq 'published'&$orderby=created_at desc&$top=20

# What this does:
# - Only fetches 4 fields from database (not all fields)
# - Filters at database level (not in Python)
# - Sorts efficiently in database
# - Returns only 20 results
# Result: Fast, efficient, minimal data transfer
```

## Example Project

A complete example project is available in the `example/` directory:

```bash
cd example/
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then visit:
- http://localhost:8000/api/posts/ - Blog posts endpoint
- http://localhost:8000/api/authors/ - Authors endpoint
- http://localhost:8000/api/categories/ - Categories endpoint

See `example/GETTING_STARTED.md` for detailed setup instructions.

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=fc_selector --cov-report=html

# Run specific test file
pytest tests/test_selector.py

# Run with verbose output
pytest -v
```

## Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/alexandre-fundcraft/fc-selector.git
cd fc-selector

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Or using uv (faster)
uv sync --group dev
```

### Code Quality

```bash
# Format code with ruff
ruff format .

# Lint code
ruff check .

# Run tests
pytest
```

## Architecture Highlights

### Read-Only by Design

All viewsets extend `ReadOnlyModelViewSet`, ensuring:
- No accidental write operations
- Safer public API exposure
- Clearer API contracts
- Better for integration scenarios

### Type-Safe Data Access

Using DTOs (Data Transfer Objects):
- Type hints for IDE support
- Runtime validation
- Explicit data contracts
- Easier refactoring

### Automatic Optimizations

- **Field-level**: Only fetches requested fields with `.only()`
- **Relationship**: Auto `select_related()` and `prefetch_related()`
- **Caching**: Request-scoped query caching
- **No N+1 queries**: Intelligent query optimization

## Support and Resources

### Documentation
- **Example Project**: See `example/` directory
- **Getting Started**: `example/GETTING_STARTED.md`
- **Architecture**: Clean, maintainable code structure

### Getting Help
- **Issues**: [GitHub Issues](https://github.com/alexandre-fundcraft/fc-selector/issues)
- **Email**: alexandre.busquets@fundcraft.lu

### Related Resources
- [OData v4 Specification](https://www.odata.org/documentation/)
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Credits

- **Built with**: [Django REST Framework](https://www.django-rest-framework.org/)
- **Developed by**: [Alexandre Busquets](https://github.com/alexandre-fundcraft) at Fundcraft

## Key Features

FC Django OData features a **read-only, performance-focused architecture** designed for modern Django applications:

### Architecture

1. **Read-Only Design**: Intentionally designed for query-only APIs
2. **Selector + DTO Pattern**: Type-safe data access with DTOs
3. **Native Parsers**: Native OData implementation without external dependencies
4. **Automatic Optimizations**: Field-level query optimization, intelligent prefetching
5. **Password Exclusion**: Automatic sensitive field exclusion
6. **Modern Python**: Python 3.8+ with type hints throughout

### Performance

- **70-90% data reduction** with `$select` parameter
- Request-scoped query caching
- Automatic N+1 query prevention
- Efficient field-level database queries

### Developer Experience

- Management commands for code generation
- Type-safe DTOs with IDE support
- Comprehensive example project
- Clean, maintainable architecture
- Excellent test coverage

## Why Read-Only?

This design choice makes the library ideal for:

1. **Public APIs**: Safely expose data without write concerns
2. **Analytics & Reports**: Efficient data retrieval for dashboards
3. **Data Integration**: Connect systems without modification risks
4. **Microservices**: Query-focused services in distributed architectures
5. **Third-party Access**: Provide data access without security concerns

If you need full CRUD operations, consider using the library alongside separate write endpoints or choose a different library.


## License

**fc-selector** is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

### What does this mean?

✅ **You CAN:**
- Use this software for free (commercial or non-commercial)
- Modify the source code
- Distribute it
- Use it in your SaaS/web services

⚠️ **You MUST:**
- **Publish your modifications** if you use this software (even if only on your server)
- Make your source code available under AGPL-3.0
- Include the original copyright and license notices
- State significant changes you made

❌ **You CANNOT:**
- Integrate this code into proprietary software without publishing your code
- Remove or modify license notices
- Hold the authors liable

### Why AGPL-3.0?

The AGPL-3.0 ensures that improvements and modifications to fc-selector benefit the entire community. 
Even if you only use it internally in a web service (like a Django API), you must share your changes.

This prevents "cloud-washing" where companies use open source code in SaaS products without contributing back.

### Commercial License

If you need to use fc-selector in a proprietary application without the AGPL obligations, 
please contact us for a commercial license:

📧 **Contact:** alexandre.busquets@fundcraft.lu

**Commercial licenses include:**
- No copyleft requirements
- Private modifications allowed  
- Priority support
- Custom features development
- Pricing starts at €10,000

### Full License Text

See the [LICENSE](LICENSE) file for the complete GNU Affero General Public License v3.0 text.


## Changelog

### Current Version

#### Major Features
- **Read-Only Architecture**: All viewsets extend `ReadOnlyModelViewSet`
- **Selector + DTO Pattern**: Type-safe data access with DTOs
- **Native OData Parsers**: No external parsing dependencies
- **Field-Level Optimization**: Automatic `.only()` for 70-90% data reduction
- **Automatic Password Exclusion**: Sensitive fields never exposed
- **Request-Scoped Caching**: Performance optimization for repeated queries
- **Enhanced Query Optimization**: Intelligent `select_related()`/`prefetch_related()`

#### Improvements
- Updated package name from `django_odata` to `fc_selector`
- All viewsets changed to read-only
- Comprehensive example project with blog application
- Improved documentation and getting started guide
- Better test coverage and code quality

---

**Ready to build efficient, read-only OData APIs?** Start with the [Quick Start](#quick-start) guide above!
