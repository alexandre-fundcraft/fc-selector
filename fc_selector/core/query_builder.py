"""
Query Builder - Fluent interface for building queries.

This module provides a protocol-agnostic builder class that allows constructing
queries using method chaining. It can be initialized with an existing query string
and allows incrementally adding query options.

The builder supports two output modes:
1. build_query_string() - Returns OData query string (for OData endpoints)
2. build() - Returns QueryIntent (protocol-agnostic, recommended)

Example:
    >>> # Using QueryIntent (recommended)
    >>> intent = QueryBuilder().filter("status eq 'active'").top(10).build()
    >>> selector.execute(intent)

    >>> # Using OData string (legacy)
    >>> query = QueryBuilder("$filter=Price gt 100").select("Name,Price").top(10)
    >>> query.build_query_string()
    '$filter=Price gt 100&$select=Name,Price&$top=10'

"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from urllib.parse import unquote_plus

from fc_selector.core.ast.nodes import And, BoolOp, Or
from fc_selector.core.filters import Expand, Expression, OrderBy
from fc_selector.core.intent import (
    ExpandIntent,
    FilterIntent,
    OrderIntent,
    PaginationIntent,
    QueryIntent,
    SelectIntent,
)

if TYPE_CHECKING:
    from fc_selector.core.ast.nodes import Node


def _default_parse_filter(expression: str) -> "Node":
    """Default filter parser using OData protocol. Lazy import to avoid circular dependency."""
    from fc_selector.protocols.odata.parsers.filter import parse_filter  # noqa: PLC0415

    return parse_filter(expression)


class QueryBuilder:
    """
    Fluent builder for OData queries.

    Allows constructing OData queries by chaining method calls. Each method
    returns self to enable fluent chaining.

    Example:
        >>> query = QueryBuilder(request_query_string).and_filter(f"id eq {pk}")
        >>> dto = selector.get_one(query)
    """

    def __init__(
        self,
        query_string: str = "",
        filter_parser: Callable[[str], "Node"] | None = None,
    ):
        """
        Initialize the query builder, optionally parsing an existing query string.

        Args:
            query_string: OData query string (e.g., "$filter=Price gt 100&$select=Name")
            filter_parser: Optional callable to parse filter strings into AST nodes.
                          Defaults to OData filter parser. Allows dependency injection
                          for testing or alternative query languages.
        """
        self._filter: str | None = None
        self._filter_ast: Node | None = None  # Pre-built AST from fluent API
        self._select: list[str] | None = None
        self._expand: list[str] | None = None
        self._expand_objects: list[Expand] | None = None  # Type-safe Expand objects
        self._orderby: list[str] | None = None
        self._orderby_objects: list[OrderBy] | None = None  # Type-safe OrderBy objects
        self._top: int | None = None
        self._skip: int | None = None
        self._count: bool | None = None
        self._filter_parser = filter_parser or _default_parse_filter

        if query_string and query_string.strip():
            self._parse_query_string(query_string)

    def _parse_query_string(self, query_string: str) -> None:
        """Parse an OData query string and populate internal state."""
        if query_string:
            # Handle URL-encoded strings ('+' becomes space, %2B becomes '+')
            if "%" in query_string or "+" in query_string:
                query_string = unquote_plus(query_string)

        for param_pair in query_string.split("&"):
            if "=" not in param_pair:
                continue

            key, value = param_pair.split("=", 1)
            key = key.strip()
            value = value.strip()

            if key == "$filter":
                self._filter = value
            elif key == "$select":
                self._select = [f.strip() for f in value.split(",")]
            elif key == "$expand":
                self._expand = [e.strip() for e in value.split(",") if "(" not in e]
                # Keep original value for complex expands with options
                if "(" in value:
                    self._expand = [value]  # Store as-is for complex expand
            elif key == "$orderby":
                self._orderby = [f.strip() for f in value.split(",")]
            elif key == "$top":
                try:
                    self._top = int(value)
                except ValueError:
                    pass
            elif key == "$skip":
                try:
                    self._skip = int(value)
                except ValueError:
                    pass
            elif key == "$count":
                self._count = value.lower() == "true"

    @classmethod
    def from_query_string(cls, query_string: str) -> QueryBuilder:
        """
        Create a QueryBuilder from an existing OData query string.

        Deprecated: Use QueryBuilder(query_string) directly instead.

        Args:
            query_string: OData query string

        Returns:
            QueryBuilder instance with parsed options
        """
        return cls(query_string)

    def filter(self, expression: str) -> QueryBuilder:
        """
        Add or replace the $filter option.

        Args:
            expression: OData filter expression (e.g., "Price gt 100")

        Returns:
            self for method chaining
        """
        self._filter = expression
        return self

    def and_filter(self, expression: str) -> QueryBuilder:
        """
        Add an AND condition to the existing filter.

        Args:
            expression: OData filter expression to AND with existing filter

        Returns:
            self for method chaining
        """
        if self._filter:
            self._filter = f"({self._filter}) and ({expression})"
        else:
            self._filter = expression
        return self

    def or_filter(self, expression: str) -> QueryBuilder:
        """
        Add an OR condition to the existing filter.

        Args:
            expression: OData filter expression to OR with existing filter

        Returns:
            self for method chaining
        """
        if self._filter:
            self._filter = f"({self._filter}) or ({expression})"
        else:
            self._filter = expression
        return self

    def where(self, expression: Expression) -> QueryBuilder:
        """
        Set filter using a type-safe Expression.

        This is the preferred alternative to string-based .filter() method.
        Expressions are built using the Field class from fc_selector.core.filters.

        Args:
            expression: Filter expression built using Field()

        Returns:
            self for method chaining

        Example:
            >>> from fc_selector.core.filters import Field
            >>> query = QueryBuilder().where(
            ...     Field("name").eq("John") & Field("age").gt(18)
            ... )
        """

        if not isinstance(expression, Expression):
            raise TypeError(
                f"where() expects an Expression, got {type(expression).__name__}. "
                "Use Field('name').eq('value') to create expressions."
            )

        self._filter_ast = expression.to_ast()
        self._filter = None  # Clear string filter
        return self

    def and_where(self, expression: Expression) -> QueryBuilder:
        """
        Add an AND condition using a type-safe Expression.

        Can be combined with string-based .filter() - the expressions
        will be combined with AND.

        Args:
            expression: Filter expression to AND with existing filter

        Returns:
            self for method chaining

        Example:
            >>> query = QueryBuilder("$filter=status eq 'active'").and_where(
            ...     Field("age").gt(18)
            ... )
        """
        if not isinstance(expression, Expression):
            raise TypeError(
                f"and_where() expects an Expression, got {type(expression).__name__}. "
                "Use Field('name').eq('value') to create expressions."
            )

        new_ast = expression.to_ast()

        if self._filter_ast:
            # Combine with existing AST
            self._filter_ast = BoolOp(op=And(), left=self._filter_ast, right=new_ast)
        elif self._filter:
            # Parse existing string filter and combine
            existing_ast = self._filter_parser(self._filter)
            self._filter_ast = BoolOp(op=And(), left=existing_ast, right=new_ast)
            self._filter = None
        else:
            self._filter_ast = new_ast

        return self

    def or_where(self, expression: Expression) -> QueryBuilder:
        """
        Add an OR condition using a type-safe Expression.

        Can be combined with string-based .filter() - the expressions
        will be combined with OR.

        Args:
            expression: Filter expression to OR with existing filter

        Returns:
            self for method chaining

        Example:
            >>> query = QueryBuilder().where(
            ...     Field("role").eq("admin")
            ... ).or_where(
            ...     Field("role").eq("superuser")
            ... )
        """
        if not isinstance(expression, Expression):
            raise TypeError(
                f"or_where() expects an Expression, got {type(expression).__name__}. "
                "Use Field('name').eq('value') to create expressions."
            )

        new_ast = expression.to_ast()

        if self._filter_ast:
            # Combine with existing AST
            self._filter_ast = BoolOp(op=Or(), left=self._filter_ast, right=new_ast)
        elif self._filter:
            # Parse existing string filter and combine
            existing_ast = self._filter_parser(self._filter)
            self._filter_ast = BoolOp(op=Or(), left=existing_ast, right=new_ast)
            self._filter = None
        else:
            self._filter_ast = new_ast

        return self

    def select(self, *fields: str) -> QueryBuilder:
        """
        Set the $select option.

        Args:
            *fields: Field names to select. Can be individual arguments or
                    a single comma-separated string.

        Returns:
            self for method chaining

        Examples:
            >>> query.select("Name", "Price")
            >>> query.select("Name,Price")
        """
        if len(fields) == 1 and "," in fields[0]:
            self._select = [f.strip() for f in fields[0].split(",")]
        else:
            self._select = list(fields)
        return self

    def expand(self, *relations) -> QueryBuilder:
        """
        Set the $expand option.

        Args:
            *relations: Relation names (strings) or Expand objects.
                       Can be individual arguments or a single comma-separated string.

        Returns:
            self for method chaining

        Examples:
            >>> # String-based (legacy)
            >>> query.expand("Author", "Category")
            >>> query.expand("Author,Category")
            >>>
            >>> # Type-safe Expand objects
            >>> query.expand(
            ...     Expand("author").select("id", "name"),
            ...     Expand("comments").filter(Field("approved").eq(True)).top(5)
            ... )
        """
        # Check if any argument is an Expand object
        has_expand_objects = any(isinstance(r, Expand) for r in relations)

        if has_expand_objects:
            # All must be Expand objects
            expand_list = []
            for r in relations:
                if isinstance(r, Expand):
                    expand_list.append(r)
                else:
                    raise TypeError(
                        f"expand() cannot mix Expand objects with strings. Got {type(r).__name__}. "
                        "Use either all strings or all Expand objects."
                    )
            self._expand_objects = expand_list
            self._expand = None  # Clear string-based expand
        else:
            # String-based expand (legacy)
            if len(relations) == 1 and isinstance(relations[0], str) and "," in relations[0]:
                self._expand = [r.strip() for r in relations[0].split(",")]
            else:
                self._expand = [str(r) for r in relations]
            self._expand_objects = None  # Clear object-based expand

        return self

    def orderby(self, *fields) -> QueryBuilder:
        """
        Set the $orderby option.

        Args:
            *fields: Field names (strings) with optional direction (asc/desc),
                    or OrderBy objects for type-safe ordering.
                    Can be individual arguments or a single comma-separated string.

        Returns:
            self for method chaining

        Examples:
            >>> # String-based (legacy)
            >>> query.orderby("Price desc", "Name asc")
            >>> query.orderby("Price desc,Name asc")
            >>>
            >>> # Type-safe OrderBy objects
            >>> query.orderby(
            ...     OrderBy("created_at").desc(),
            ...     OrderBy("name").asc()
            ... )
        """
        # Check if any argument is an OrderBy object
        has_orderby_objects = any(isinstance(f, OrderBy) for f in fields)

        if has_orderby_objects:
            # All must be OrderBy objects
            orderby_list = []
            for f in fields:
                if isinstance(f, OrderBy):
                    orderby_list.append(f)
                else:
                    raise TypeError(
                        f"orderby() cannot mix OrderBy objects with strings. Got {type(f).__name__}. "
                        "Use either all strings or all OrderBy objects."
                    )
            self._orderby_objects = orderby_list
            self._orderby = None  # Clear string-based orderby
        else:
            # String-based orderby (legacy)
            if len(fields) == 1 and isinstance(fields[0], str) and "," in fields[0]:
                self._orderby = [f.strip() for f in fields[0].split(",")]
            else:
                self._orderby = [str(f) for f in fields]
            self._orderby_objects = None  # Clear object-based orderby

        return self

    def top(self, count: int) -> QueryBuilder:
        """
        Set the $top option (limit).

        Args:
            count: Maximum number of records to return

        Returns:
            self for method chaining
        """
        self._top = count
        return self

    def skip(self, count: int) -> QueryBuilder:
        """
        Set the $skip option (offset).

        Args:
            count: Number of records to skip

        Returns:
            self for method chaining
        """
        self._skip = count
        return self

    def count(self, include: bool = True) -> QueryBuilder:
        """
        Set the $count option.

        Args:
            include: Whether to include count in response

        Returns:
            self for method chaining
        """
        self._count = include
        return self

    def build_query_string(self) -> str:
        """
        Build the OData query string.

        Returns:
            Query string (e.g., "$filter=Price gt 100&$top=10")
        """
        params = []

        if self._filter:
            params.append(f"$filter={self._filter}")
        if self._select:
            params.append(f"$select={','.join(self._select)}")
        if self._expand:
            params.append(f"$expand={','.join(self._expand)}")
        if self._orderby:
            params.append(f"$orderby={','.join(self._orderby)}")
        if self._top is not None:
            params.append(f"$top={self._top}")
        if self._skip is not None:
            params.append(f"$skip={self._skip}")
        if self._count is not None:
            params.append(f"$count={'true' if self._count else 'false'}")

        return "&".join(params)

    def to_dict(self) -> dict:
        """
        Convert query options to a dictionary.

        Returns:
            Dictionary with OData query parameters
        """
        result = {}

        if self._filter:
            result["$filter"] = self._filter
        if self._select:
            result["$select"] = ",".join(self._select)
        if self._expand:
            result["$expand"] = ",".join(self._expand)
        if self._orderby:
            result["$orderby"] = ",".join(self._orderby)
        if self._top is not None:
            result["$top"] = str(self._top)
        if self._skip is not None:
            result["$skip"] = str(self._skip)
        if self._count is not None:
            result["$count"] = "true" if self._count else "false"

        return result

    def build(self) -> QueryIntent:
        """
        Build a QueryIntent from the current builder state.

        This is the recommended way to use the builder output with selectors.
        QueryIntent is protocol-agnostic and can be executed directly.

        Returns:
            QueryIntent instance representing this query

        Example:
            >>> query = QueryBuilder().filter("status eq 'active'").top(10)
            >>> intent = query.build()
            >>> results = selector.execute(intent)
        """
        intent = QueryIntent()

        intent.filter = self._build_filter_intent()
        intent.select = self._build_select_intent()
        intent.expand = self._build_expand_intent()
        intent.orderby = self._build_orderby_intent()
        intent.pagination = self._build_pagination_intent()

        return intent

    def _build_filter_intent(self) -> FilterIntent | None:
        """Build filter intent from current builder state."""
        if not (self._filter or self._filter_ast):
            return None

        ast_to_use = self._filter_ast
        if ast_to_use is None and self._filter:
            ast_to_use = self._filter_parser(self._filter)

        return FilterIntent(expression=self._filter, ast=ast_to_use)

    def _build_select_intent(self) -> SelectIntent | None:
        """Build select intent from current builder state."""
        if not self._select:
            return None

        return SelectIntent(fields=list(self._select))

    def _build_expand_intent(self) -> ExpandIntent | None:
        """Build expand intent from current builder state."""
        if self._expand_objects:
            return self._build_expand_from_objects()
        elif self._expand:
            return self._build_expand_from_strings()

        return None

    def _build_expand_from_objects(self) -> ExpandIntent:
        """Build expand intent from type-safe Expand objects."""
        relations = {}
        for expand_obj in self._expand_objects:
            relations[expand_obj.relation] = expand_obj.to_intent()
        return ExpandIntent(relations=relations)

    def _build_expand_from_strings(self) -> ExpandIntent:
        """Build expand intent from string-based expand (legacy)."""
        relations = {}
        for relation in self._expand:
            if "(" in relation:
                base_relation = relation.split("(")[0].strip()
                relations[base_relation] = QueryIntent()
            else:
                relations[relation] = QueryIntent()
        return ExpandIntent(relations=relations)

    def _build_orderby_intent(self) -> OrderIntent | None:
        """Build orderby intent from current builder state."""
        if self._orderby_objects:
            return self._build_orderby_from_objects()
        elif self._orderby:
            return self._build_orderby_from_strings()

        return None

    def _build_orderby_from_objects(self) -> OrderIntent:
        """Build orderby intent from type-safe OrderBy objects."""
        order_tuples: list[tuple[str, str]] = [(obj.field, obj.direction) for obj in self._orderby_objects]
        return OrderIntent.from_tuples(order_tuples)

    def _build_orderby_from_strings(self) -> OrderIntent:
        """Build orderby intent from string-based orderby (legacy)."""
        order_tuples: list[tuple[str, str]] = []
        for field_spec in self._orderby:
            parts = field_spec.strip().split()
            field_name = parts[0]
            direction = parts[1].lower() if len(parts) > 1 else "asc"
            if direction not in ("asc", "desc"):
                direction = "asc"
            order_tuples.append((field_name, direction))
        return OrderIntent.from_tuples(order_tuples)

    def _build_pagination_intent(self) -> PaginationIntent | None:
        """Build pagination intent from current builder state."""
        if self._top is None and self._skip is None and not self._count:
            return None

        return PaginationIntent(limit=self._top, offset=self._skip, include_count=self._count or False)

    def to_odata_string(self) -> str:
        """
        Serialize to OData query string format.

        This is an alias for build_query_string() with a more explicit name.

        Returns:
            OData query string (e.g., "$filter=Price gt 100&$top=10")
        """
        return self.build_query_string()

    def get_filter_ast(self) -> Node | None:
        """
        Get the filter as an AST node.

        If a string filter was set, it will be parsed. If an AST was set
        directly (via where()), it will be returned as-is.

        Returns:
            AST node representing the filter, or None if no filter
        """
        if self._filter_ast is not None:
            return self._filter_ast
        if self._filter:
            return self._filter_parser(self._filter)
        return None

    def __str__(self) -> str:
        """Return the query string."""
        return self.build_query_string()

    def __repr__(self) -> str:
        """Return a detailed representation."""
        return f"QueryBuilder({self.build_query_string()!r})"
