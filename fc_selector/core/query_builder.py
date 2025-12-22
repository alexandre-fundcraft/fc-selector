"""
OData Query Builder - Fluent interface for building OData queries.

This module provides a builder class that allows constructing OData queries
using method chaining. It can be initialized with an existing query string
and allows incrementally adding query options.

Example:
    >>> query = ODataQueryBuilder("$filter=Price gt 100").select("Name,Price").top(10)
    >>> query.build_query_string()
    '$filter=Price gt 100&$select=Name,Price&$top=10'
"""

from urllib.parse import unquote_plus


class ODataQueryBuilder:
    """
    Fluent builder for OData queries.

    Allows constructing OData queries by chaining method calls. Each method
    returns self to enable fluent chaining.

    Example:
        >>> query = ODataQueryBuilder(request_query_string).and_filter(f"id eq {pk}")
        >>> dto = selector.get_one(query)
    """

    def __init__(self, query_string: str = ""):
        """
        Initialize the query builder, optionally parsing an existing query string.

        Args:
            query_string: OData query string (e.g., "$filter=Price gt 100&$select=Name")
        """
        self._filter: str | None = None
        self._select: list[str] | None = None
        self._expand: list[str] | None = None
        self._orderby: list[str] | None = None
        self._top: int | None = None
        self._skip: int | None = None
        self._count: bool | None = None

        if query_string and query_string.strip():
            self._parse_query_string(query_string)

    def _parse_query_string(self, query_string: str) -> None:
        """Parse an OData query string and populate internal state."""
        if query_string:
            # Handle encoded strings
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
    def from_query_string(cls, query_string: str) -> "ODataQueryBuilder":
        """
        Create an ODataQueryBuilder from an existing OData query string.

        Deprecated: Use ODataQueryBuilder(query_string) directly instead.

        Args:
            query_string: OData query string

        Returns:
            ODataQueryBuilder instance with parsed options
        """
        return cls(query_string)

    def filter(self, expression: str) -> "ODataQueryBuilder":
        """
        Add or replace the $filter option.

        Args:
            expression: OData filter expression (e.g., "Price gt 100")

        Returns:
            self for method chaining
        """
        self._filter = expression
        return self

    def and_filter(self, expression: str) -> "ODataQueryBuilder":
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

    def or_filter(self, expression: str) -> "ODataQueryBuilder":
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

    def select(self, *fields: str) -> "ODataQueryBuilder":
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

    def expand(self, *relations: str) -> "ODataQueryBuilder":
        """
        Set the $expand option.

        Args:
            *relations: Relation names to expand. Can be individual arguments
                       or a single comma-separated string.

        Returns:
            self for method chaining

        Examples:
            >>> query.expand("Author", "Category")
            >>> query.expand("Author,Category")
        """
        if len(relations) == 1 and "," in relations[0]:
            self._expand = [r.strip() for r in relations[0].split(",")]
        else:
            self._expand = list(relations)
        return self

    def orderby(self, *fields: str) -> "ODataQueryBuilder":
        """
        Set the $orderby option.

        Args:
            *fields: Field names with optional direction (asc/desc).
                    Can be individual arguments or a single comma-separated string.

        Returns:
            self for method chaining

        Examples:
            >>> query.orderby("Price desc", "Name asc")
            >>> query.orderby("Price desc,Name asc")
        """
        if len(fields) == 1 and "," in fields[0]:
            self._orderby = [f.strip() for f in fields[0].split(",")]
        else:
            self._orderby = list(fields)
        return self

    def top(self, count: int) -> "ODataQueryBuilder":
        """
        Set the $top option (limit).

        Args:
            count: Maximum number of records to return

        Returns:
            self for method chaining
        """
        self._top = count
        return self

    def skip(self, count: int) -> "ODataQueryBuilder":
        """
        Set the $skip option (offset).

        Args:
            count: Number of records to skip

        Returns:
            self for method chaining
        """
        self._skip = count
        return self

    def count(self, include: bool = True) -> "ODataQueryBuilder":
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

    def __str__(self) -> str:
        """Return the query string."""
        return self.build_query_string()

    def __repr__(self) -> str:
        """Return a detailed representation."""
        return f"ODataQueryBuilder({self.build_query_string()!r})"
