"""
Fluent OrderBy builder for type-safe ordering construction.

This module provides the OrderBy class for building OData $orderby options
using a fluent, type-safe API.

Example:
    >>> from fc_selector.core.filters import OrderBy
    >>>
    >>> # Ascending (default)
    >>> OrderBy("created_at")
    >>> OrderBy("created_at").asc()
    >>>
    >>> # Descending
    >>> OrderBy("created_at").desc()
    >>>
    >>> # Use in QueryBuilder
    >>> query = QueryBuilder().orderby(
    ...     OrderBy("created_at").desc(),
    ...     OrderBy("name").asc()
    ... )
"""

from __future__ import annotations

from typing import Literal


class OrderBy:
    """
    Fluent builder for $orderby options.

    Allows building order expressions with explicit direction.

    Example:
        >>> # Order by created_at descending, then by name ascending
        >>> query = QueryBuilder().orderby(
        ...     OrderBy("created_at").desc(),
        ...     OrderBy("name").asc()
        ... )
    """

    def __init__(self, field: str, direction: Literal["asc", "desc"] = "asc"):
        """
        Initialize OrderBy for a field.

        Args:
            field: Field name to order by
            direction: Sort direction ("asc" or "desc"), defaults to "asc"
        """
        self._field = field
        self._direction: Literal["asc", "desc"] = direction

    @property
    def field(self) -> str:
        """Get the field name."""
        return self._field

    @property
    def direction(self) -> Literal["asc", "desc"]:
        """Get the sort direction."""
        return self._direction

    def asc(self) -> OrderBy:
        """
        Set sort direction to ascending.

        Returns:
            self for method chaining

        Example:
            >>> OrderBy("name").asc()
        """
        self._direction = "asc"
        return self

    def desc(self) -> OrderBy:
        """
        Set sort direction to descending.

        Returns:
            self for method chaining

        Example:
            >>> OrderBy("created_at").desc()
        """
        self._direction = "desc"
        return self

    def to_tuple(self) -> tuple[str, Literal["asc", "desc"]]:
        """
        Convert to tuple format (field, direction).

        Returns:
            Tuple of (field_name, direction)
        """
        return (self._field, self._direction)

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"OrderBy('{self._field}').{self._direction}()"

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if not isinstance(other, OrderBy):
            return NotImplemented
        return self._field == other._field and self._direction == other._direction

    def __hash__(self) -> int:
        """Return hash."""
        return hash((self._field, self._direction))
