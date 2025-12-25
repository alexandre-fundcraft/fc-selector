"""
Field class for building type-safe filter expressions.

This module provides the Field class that allows building filter expressions
using a fluent, type-safe API instead of OData strings.

Example:
    >>> from fc_selector.core.filters import Field
    >>> Field("name").eq("John") & Field("age").gt(18)
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time
from typing import Any
from uuid import UUID

from fc_selector.core.ast import nodes as ast

from .expressions import Expression


def _to_literal(value: Any) -> ast._Literal:
    """
    Convert a Python value to an AST literal node.

    Args:
        value: Python value to convert

    Returns:
        Appropriate AST literal node
    """
    if value is None:
        return ast.Null()
    elif isinstance(value, bool):
        return ast.Boolean(val="true" if value else "false")
    elif isinstance(value, int):
        return ast.Integer(val=str(value))
    elif isinstance(value, float):
        return ast.Float(val=str(value))
    elif isinstance(value, str):
        # Don't add quotes - the Django visitor handles SQL quoting via Value()
        return ast.String(val=value)
    elif isinstance(value, date) and not isinstance(value, datetime):
        return ast.Date(val=value.isoformat())
    elif isinstance(value, datetime):
        return ast.DateTime(val=value.isoformat())
    elif isinstance(value, time):
        return ast.Time(val=value.isoformat())
    elif isinstance(value, UUID):
        return ast.GUID(val=str(value))
    else:
        # Fallback to string - don't add quotes, Django handles SQL quoting
        return ast.String(val=str(value))


def _to_literal_list(values: Sequence[Any]) -> ast.List:
    """
    Convert a Python sequence to an AST List node.

    Args:
        values: Sequence of Python values

    Returns:
        AST List node
    """
    return ast.List(val=[_to_literal(v) for v in values])


class Field:
    """
    Represents a field reference for building type-safe filter expressions.

    Field provides a fluent API for constructing filter expressions that
    are type-safe and IDE-friendly. The expressions build AST nodes directly,
    avoiding the need to parse string filters.

    Examples:
        # Simple equality
        >>> Field("name").eq("John")

        # Comparisons
        >>> Field("age").gt(18)
        >>> Field("price").between(10, 100)

        # String operations
        >>> Field("email").endswith("@example.com")

        # Null checks
        >>> Field("deleted_at").is_null()

        # In operator
        >>> Field("status").is_in(["active", "pending"])

        # Nested fields
        >>> Field("author.name").eq("John")
        >>> Field("author").name.eq("John")  # Alternative syntax

        # Composition
        >>> (Field("name").eq("John") & Field("age").gt(18)) | Field("vip").eq(True)
    """

    def __init__(self, name: str):
        """
        Initialize a field reference.

        Args:
            name: Field name. Can include dots for nested fields (e.g., "author.name")
        """
        self._name = name
        self._parts: list[str] = name.split(".") if "." in name else [name]

    def _build_identifier(self) -> ast.Node:
        """
        Build an AST identifier or attribute chain from field parts.

        For simple fields like "name", returns Identifier("name").
        For nested fields like "author.name", returns
        Attribute(Identifier("author"), "name").

        Returns:
            AST node representing the field reference
        """
        if len(self._parts) == 1:
            return ast.Identifier(name=self._parts[0])

        # Build nested Attribute chain: author.user.name
        # -> Attribute(Attribute(Identifier('author'), 'user'), 'name')
        result: ast.Node = ast.Identifier(name=self._parts[0])
        for part in self._parts[1:]:
            result = ast.Attribute(owner=result, attr=part)
        return result

    def __getattr__(self, name: str) -> Field:
        """
        Enable dot notation for nested fields.

        Example:
            >>> Field("author").name.eq("John")
            # Equivalent to Field("author.name").eq("John")

        Args:
            name: Attribute name

        Returns:
            New Field with appended attribute
        """
        if name.startswith("_"):
            raise AttributeError(name)
        return Field(f"{self._name}.{name}")

    # === Comparison Operators ===

    def eq(self, value: Any) -> Expression:
        """
        Equal to: field eq value

        Args:
            value: Value to compare against

        Returns:
            Expression representing field == value
        """
        return Expression(
            ast.Compare(
                comparator=ast.Eq(),
                left=self._build_identifier(),
                right=_to_literal(value),
            )
        )

    def ne(self, value: Any) -> Expression:
        """
        Not equal to: field ne value

        Args:
            value: Value to compare against

        Returns:
            Expression representing field != value
        """
        return Expression(
            ast.Compare(
                comparator=ast.NotEq(),
                left=self._build_identifier(),
                right=_to_literal(value),
            )
        )

    def gt(self, value: Any) -> Expression:
        """
        Greater than: field gt value

        Args:
            value: Value to compare against

        Returns:
            Expression representing field > value
        """
        return Expression(
            ast.Compare(
                comparator=ast.Gt(),
                left=self._build_identifier(),
                right=_to_literal(value),
            )
        )

    def ge(self, value: Any) -> Expression:
        """
        Greater than or equal: field ge value

        Args:
            value: Value to compare against

        Returns:
            Expression representing field >= value
        """
        return Expression(
            ast.Compare(
                comparator=ast.GtE(),
                left=self._build_identifier(),
                right=_to_literal(value),
            )
        )

    def lt(self, value: Any) -> Expression:
        """
        Less than: field lt value

        Args:
            value: Value to compare against

        Returns:
            Expression representing field < value
        """
        return Expression(
            ast.Compare(
                comparator=ast.Lt(),
                left=self._build_identifier(),
                right=_to_literal(value),
            )
        )

    def le(self, value: Any) -> Expression:
        """
        Less than or equal: field le value

        Args:
            value: Value to compare against

        Returns:
            Expression representing field <= value
        """
        return Expression(
            ast.Compare(
                comparator=ast.LtE(),
                left=self._build_identifier(),
                right=_to_literal(value),
            )
        )

    # === Null Checks ===

    def is_null(self) -> Expression:
        """
        Check if field is null: field eq null

        Returns:
            Expression representing field == null
        """
        return Expression(
            ast.Compare(
                comparator=ast.Eq(),
                left=self._build_identifier(),
                right=ast.Null(),
            )
        )

    def is_not_null(self) -> Expression:
        """
        Check if field is not null: field ne null

        Returns:
            Expression representing field != null
        """
        return Expression(
            ast.Compare(
                comparator=ast.NotEq(),
                left=self._build_identifier(),
                right=ast.Null(),
            )
        )

    # === In Operator ===

    def is_in(self, values: Sequence[Any]) -> Expression:
        """
        Check if field value is in list: field in [values]

        Args:
            values: Sequence of values to check against

        Returns:
            Expression representing field IN (values)
        """
        return Expression(
            ast.Compare(
                comparator=ast.In(),
                left=self._build_identifier(),
                right=_to_literal_list(values),
            )
        )

    def not_in(self, values: Sequence[Any]) -> Expression:
        """
        Check if field value is not in list: not (field in [values])

        Args:
            values: Sequence of values to check against

        Returns:
            Expression representing field NOT IN (values)
        """
        return ~self.is_in(values)

    # === String Functions ===

    def contains(self, substring: str) -> Expression:
        """
        String contains: contains(field, substring)

        Args:
            substring: Substring to search for

        Returns:
            Expression representing contains(field, substring)
        """
        return Expression(
            ast.Call(
                func=ast.Identifier(name="contains"),
                args=[self._build_identifier(), _to_literal(substring)],
            )
        )

    def startswith(self, prefix: str) -> Expression:
        """
        String starts with: startswith(field, prefix)

        Args:
            prefix: Prefix to match

        Returns:
            Expression representing startswith(field, prefix)
        """
        return Expression(
            ast.Call(
                func=ast.Identifier(name="startswith"),
                args=[self._build_identifier(), _to_literal(prefix)],
            )
        )

    def endswith(self, suffix: str) -> Expression:
        """
        String ends with: endswith(field, suffix)

        Args:
            suffix: Suffix to match

        Returns:
            Expression representing endswith(field, suffix)
        """
        return Expression(
            ast.Call(
                func=ast.Identifier(name="endswith"),
                args=[self._build_identifier(), _to_literal(suffix)],
            )
        )

    def matches(self, pattern: str) -> Expression:
        """
        Regex match: matchesPattern(field, pattern)

        Args:
            pattern: Regex pattern to match

        Returns:
            Expression representing matchesPattern(field, pattern)
        """
        return Expression(
            ast.Call(
                func=ast.Identifier(name="matchesPattern"),
                args=[self._build_identifier(), _to_literal(pattern)],
            )
        )

    # === Range Operations ===

    def between(self, low: Any, high: Any) -> Expression:
        """
        Check if field is between two values (inclusive).

        Equivalent to: field ge low and field le high

        Args:
            low: Lower bound (inclusive)
            high: Upper bound (inclusive)

        Returns:
            Expression representing low <= field <= high
        """
        return self.ge(low) & self.le(high)

    # === SQL-style Aliases ===

    equals = eq
    not_equals = ne
    greater_than = gt
    greater_than_or_equal = ge
    less_than = lt
    less_than_or_equal = le

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Field('{self._name}')"
