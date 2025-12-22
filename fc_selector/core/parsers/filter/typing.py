"""
Type Checking for OData AST Nodes.

This module provides type checking utilities for OData AST nodes.

Original Code: https://github.com/gorilla-co/odata-query
License: MIT
Authors: Original odata-query authors
Modified by: Alexandre Busquets (django-odata)

Modifications:
- Changed imports to use django_odata.core modules
- Removed unused functions (infer_type, infer_return_type)
- Maintained MIT license and original credits
"""

import operator

from . import ast
from . import exceptions as ex


def typecheck(
    node: ast._Node, expected_type: type | tuple[type, ...], field_name: str
) -> None:
    """
    Checks that the node type matches the expected type(s).

    Args:
        node: The node to type check.
        expected_type: The allowed type(s) the node can have.
        field_name: The name of the field you're typechecking. Only used in the
            exception message.
    Raises:
        ArgumentTypeException: If node type doesn't match expected type(s).
    """
    actual_type = type(node)
    compare = operator.contains if isinstance(expected_type, tuple) else operator.eq
    if not compare(expected_type, actual_type):
        allowed = (
            [t.__name__ for t in expected_type]
            if isinstance(expected_type, tuple)
            else expected_type.__name__
        )
        raise ex.ArgumentTypeException(field_name, str(allowed), actual_type.__name__)
