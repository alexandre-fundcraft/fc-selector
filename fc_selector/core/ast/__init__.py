"""
Abstract Syntax Tree (AST) for OData Query Language.

This package provides framework-agnostic AST node definitions and visitor
pattern implementation for parsing and transforming OData queries.

Original Code: https://github.com/gorilla-co/odata-query
License: MIT
Authors: Original odata-query authors
Modified by: Alexandre Busquets (django-odata)

Usage:
    from fc_selector.core.ast import nodes, visitor

    # Create AST nodes
    ast_node = nodes.Compare(
        comparator=nodes.Eq(),
        left=nodes.Identifier('name'),
        right=nodes.String("'John'")
    )

    # Implement visitor
    class MyVisitor(visitor.NodeVisitor):
        def visit_Identifier(self, node):
            return F(node.name)

    # Visit AST
    visitor_instance = MyVisitor()
    result = visitor_instance.visit(ast_node)
"""

from . import nodes, visitor
from .nodes import (
    GUID,
    Add,
    All,
    And,
    Any,
    Apply,
    ApplyAggregateSpec,
    ApplyFilter,
    ApplyGroupBy,
    ApplyTransformation,
    Attribute,
    BinOp,
    Boolean,
    BoolOp,
    Call,
    CollectionLambda,
    Compare,
    Date,
    DateTime,
    Div,
    Duration,
    Eq,
    Float,
    Gt,
    GtE,
    Identifier,
    In,
    Integer,
    Lambda,
    List,
    Lt,
    LtE,
    Mod,
    Mult,
    NamedParam,
    Node,
    Not,
    NotEq,
    Null,
    Or,
    String,
    Sub,
    Time,
    UnaryOp,
    USub,
    _BinOpToken,
    _BoolOpToken,
    _CollectionOperator,
    _Comparator,
    _Literal,
    _UnaryOpToken,
)
from .visitor import NodeTransformer, NodeVisitor, iter_dataclass_fields

__all__ = [
    "nodes",
    "visitor",
    "Node",
    "Identifier",
    "Attribute",
    "_Literal",
    "Null",
    "Integer",
    "Float",
    "Boolean",
    "String",
    "Date",
    "Time",
    "DateTime",
    "Duration",
    "GUID",
    "List",
    "_BinOpToken",
    "Add",
    "Sub",
    "Mult",
    "Div",
    "Mod",
    "BinOp",
    "_Comparator",
    "Eq",
    "NotEq",
    "Lt",
    "LtE",
    "Gt",
    "GtE",
    "In",
    "Compare",
    "_BoolOpToken",
    "And",
    "Or",
    "BoolOp",
    "_UnaryOpToken",
    "Not",
    "USub",
    "UnaryOp",
    "NamedParam",
    "Call",
    "_CollectionOperator",
    "Any",
    "All",
    "Lambda",
    "CollectionLambda",
    "Apply",  # New
    "ApplyAggregateSpec",  # New
    "ApplyFilter",  # New
    "ApplyGroupBy",  # New
    "ApplyTransformation",  # New
    "NodeVisitor",
    "NodeTransformer",
    "iter_dataclass_fields",
]
