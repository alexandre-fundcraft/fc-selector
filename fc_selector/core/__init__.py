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


# Lazy re-exports for backward compatibility (avoids circular imports)
def __getattr__(name: str):
    """Provide backward-compatible imports from protocols layer."""
    if name == "parse_odata_query":
        from fc_selector.protocols.odata.parsers.query import parse_odata_query  # noqa: PLC0415

        return parse_odata_query
    if name == "ODataQueryParser":
        from fc_selector.protocols.odata.parsers.query import ODataQueryParser  # noqa: PLC0415

        return ODataQueryParser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
