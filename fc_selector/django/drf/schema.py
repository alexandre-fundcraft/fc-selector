"""
OData schema generation for API documentation.

Provides automatic documentation of OData query parameters for ViewSets.
"""

from rest_framework.schemas.openapi import AutoSchema


class ODataAutoSchema(AutoSchema):
    """
    Custom AutoSchema that documents OData query parameters.

    This schema automatically adds documentation for all supported OData
    query parameters to any ViewSet that uses it.

    Usage:
        class MyViewSet(ODataModelViewSet):
            schema = ODataAutoSchema()
    """

    def get_operation(self, path, method):
        """Add OData parameters to the operation."""
        operation = super().get_operation(path, method)

        # Only add OData params to list/GET operations
        if method == 'GET' and not path.endswith('/{id}'):
            operation = self._add_odata_parameters(operation)

        return operation

    def _add_odata_parameters(self, operation):
        """Add OData query parameters to the operation."""
        if 'parameters' not in operation:
            operation['parameters'] = []

        odata_params = [
            {
                'name': '$filter',
                'in': 'query',
                'required': False,
                'description': (
                    'OData filter expression to filter results.\n\n'
                    '**Operators:**\n'
                    '- `eq` - Equal (e.g., `status eq \'published\'`)\n'
                    '- `ne` - Not equal (e.g., `status ne \'draft\'`)\n'
                    '- `gt` - Greater than (e.g., `age gt 18`)\n'
                    '- `ge` - Greater than or equal (e.g., `price ge 100`)\n'
                    '- `lt` - Less than (e.g., `age lt 65`)\n'
                    '- `le` - Less than or equal (e.g., `price le 1000`)\n'
                    '- `and` - Logical AND (e.g., `status eq \'published\' and age gt 18`)\n'
                    '- `or` - Logical OR (e.g., `status eq \'draft\' or status eq \'published\'`)\n'
                    '- `not` - Logical NOT (e.g., `not (status eq \'archived\')`)\n'
                    '- `contains` - String contains (e.g., `contains(title, \'OData\')`)\n'
                    '- `startswith` - String starts with (e.g., `startswith(name, \'John\')`)\n'
                    '- `endswith` - String ends with (e.g., `endswith(email, \'@example.com\')`)\n\n'
                    '**Examples:**\n'
                    '- `$filter=status eq \'published\'`\n'
                    '- `$filter=age gt 18 and status eq \'active\'`\n'
                    '- `$filter=contains(title, \'Django\')`'
                ),
                'schema': {
                    'type': 'string',
                },
                'examples': {
                    'simple': {
                        'value': 'status eq \'published\'',
                        'summary': 'Simple equality filter'
                    },
                    'complex': {
                        'value': 'age gt 18 and status eq \'active\'',
                        'summary': 'Complex filter with AND'
                    },
                    'contains': {
                        'value': 'contains(title, \'OData\')',
                        'summary': 'String contains filter'
                    }
                }
            },
            {
                'name': '$select',
                'in': 'query',
                'required': False,
                'description': (
                    'Comma-separated list of fields to include in the response.\n\n'
                    'Only the specified fields will be returned, reducing response size '
                    'and improving performance.\n\n'
                    '**Examples:**\n'
                    '- `$select=id,title` - Only return id and title fields\n'
                    '- `$select=id,name,email` - Return id, name, and email'
                ),
                'schema': {
                    'type': 'string',
                },
                'examples': {
                    'minimal': {
                        'value': 'id,title',
                        'summary': 'Minimal fields'
                    },
                    'extended': {
                        'value': 'id,title,author,created_at',
                        'summary': 'Extended field list'
                    }
                }
            },
            {
                'name': '$expand',
                'in': 'query',
                'required': False,
                'description': (
                    'Comma-separated list of related entities to include (eager loading).\n\n'
                    'Expands related entities inline to reduce the number of requests needed.\n\n'
                    '**Examples:**\n'
                    '- `$expand=author` - Include author details\n'
                    '- `$expand=author,category` - Include author and category\n'
                    '- `$expand=author($select=id,name)` - Expand with nested $select'
                ),
                'schema': {
                    'type': 'string',
                },
                'examples': {
                    'simple': {
                        'value': 'author',
                        'summary': 'Expand single relation'
                    },
                    'multiple': {
                        'value': 'author,category,tags',
                        'summary': 'Expand multiple relations'
                    },
                    'nested': {
                        'value': 'author($select=id,name)',
                        'summary': 'Expand with nested query'
                    }
                }
            },
            {
                'name': '$orderby',
                'in': 'query',
                'required': False,
                'description': (
                    'Comma-separated list of fields to sort by.\n\n'
                    'Use `asc` (ascending, default) or `desc` (descending) after the field name.\n\n'
                    '**Examples:**\n'
                    '- `$orderby=created_at desc` - Sort by created_at descending\n'
                    '- `$orderby=title asc` - Sort by title ascending\n'
                    '- `$orderby=status,created_at desc` - Sort by status, then created_at desc'
                ),
                'schema': {
                    'type': 'string',
                },
                'examples': {
                    'ascending': {
                        'value': 'title',
                        'summary': 'Sort ascending (default)'
                    },
                    'descending': {
                        'value': 'created_at desc',
                        'summary': 'Sort descending'
                    },
                    'multiple': {
                        'value': 'status,created_at desc',
                        'summary': 'Multiple sort fields'
                    }
                }
            },
            {
                'name': '$top',
                'in': 'query',
                'required': False,
                'description': (
                    'Maximum number of results to return (limit).\n\n'
                    'Use with `$skip` for pagination.\n\n'
                    '**Examples:**\n'
                    '- `$top=10` - Return first 10 results\n'
                    '- `$top=25&$skip=50` - Return 25 results starting from position 50'
                ),
                'schema': {
                    'type': 'integer',
                    'minimum': 0,
                },
                'example': 10
            },
            {
                'name': '$skip',
                'in': 'query',
                'required': False,
                'description': (
                    'Number of results to skip (offset).\n\n'
                    'Use with `$top` for pagination.\n\n'
                    '**Pagination formula:**\n'
                    '- Page 1: `$top=10&$skip=0`\n'
                    '- Page 2: `$top=10&$skip=10`\n'
                    '- Page 3: `$top=10&$skip=20`\n\n'
                    '**Examples:**\n'
                    '- `$skip=10` - Skip first 10 results\n'
                    '- `$skip=20&$top=10` - Get results 21-30'
                ),
                'schema': {
                    'type': 'integer',
                    'minimum': 0,
                },
                'example': 0
            },
            {
                'name': '$count',
                'in': 'query',
                'required': False,
                'description': (
                    'Include total count of results in the response.\n\n'
                    'When set to `true`, the response will include `@odata.count` '
                    'with the total number of results (before pagination).\n\n'
                    '**Examples:**\n'
                    '- `$count=true` - Include total count\n'
                    '- `$count=false` - Don\'t include count (default)'
                ),
                'schema': {
                    'type': 'boolean',
                },
                'example': 'true'
            },
        ]

        operation['parameters'].extend(odata_params)
        return operation


