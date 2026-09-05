"""
Core functionality - Framework-agnostic layer.

This package contains the protocol-agnostic core:
- ast: Abstract Syntax Tree nodes for filter expressions
- intent: Protocol-agnostic query representation (QueryIntent)
- filters: Type-safe fluent API (Field, Expand, OrderBy)
- QueryBuilder: Fluent query builder

For OData-specific parsing, use:
    from fc_selector.protocols.odata import parse_odata_query
"""

from .query_builder import QueryBuilder

__all__ = [
    "QueryBuilder",
]
