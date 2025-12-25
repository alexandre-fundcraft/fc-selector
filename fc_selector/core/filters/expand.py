"""
Fluent Expand builder for type-safe expand construction.

This module provides the Expand class for building OData $expand options
using a fluent, type-safe API.

Example:
    >>> from fc_selector.core.filters import Expand, Field
    >>>
    >>> # Simple expand
    >>> Expand("author")
    >>>
    >>> # Expand with nested select
    >>> Expand("author").select("id", "name", "email")
    >>>
    >>> # Expand with nested filter
    >>> Expand("comments").filter(Field("approved").eq(True))
    >>>
    >>> # Expand with multiple options
    >>> Expand("comments").select("id", "text").filter(Field("approved").eq(True)).top(5)
    >>>
    >>> # Nested expand
    >>> Expand("author").select("id", "name").expand(Expand("profile").select("avatar"))
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fc_selector.core.ast.nodes import Node
from fc_selector.core.filters.expressions import Expression
from fc_selector.core.filters.orderby import OrderBy
from fc_selector.core.intent import (
    ExpandIntent,
    FilterIntent,
    OrderIntent,
    PaginationIntent,
    QueryIntent,
    SelectIntent,
)

if TYPE_CHECKING:
    pass


class Expand:
    """
    Fluent builder for $expand options.

    Allows building expand expressions with nested options like $select,
    $filter, $top, $orderby, and nested $expand.

    Example:
        >>> # Expand with options
        >>> expand = Expand("author").select("id", "name").top(1)
        >>>
        >>> # Use in QueryBuilder
        >>> query = QueryBuilder().expand(
        ...     Expand("author").select("id", "name"),
        ...     Expand("comments").filter(Field("approved").eq(True)).top(10)
        ... )
    """

    def __init__(self, relation: str):
        """
        Initialize Expand for a relation.

        Args:
            relation: Name of the relation to expand (e.g., "author", "comments")
        """
        self._relation = relation
        self._select_fields: list[str] | None = None
        self._filter_expression: Expression | None = None
        self._filter_ast: Node | None = None
        self._top_value: int | None = None
        self._skip_value: int | None = None
        self._orderby_specs: list[tuple[str, str]] | None = None
        self._nested_expands: list[Expand] | None = None

    @property
    def relation(self) -> str:
        """Get the relation name."""
        return self._relation

    def select(self, *fields: str) -> Expand:
        """
        Add $select to the expand.

        Args:
            *fields: Field names to select from the expanded relation.
                    Can be individual arguments or a single comma-separated string.

        Returns:
            self for method chaining

        Example:
            >>> Expand("author").select("id", "name", "email")
            >>> Expand("author").select("id,name,email")  # Also works
        """
        if len(fields) == 1 and "," in fields[0]:
            self._select_fields = [f.strip() for f in fields[0].split(",")]
        else:
            self._select_fields = list(fields)
        return self

    def filter(self, expression: Expression) -> Expand:
        """
        Add $filter to the expand using a type-safe Expression.

        Args:
            expression: Filter expression built using Field()

        Returns:
            self for method chaining

        Example:
            >>> Expand("comments").filter(Field("approved").eq(True))
            >>> Expand("posts").filter(Field("status").eq("published") & Field("views").gt(100))
        """
        if not isinstance(expression, Expression):
            raise TypeError(
                f"filter() expects an Expression, got {type(expression).__name__}. "
                "Use Field('name').eq('value') to create expressions."
            )

        self._filter_expression = expression
        self._filter_ast = expression.to_ast()
        return self

    def top(self, count: int) -> Expand:
        """
        Add $top to the expand (limit results).

        Args:
            count: Maximum number of related records to return

        Returns:
            self for method chaining

        Example:
            >>> Expand("comments").top(5)
        """
        self._top_value = count
        return self

    def skip(self, count: int) -> Expand:
        """
        Add $skip to the expand (offset results).

        Args:
            count: Number of related records to skip

        Returns:
            self for method chaining

        Example:
            >>> Expand("comments").skip(10).top(5)
        """
        self._skip_value = count
        return self

    def orderby(self, *specs) -> Expand:
        """
        Add $orderby to the expand.

        Args:
            *specs: OrderBy objects or strings like "field asc", "field desc"

        Returns:
            self for method chaining

        Example:
            >>> Expand("comments").orderby(OrderBy("created_at").desc())
            >>> Expand("comments").orderby("created_at desc", "id asc")
        """
        order_tuples: list[tuple[str, str]] = []
        for spec in specs:
            if isinstance(spec, OrderBy):
                order_tuples.append((spec.field, str(spec.direction)))
            elif isinstance(spec, str):
                parts = spec.strip().split()
                field = parts[0]
                direction = parts[1].lower() if len(parts) > 1 else "asc"
                if direction not in ("asc", "desc"):
                    direction = "asc"
                order_tuples.append((field, direction))
            else:
                raise TypeError(f"orderby() expects OrderBy or string, got {type(spec).__name__}")

        self._orderby_specs = order_tuples
        return self

    def expand(self, *expands: Expand) -> Expand:
        """
        Add nested $expand to the expand.

        Args:
            *expands: Nested Expand objects

        Returns:
            self for method chaining

        Example:
            >>> Expand("author").expand(
            ...     Expand("profile").select("avatar", "bio")
            ... )
        """
        if self._nested_expands is None:
            self._nested_expands = []

        for exp in expands:
            if not isinstance(exp, Expand):
                raise TypeError(f"expand() expects Expand objects, got {type(exp).__name__}")
            self._nested_expands.append(exp)

        return self

    def to_intent(self) -> QueryIntent:
        """
        Convert this Expand to a QueryIntent for the nested query.

        Returns:
            QueryIntent representing the nested expand options
        """
        intent = QueryIntent()

        # Build nested filter
        if self._filter_ast is not None:
            intent.filter = FilterIntent(ast=self._filter_ast)

        # Build nested select
        if self._select_fields:
            intent.select = SelectIntent(fields=list(self._select_fields))

        # Build nested orderby
        if self._orderby_specs:
            intent.orderby = OrderIntent.from_tuples(self._orderby_specs)

        # Build nested pagination
        if self._top_value is not None or self._skip_value is not None:
            intent.pagination = PaginationIntent(
                limit=self._top_value,
                offset=self._skip_value,
            )

        # Build nested expand (recursive)
        if self._nested_expands:
            relations = {}
            for nested in self._nested_expands:
                relations[nested.relation] = nested.to_intent()
            intent.expand = ExpandIntent(relations=relations)

        return intent

    def __repr__(self) -> str:
        """Return detailed representation."""
        parts = [f"Expand('{self._relation}')"]
        if self._select_fields:
            parts.append(f".select({', '.join(repr(f) for f in self._select_fields)})")
        if self._filter_expression:
            parts.append(".filter(...)")
        if self._top_value is not None:
            parts.append(f".top({self._top_value})")
        if self._skip_value is not None:
            parts.append(f".skip({self._skip_value})")
        if self._orderby_specs:
            parts.append(".orderby(...)")
        if self._nested_expands:
            parts.append(".expand(...)")
        return "".join(parts)
