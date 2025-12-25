"""
Abstract Syntax Tree (AST) for OData Query Language.

This package provides framework-agnostic AST node definitions and visitor
pattern implementation for parsing and transforming OData queries.

Original Code: https://github.com/gorilla-co/odata-query
License: MIT
Authors: Original odata-query authors
Modified by: Alexandre Busquets (django-odata)

Usage:
    from django_odata.core.parsers.filter.ast import nodes, visitor

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
    # Functions
    NamedParam,
    # Base
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
    # Arithmetic
    _BinOpToken,
    # Boolean
    _BoolOpToken,
    # Collections
    _CollectionOperator,
    # Comparison
    _Comparator,
    # Literals
    _Literal,
    # Unary
    _UnaryOpToken,
)
from .visitor import NodeTransformer, NodeVisitor, iter_dataclass_fields

__all__ = [
    # Modules
    "nodes",
    "visitor",
    # Base
    "Node",
    "Identifier",
    "Attribute",
    # Literals
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
    # Arithmetic
    "_BinOpToken",
    "Add",
    "Sub",
    "Mult",
    "Div",
    "Mod",
    "BinOp",
    # Comparison
    "_Comparator",
    "Eq",
    "NotEq",
    "Lt",
    "LtE",
    "Gt",
    "GtE",
    "In",
    "Compare",
    # Boolean
    "_BoolOpToken",
    "And",
    "Or",
    "BoolOp",
    # Unary
    "_UnaryOpToken",
    "Not",
    "USub",
    "UnaryOp",
    # Functions
    "NamedParam",
    "Call",
    # Collections
    "_CollectionOperator",
    "Any",
    "All",
    "Lambda",
    "CollectionLambda",
    # Visitor
    "NodeVisitor",
    "NodeTransformer",
    "iter_dataclass_fields",
]
