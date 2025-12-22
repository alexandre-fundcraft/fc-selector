"""
OData Selector ViewSet Mixin.

Provides OData support using the Selector + DTO pattern for hexagonal architecture.
"""

from django.conf import settings
from django.db import connection, reset_queries
from rest_framework import status
from rest_framework.response import Response

try:
    from drf_spectacular.types import OpenApiTypes
    from drf_spectacular.utils import OpenApiParameter, extend_schema
    HAS_SPECTACULAR = True
except ImportError:
    HAS_SPECTACULAR = False


# OData parameter definitions for drf-spectacular
ODATA_PARAMETERS = [
    {
        "name": "$filter",
        "type": OpenApiTypes.STR if HAS_SPECTACULAR else str,
        "location": "query",
        "required": False,
        "description": """OData filter expression.

**Comparison operators:** `eq`, `ne`, `gt`, `ge`, `lt`, `le`
**Logical operators:** `and`, `or`, `not`
**String functions:** `contains()`, `startswith()`, `endswith()`, `tolower()`, `toupper()`

**Examples:**
- `status eq 'published'`
- `rating gt 4.0 and status eq 'published'`
- `contains(title, 'Django')`
- `author/name eq 'John'`
- `categories/any(c: c/id eq 1)`""",
        "examples": [
            {"name": "equality", "value": "status eq 'published'"},
            {"name": "comparison", "value": "rating gt 4.0"},
            {"name": "combined", "value": "status eq 'published' and featured eq true"},
            {"name": "contains", "value": "contains(title, 'Django')"},
            {"name": "nested", "value": "author/name eq 'John'"},
        ],
    },
    {
        "name": "$select",
        "type": OpenApiTypes.STR if HAS_SPECTACULAR else str,
        "location": "query",
        "required": False,
        "description": """Comma-separated list of fields to return.

Only selected fields are fetched from the database, improving performance.

**Examples:**
- `id,title,status`
- `id,title,author`""",
        "examples": [
            {"name": "minimal", "value": "id,title"},
            {"name": "with_relation", "value": "id,title,author,created_at"},
        ],
    },
    {
        "name": "$expand",
        "type": OpenApiTypes.STR if HAS_SPECTACULAR else str,
        "location": "query",
        "required": False,
        "description": """Comma-separated list of relations to expand (eager load).

**Examples:**
- `author`
- `author,categories`
- `author($select=id,name)` - with nested $select""",
        "examples": [
            {"name": "single", "value": "author"},
            {"name": "multiple", "value": "author,categories"},
            {"name": "nested_select", "value": "author($select=id,name)"},
        ],
    },
    {
        "name": "$orderby",
        "type": OpenApiTypes.STR if HAS_SPECTACULAR else str,
        "location": "query",
        "required": False,
        "description": """Comma-separated list of fields to sort by.

Use `asc` (default) or `desc` after field name.

**Examples:**
- `created_at desc`
- `title asc`
- `featured desc,created_at desc`""",
        "examples": [
            {"name": "descending", "value": "created_at desc"},
            {"name": "multiple", "value": "featured desc,created_at desc"},
        ],
    },
    {
        "name": "$top",
        "type": OpenApiTypes.INT if HAS_SPECTACULAR else int,
        "location": "query",
        "required": False,
        "description": """Maximum number of results to return (limit).

**Examples:**
- `10` - Return first 10 results
- Use with `$skip` for pagination""",
    },
    {
        "name": "$skip",
        "type": OpenApiTypes.INT if HAS_SPECTACULAR else int,
        "location": "query",
        "required": False,
        "description": """Number of results to skip (offset).

**Pagination:**
- Page 1: `$top=10&$skip=0`
- Page 2: `$top=10&$skip=10`
- Page 3: `$top=10&$skip=20`""",
    },
    {
        "name": "$count",
        "type": OpenApiTypes.BOOL if HAS_SPECTACULAR else bool,
        "location": "query",
        "required": False,
        "description": """Include total count in response.

When `true`, response includes `@odata.count` with total results.""",
    },
]


def get_odata_openapi_parameters():
    """Get OpenApiParameter list for drf-spectacular."""
    if not HAS_SPECTACULAR:
        return []

    params = []
    for p in ODATA_PARAMETERS:
        param = OpenApiParameter(
            name=p["name"],
            type=p["type"],
            location=OpenApiParameter.QUERY,
            required=p.get("required", False),
            description=p["description"],
        )
        params.append(param)
    return params


