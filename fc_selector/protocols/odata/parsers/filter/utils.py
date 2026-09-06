"""
Utility Functions for OData AST Manipulation.

This module provides helper functions for working with OData AST nodes.

Original Code: https://github.com/gorilla-co/odata-query
License: MIT
Authors: Original odata-query authors
Modified by: Alexandre Busquets (django-odata)

Modifications:
- Changed imports to use fc_selector.core modules
- Maintained MIT license and original credits
"""

from typing import cast

from fc_selector.core import ast

from .rewrite import IdentifierStripper


def expression_relative_to_identifier(identifier: ast.Identifier, expression: ast.Node) -> ast.Node:
    """
    Shorthand for the :class:`IdentifierStripper`.

    Args:
        identifier: Identifier to strip from ``expression``.
        expression: Expression to strip the ``identifier`` from.

    Returns:
        The ``expression`` relative to the ``identifier``.
    """
    stripper = IdentifierStripper(identifier)
    result = cast(ast.Node, stripper.visit(expression))
    return result
