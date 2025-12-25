"""
Visitor Pattern Implementation for AST Traversal and Transformation.

This module provides base classes for implementing visitors that walk and
transform Abstract Syntax Trees (ASTs). The visitor pattern allows framework-
specific implementations to transform AST nodes into their respective query
representations without coupling the AST to any specific framework.

Original Code: https://github.com/gorilla-co/odata-query
License: MIT
Authors: Original odata-query authors
Modified by: Alexandre Busquets (django-odata)

Modifications:
- Added comprehensive docstrings
- Maintained MIT license and original credits

Usage:
    # Simple visitor that walks the AST
    class MyVisitor(NodeVisitor):
        def visit_Identifier(self, node):
            print(f"Found identifier: {node.name}")
            return node.name

    # Transformer that modifies the AST
    class MyTransformer(NodeTransformer):
        def visit_String(self, node):
            # Convert all strings to uppercase
            return String(val=node.val.upper())
"""

from collections.abc import Iterator
from dataclasses import fields
from typing import Any

from . import nodes


def iter_dataclass_fields(node: nodes.Node) -> Iterator[tuple[str, Any]]:
    """
    Iterate over all fields of a dataclass node.

    This utility function loops over all fields of the given node, yielding
    the field's name and current value. Used internally by visitors to
    traverse AST nodes.

    Args:
        node: AST node to iterate over

    Yields:
        Tuples of (fieldname, value) for each field in the node

    Example:
        >>> node = Compare(comparator=Eq(), left=Identifier('name'), right=String("'John'"))
        >>> for field_name, field_value in iter_dataclass_fields(node):
        ...     print(f"{field_name}: {field_value}")
        comparator: Eq()
        left: Identifier(name='name', namespace=())
        right: String(val="'John'")
    """
    for field in fields(node):
        yield field.name, getattr(node, field.name)


class NodeVisitor:
    """
    Base class for visitors that walk the AST.

    This class is meant to be subclassed, with the subclass adding visitor
    methods. By default, visitor methods for nodes are named 'visit_' + class
    name of the node (e.g., visit_Identifier(self, node)).

    If no visitor method exists for a node, the generic_visit method is used
    instead, which recursively visits all child nodes.

    The visitor pattern allows you to perform operations on AST nodes without
    modifying the AST structure itself. This is useful for:
    - Type checking
    - Code generation
    - Query optimization
    - Transformation to framework-specific objects

    Example:
        >>> class PrintVisitor(NodeVisitor):
        ...     def visit_Identifier(self, node):
        ...         print(f"Identifier: {node.name}")
        ...         self.generic_visit(node)
        ...
        ...     def visit_Compare(self, node):
        ...         print(f"Comparison: {node.comparator.__class__.__name__}")
        ...         self.generic_visit(node)
        ...
        >>> visitor = PrintVisitor()
        >>> ast = Compare(comparator=Eq(), left=Identifier('name'), right=String("'John'"))
        >>> visitor.visit(ast)
        Comparison: Eq
        Identifier: name

    Django Example:
        >>> class AstToDjangoQVisitor(NodeVisitor):
        ...     def visit_Identifier(self, node):
        ...         return F(node.name)
        ...
        ...     def visit_Compare(self, node):
        ...         lhs = self.visit(node.left)
        ...         rhs = self.visit(node.right)
        ...         comparator = self.visit(node.comparator)
        ...         return comparator(lhs, rhs)
        ...
        ...     def visit_Eq(self, node):
        ...         return lookups.Exact
        ...
        >>> visitor = AstToDjangoQVisitor(MyModel)
        >>> q_filter = visitor.visit(ast)  # Returns Django Q object
    """

    def visit(self, node: nodes.Node) -> Any:
        """
        Visit a node by calling the appropriate visitor method.

        This method looks for an explicit node visiting method on self named
        'visit_' + node class name. If no such method exists, it calls
        generic_visit instead.

        Args:
            node: AST node to visit

        Returns:
            Whatever the called visitor method returned. The user is free to
            choose what the NodeVisitor should return.

        Example:
            >>> visitor = MyVisitor()
            >>> result = visitor.visit(Identifier('name'))
            # Calls visitor.visit_Identifier(Identifier('name'))
        """
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: nodes.Node):
        """
        Visit all fields on a node recursively.

        Called if no explicit visitor method exists for a node. This default
        implementation recursively visits all child nodes but doesn't return
        anything or modify the tree.

        Override this method if you want custom behavior for unhandled nodes.

        Args:
            node: AST node to visit

        Example:
            >>> class CountingVisitor(NodeVisitor):
            ...     def __init__(self):
            ...         self.count = 0
            ...
            ...     def generic_visit(self, node):
            ...         self.count += 1
            ...         super().generic_visit(node)
            ...
            >>> visitor = CountingVisitor()
            >>> visitor.visit(complex_ast)
            >>> print(f"Total nodes: {visitor.count}")
        """
        for _field, value in iter_dataclass_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, nodes.Node):
                        self.visit(item)
            elif isinstance(value, nodes.Node):
                self.visit(value)


