"""
AST Rewriter for OData Expressions.

This module provides the NodeTransformer used to make a filter expression
relative to an identifier (see ``utils.expression_relative_to_identifier``).

Original Code: https://github.com/gorilla-co/odata-query
License: MIT
Authors: Original odata-query authors
Modified by: Alexandre Busquets (django-odata)

Modifications:
- Changed imports to use fc_selector.core modules
- Maintained MIT license and original credits
"""

from fc_selector.core import ast
from fc_selector.core.ast import visitor


class IdentifierStripper(visitor.NodeTransformer):
    """
    A :class:`NodeTransformer` that strips the given identifier off of
    attributes. E.g. ``author/name`` -> ``name``.

    Args:
        strip: The identifier to strip off of all attributes in the :term:`AST`
    """

    def __init__(self, strip: ast.Identifier):
        self.strip = strip

    def visit_Attribute(self, node: ast.Attribute) -> ast.Node:
        """:meta private:"""
        if node.owner == self.strip:
            return ast.Identifier(node.attr)
        if isinstance(node.owner, ast.Attribute):
            return ast.Attribute(self.visit(node.owner), node.attr)

        return node
