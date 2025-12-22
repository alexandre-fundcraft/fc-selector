"""
DRF Spectacular extensions for OData parameter documentation.

This module provides automatic OpenAPI documentation for OData query parameters.
"""

try:
    from drf_spectacular.extensions import OpenApiViewExtension
    from drf_spectacular.types import OpenApiTypes
    from drf_spectacular.utils import OpenApiParameter

    HAS_SPECTACULAR = True
except ImportError:
    HAS_SPECTACULAR = False


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
ODATA_RETRIEVE_PARAMETERS = [
    p for p in ODATA_PARAMETERS if p.name in ("$select", "$expand")
]


if HAS_SPECTACULAR:

    class ODataSelectorViewExtension(OpenApiViewExtension):
        """
        Automatically add OData parameters to ViewSets using ODataSelectorViewSetMixin.
        """

        target_class = "fc_selector.django.drf.viewsets.selector_mixin.ODataSelectorViewSetMixin"

        def view_replacement(self):
            """Return the original view class - we just want to add parameters."""
            return self.target

    def get_odata_schema_extension():
        """
        Get a schema extension callback for drf-spectacular.

        Add to settings:
            SPECTACULAR_SETTINGS = {
                'PREPROCESSING_HOOKS': ['fc_selector.django.drf.spectacular.preprocess_odata_parameters'],
            }
        """
        return preprocess_odata_parameters

    def preprocess_odata_parameters(endpoints):
        """
        Preprocessing hook to add OData parameters to endpoints.

        This hook adds OData query parameters to any endpoint that uses
        ODataSelectorViewSetMixin.
        """
        from fc_selector.django.drf.viewsets.selector_mixin import (
            ODataSelectorViewSetMixin,
        )

        for path, path_regex, method, callback in endpoints:
            view_class = getattr(callback, "cls", None)
            if view_class and issubclass(view_class, ODataSelectorViewSetMixin):
                # Mark this view for OData parameter injection
                if not hasattr(callback, "_odata_params_added"):
                    callback._odata_params_added = True

        return endpoints

    def postprocess_odata_schema(result, generator, request, public):
        """
        Post-processing hook to add OData parameters to schema.

        Add to settings:
            SPECTACULAR_SETTINGS = {
                'POSTPROCESSING_HOOKS': ['fc_selector.django.drf.spectacular.postprocess_odata_schema'],
            }
        """

        paths = result.get("paths", {})

        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.lower() != "get":
                    continue

                # Check if this is an OData endpoint by looking at tags or operationId
                operation_id = operation.get("operationId", "")
                tags = operation.get("tags", [])

                # Add parameters if not already present
                if "parameters" not in operation:
                    operation["parameters"] = []

                existing_param_names = {p.get("name") for p in operation["parameters"]}

                # Determine which parameters to add based on operation type
                is_list = "_list" in operation_id or not path.endswith("}")
                params_to_add = ODATA_PARAMETERS if is_list else ODATA_RETRIEVE_PARAMETERS

                for param in params_to_add:
                    if param.name not in existing_param_names:
                        operation["parameters"].append({
                            "name": param.name,
                            "in": "query",
                            "required": param.required,
                            "description": param.description,
                            "schema": {"type": "string" if param.type == OpenApiTypes.STR else "integer" if param.type == OpenApiTypes.INT else "boolean"},
                        })

        return result


def get_odata_parameters():
    """Get list of OData OpenApiParameter objects."""
    if not HAS_SPECTACULAR:
        return []
    return ODATA_PARAMETERS


def get_odata_retrieve_parameters():
    """Get list of OData OpenApiParameter objects for retrieve."""
    if not HAS_SPECTACULAR:
        return []
    return ODATA_RETRIEVE_PARAMETERS