class NodeTransformer(NodeVisitor):
    """
    A subclass of NodeVisitor that allows modification of the AST.

    The visitor methods should return instances of nodes.Node that replace
    the passed node. This allows you to:
    - Optimize the AST
    - Rewrite queries
    - Inject additional conditions
    - Normalize expressions

    Unlike NodeVisitor, NodeTransformer modifies the tree and returns a new
    (or modified) AST. All dataclass nodes are immutable (frozen=True), so
    transformations create new nodes rather than modifying existing ones.

    Example:
        >>> class OptimizeTransformer(NodeTransformer):
        ...     def visit_BoolOp(self, node):
        ...         # Visit children first
        ...         node = self.generic_visit(node)
        ...
        ...         # Optimize: (a and a) → a
        ...         if isinstance(node.op, And) and node.left == node.right:
        ...             return node.left
        ...
        ...         return node
        ...
        >>> transformer = OptimizeTransformer()
        >>> optimized_ast = transformer.visit(original_ast)

    Rewriting Example:
        >>> class AddDefaultFilter(NodeTransformer):
        ...     def visit_Compare(self, node):
        ...         # Visit children first
        ...         node = self.generic_visit(node)
        ...
        ...         # Wrap all comparisons with "and is_active eq true"
        ...         default_filter = Compare(
        ...             comparator=Eq(),
        ...             left=Identifier('is_active'),
        ...             right=Boolean('true')
        ...         )
        ...         return BoolOp(op=And(), left=node, right=default_filter)
        ...
        >>> transformer = AddDefaultFilter()
        >>> new_ast = transformer.visit(ast)
    """

    def generic_visit(self, node: nodes.Node) -> nodes.Node:
        """
        Visit all fields on a node and rebuild it with transformed children.

        This default implementation recursively visits and transforms all child
        nodes, then creates a new instance of the node with the transformed
        children.

        Since all AST nodes are immutable (frozen=True), we create new nodes
        rather than modifying existing ones.

        Args:
            node: AST node to transform

        Returns:
            New node instance with transformed children

        Example:
            >>> class UppercaseTransformer(NodeTransformer):
            ...     def visit_String(self, node):
            ...         return String(val=node.val.upper())
            ...
            >>> # This will uppercase all strings in the tree:
            >>> transformer = UppercaseTransformer()
            >>> new_ast = transformer.visit(ast)
        """
        new_kwargs = {}

        for field, value in iter_dataclass_fields(node):
            if isinstance(value, list):
                new_val = []
                for item in value:
                    if isinstance(item, nodes.Node):
                        new_val.append(self.visit(item))
                    else:
                        new_val.append(item)
            elif isinstance(value, nodes.Node):
                new_val = self.visit(value)
            else:
                new_val = value

            new_kwargs[field] = new_val

        return type(node)(**new_kwargs)
