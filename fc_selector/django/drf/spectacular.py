"""
OData query parameter documentation for drf-spectacular.

``ODATA_PARAMETERS`` is the single definition of the OData query parameters;
everything that documents them (viewset decorators, schema post-processing)
reads it from here.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

ODATA_PARAMETERS = [
    OpenApiParameter(
        name="$filter",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        required=False,
        description="""OData filter expression.

**Comparison operators:** `eq`, `ne`, `gt`, `ge`, `lt`, `le`
**Logical operators:** `and`, `or`, `not`
**String functions:** `contains()`, `startswith()`, `endswith()`, `tolower()`, `toupper()`

**Examples:**
- `status eq 'published'`
- `rating gt 4.0 and status eq 'published'`
- `contains(title, 'Django')`
- `author/name eq 'John'`
- `categories/any(c: c/id eq 1)`""",
    ),
    OpenApiParameter(
        name="$select",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        required=False,
        description="""Comma-separated list of fields to return.

Only selected fields are fetched from the database, improving performance.

**Examples:**
- `id,title,status`
- `id,title,author`""",
    ),
    OpenApiParameter(
        name="$expand",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        required=False,
        description="""Comma-separated list of relations to expand (eager load).

**Examples:**
- `author`
- `author,categories`
- `author($select=id,name)` - with nested $select""",
    ),
    OpenApiParameter(
        name="$orderby",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        required=False,
        description="""Comma-separated list of fields to sort by.

Use `asc` (default) or `desc` after field name.

**Examples:**
- `created_at desc`
- `title asc`
- `featured desc,created_at desc`""",
    ),
    OpenApiParameter(
        name="$top",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        required=False,
        description="""Maximum number of results to return (limit).

**Examples:**
- `10` - Return first 10 results
- Use with `$skip` for pagination""",
    ),
    OpenApiParameter(
        name="$skip",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        required=False,
        description="""Number of results to skip (offset).

**Pagination:**
- Page 1: `$top=10&$skip=0`
- Page 2: `$top=10&$skip=10`
- Page 3: `$top=10&$skip=20`""",
    ),
    OpenApiParameter(
        name="$count",
        type=OpenApiTypes.BOOL,
        location=OpenApiParameter.QUERY,
        required=False,
        description="""Include total count in response.

When `true`, response includes `@odata.count` with total results.""",
    ),
]


# Parameters for retrieve (only $select and $expand make sense)
ODATA_RETRIEVE_PARAMETERS = [p for p in ODATA_PARAMETERS if p.name in ("$select", "$expand")]

_SCHEMA_TYPES = {OpenApiTypes.STR: "string", OpenApiTypes.INT: "integer", OpenApiTypes.BOOL: "boolean"}


def postprocess_odata_schema(result, generator, request, public):
    """
    Post-processing hook to add OData parameters to schema.

    Add to settings:
        SPECTACULAR_SETTINGS = {
            'POSTPROCESSING_HOOKS': ['fc_selector.django.drf.spectacular.postprocess_odata_schema'],
        }
    """
    for path, methods in result.get("paths", {}).items():
        for method, operation in methods.items():
            if method.lower() != "get":
                continue

            operation.setdefault("parameters", [])
            existing_param_names = {p.get("name") for p in operation["parameters"]}

            # Detail endpoints only get the parameters that make sense for them
            is_list = "_list" in operation.get("operationId", "") or not path.rstrip("/").endswith("}")
            params_to_add = ODATA_PARAMETERS if is_list else ODATA_RETRIEVE_PARAMETERS

            for param in params_to_add:
                if param.name not in existing_param_names:
                    operation["parameters"].append(
                        {
                            "name": param.name,
                            "in": "query",
                            "required": param.required,
                            "description": param.description,
                            "schema": {"type": _SCHEMA_TYPES.get(param.type, "string")},
                        }
                    )

    return result
