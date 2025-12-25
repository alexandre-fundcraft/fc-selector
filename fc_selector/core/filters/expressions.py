"""
Expression wrapper for AST nodes with Python operator support.

This module provides the Expression class that wraps AST nodes and enables
Python operator overloading for composing filter expressions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fc_selector.core.ast.nodes import And, BoolOp, Not, Or, UnaryOp

if TYPE_CHECKING:
    from fc_selector.core.ast.nodes import Node


class Expression:
    """
    Wrapper for AST nodes that enables Python operator overloading.

    Expression objects can be combined using Python operators:
    - & for AND
    - | for OR
    - ~ for NOT

    Example:
        >>> expr1 = Field("name").eq("John")
        >>> expr2 = Field("age").gt(18)
        >>> combined = expr1 & expr2  # AND
        >>> negated = ~expr1  # NOT
    """

    def __init__(self, node: Node):
        """
        Initialize expression with an AST node.

        Args:
            node: AST node to wrap
        """
        self._node = node

    def to_ast(self) -> Node:
        """
        Return the underlying AST node.

        Returns:
            The wrapped AST node
        """
        return self._node

    def __and__(self, other: Expression) -> Expression:
        """
        Combine with AND: expr1 & expr2

        Args:
            other: Expression to AND with

        Returns:
            New Expression representing (self AND other)
        """
        return Expression(BoolOp(op=And(), left=self._node, right=other._node))

    def __or__(self, other: Expression) -> Expression:
        """
        Combine with OR: expr1 | expr2

        Args:
            other: Expression to OR with

        Returns:
            New Expression representing (self OR other)
        """
        return Expression(BoolOp(op=Or(), left=self._node, right=other._node))

    def __invert__(self) -> Expression:
        """
        Negate: ~expr

        Returns:
            New Expression representing (NOT self)
        """
        return Expression(UnaryOp(op=Not(), operand=self._node))

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Expression({self._node!r})"

    def __eq__(self, other: object) -> bool:
        """Check equality based on AST node."""
        if isinstance(other, Expression):
            return self._node == other._node
        return False

    def __hash__(self) -> int:
        """Hash based on AST node."""
        return hash(self._node)