def get_odata_parameters_description():
    """
    Get a formatted description of all OData parameters.

    Useful for adding to ViewSet docstrings.

    Returns:
        str: Formatted markdown description of OData parameters
    """
    return """
    ## OData Query Parameters

    This endpoint supports the following OData v4 query parameters:

    ### Filtering (`$filter`)
    Filter results using OData expressions.

    **Operators:** `eq`, `ne`, `gt`, `ge`, `lt`, `le`, `and`, `or`, `not`, `contains`, `startswith`, `endswith`

    **Examples:**
    - `?$filter=status eq 'published'` - Get published items
    - `?$filter=age gt 18 and status eq 'active'` - Complex filter
    - `?$filter=contains(title, 'OData')` - String contains

    ### Field Selection (`$select`)
    Select specific fields to return.

    **Examples:**
    - `?$select=id,title` - Return only id and title
    - `?$select=id,name,email` - Return id, name, and email

    ### Expansion (`$expand`)
    Eagerly load related entities.

    **Examples:**
    - `?$expand=author` - Include author details
    - `?$expand=author,category` - Expand multiple relations
    - `?$expand=author($select=id,name)` - Expand with nested query

    ### Ordering (`$orderby`)
    Sort results by one or more fields.

    **Examples:**
    - `?$orderby=created_at desc` - Sort by date descending
    - `?$orderby=status,created_at desc` - Multiple sort fields

    ### Pagination (`$top` and `$skip`)
    Paginate through results.

    **Examples:**
    - `?$top=10` - First 10 results
    - `?$top=10&$skip=10` - Results 11-20 (page 2)
    - `?$top=25&$skip=50` - Results 51-75 (page 3)

    ### Count (`$count`)
    Include total count of results.

    **Examples:**
    - `?$count=true` - Include @odata.count in response

    ### Combining Parameters
    All parameters can be combined for complex queries:

    ```
    ?$filter=status eq 'published'
     &$select=id,title,author
     &$expand=author
     &$orderby=created_at desc
     &$top=10
     &$skip=20
     &$count=true
    ```
    """