def build_odata_response(request, serializer_data, query_string, entity_set_name, selector=None):
    """
    Build OData-compliant response with pagination, count, and debug info.

    Args:
        request: Django request object
        serializer_data: Serialized data to return
        query_string: OData query string
        entity_set_name: Name of the entity set (posts, authors, etc.)
        selector: Optional selector instance for count queries

    Returns:
        dict: OData response with @odata.context, value, @odata.count, @odata.nextLink, @debug
    """
    response_data = {
        "@odata.context": f"{request.build_absolute_uri('/odata/')}$metadata#{entity_set_name}",
        "value": serializer_data
    }

    # Parse query string
    parsed_qs = {}
    for param in query_string.split('&'):
        if '=' in param:
            key, value = param.split('=', 1)
            parsed_qs[key] = value

    # Add OData count if requested
    if '$count' in parsed_qs and parsed_qs.get('$count', '').lower() == 'true':
        if selector:
            # Remove $count from query to get accurate count
            count_query = '&'.join([f"{k}={v}" for k, v in parsed_qs.items() if k != '$count'])
            total_count = selector.query(count_query).count()
            response_data["@odata.count"] = total_count

    # Add pagination links (nextLink)
    top = int(parsed_qs.get('$top', 50))
    skip = int(parsed_qs.get('$skip', 0))

    # Check if there are more results
    if len(serializer_data) == top:  # If we got exactly 'top' results, there might be more
        next_skip = skip + top
        # Build next link
        next_params = parsed_qs.copy()
        next_params['$skip'] = str(next_skip)
        next_query = '&'.join([f"{k}={v}" for k, v in next_params.items()])
        response_data["@odata.nextLink"] = f"{request.build_absolute_uri(request.path)}?{next_query}"

    # Add debug queries if in debug mode
    if settings.DEBUG and hasattr(connection, 'queries'):
        queries = connection.queries
        response_data["@debug"] = {
            "query_count": len(queries),
            "queries": [
                {
                    "sql": q['sql'],
                    "time": q['time']
                }
                for q in queries
            ],
            "total_time": f"{sum(float(q['time']) for q in queries):.4f}"
        }

    return response_data


class ODataSelectorViewSetMixin:
    """
    Mixin to add OData support to ViewSets using the Selector + DTO pattern.

    This mixin follows hexagonal architecture principles:
    - Uses ODataSelector for data access (no QuerySet exposure)
    - Returns DTOs instead of Django model instances
    - Supports full OData query syntax

    Requires:
    - selector_class: The Selector class to use
    - odata_entity_set_name: Name of the entity set for OData metadata

    Example:
        class BlogPostViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
            selector_class = BlogPostSelector
            odata_entity_set_name = "posts"
            serializer_class = BlogPostDTOSerializer

            # list() and retrieve() are provided by the mixin
    """

    selector_class = None
    odata_entity_set_name = None

    def get_selector(self):
        """Get an instance of the selector class."""
        if self.selector_class is None:
            raise NotImplementedError(f"{self.__class__.__name__} must define 'selector_class'")
        return self.selector_class()

    def get_list_schema_decorator(self):
        """Get the extend_schema decorator for list action."""
        if not HAS_SPECTACULAR:
            return lambda f: f
        return extend_schema(
            parameters=get_odata_openapi_parameters(),
            description="List entities with OData query support.",
        )

    def get_retrieve_schema_decorator(self):
        """Get the extend_schema decorator for retrieve action."""
        if not HAS_SPECTACULAR:
            return lambda f: f
        return extend_schema(
            parameters=[
                p for p in get_odata_openapi_parameters()
                if p.name in ('$select', '$expand')
            ],
            description="Retrieve a single entity. Supports $select and $expand.",
        )

    def list(self, request, *args, **kwargs):
        """
        List entities with full OData support.

        Supports: $filter, $select, $expand, $orderby, $top, $skip, $count

        Returns DTOs serialized to JSON with OData metadata.
        """
        # Reset queries to track only this request
        if settings.DEBUG:
            reset_queries()

        # Get OData query string from request
        query_string = request.META.get('QUERY_STRING', '')

        # Use selector to query database with OData parameters
        selector = self.get_selector()
        dtos = selector.query_as_dtos(query_string)

        # Serialize DTOs to JSON
        serializer = self.get_serializer(dtos, many=True)

        # Build OData response with pagination
        response_data = build_odata_response(
            request=request,
            serializer_data=serializer.data,
            query_string=query_string,
            entity_set_name=self.odata_entity_set_name,
            selector=selector
        )

        return Response(response_data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        Retrieve a single entity with OData support.

        Uses ODataQueryBuilder to filter by pk without exposing QuerySet.
        """
        from fc_selector.core import ODataQueryBuilder

        # Get OData query string
        query_string = request.META.get('QUERY_STRING', '')

        # Use selector with ODataQueryBuilder (no QuerySet exposure)
        selector = self.get_selector()

        # Build query with pk filter using pure OData syntax
        query = ODataQueryBuilder(query_string).and_filter(f"id eq {pk}")
        dto = selector.get_one(query)

        if not dto:
            return Response(
                {'detail': 'Not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serialize
        serializer = self.get_serializer(dto)

        return Response(serializer.data)
