"""
Framework-agnostic OData query parser.

Parses OData query strings and dictionaries into structured ODataQuery objects.
"""

from typing import Any

from ..expand import parse_expand
from ..orderby import parse_orderby
from ..select import parse_select
from .models import (
    ExpandOption,
    FilterOption,
    ODataQuery,
    OrderByOption,
    SelectOption,
    SkipOption,
    TopOption,
)


class ODataQueryParser:
    """Framework-agnostic OData query parser."""

    def __init__(self):
        """Initialize the parser."""
        self.query_options = {
            "$filter": self._parse_filter,
            "$select": self._parse_select,
            "$expand": self._parse_expand,
            "$orderby": self._parse_orderby,
            "$top": self._parse_top,
            "$skip": self._parse_skip,
            "$count": self._parse_count,
        }

    def parse(self, query_params: dict[str, Any]) -> ODataQuery:
        """
        Parse OData query parameters into ODataQuery object.

        Args:
            query_params: Dictionary of query parameters

        Returns:
            ODataQuery object
        """
        query = ODataQuery()

        # Handle None input
        if query_params is None:
            return query

        for param_name, parser_func in self.query_options.items():
            if param_name in query_params:
                parser_func(query, query_params[param_name])

        return query

    def parse_from_string(self, query_string: str) -> ODataQuery:
        """
        Parse OData query string into ODataQuery object.

        Args:
            query_string: Raw query string (e.g., "$filter=status eq 'published'&$expand=author")

        Returns:
            ODataQuery object
        """
        if not query_string or not query_string.strip():
            return ODataQuery()

        params = self._parse_query_string(query_string)
        return self.parse(params)

    def parse_query_string(self, query_string: str) -> ODataQuery:
        """
        Parse OData query string into ODataQuery object.

        Alias for parse_from_string() to match common API patterns.

        Args:
            query_string: Raw query string (e.g., "$top=10&$skip=20&$filter=name eq 'John'")

        Returns:
            ODataQuery object
        """
        return self.parse_from_string(query_string)

    def _parse_query_string(self, query_string: str) -> dict[str, str]:
        """Parse raw query string into parameter dictionary."""
        from urllib.parse import unquote_plus

        # Remove leading '?' if present
        if query_string.startswith("?"):
            query_string = query_string[1:]

        query_string = unquote_plus(query_string)

        params = {}
        for param_pair in query_string.split("&"):
            if "=" in param_pair:
                key, value = param_pair.split("=", 1)
                params[key.strip()] = value.strip()
        return params

    def _parse_filter(self, query: ODataQuery, value: str) -> None:
        """Parse $filter option."""
        from ..filter import parse_filter

        # Parse the filter expression into AST
        try:
            ast_tree = parse_filter(value)
        except Exception:
            # If parsing fails, store None for AST but keep the raw value
            ast_tree = None

        query.filter = FilterOption(value=value, ast=ast_tree)

    def _parse_select(self, query: ODataQuery, value: str) -> None:
        """Parse $select option."""
        fields = parse_select(value)
        query.select = SelectOption(value=value, fields=fields)

    def _parse_expand(self, query: ODataQuery, value: str) -> None:
        """Parse $expand option."""
        nested = parse_expand(value)
        query.expand = ExpandOption(value=value, nested_options=nested)

    def _parse_orderby(self, query: ODataQuery, value: str) -> None:
        """Parse $orderby option."""
        fields = parse_orderby(value)
        query.orderby = OrderByOption(value=value, fields=fields)

    def _parse_top(self, query: ODataQuery, value: str) -> None:
        """Parse $top option."""
        query.top = TopOption(value=value)

    def _parse_skip(self, query: ODataQuery, value: str) -> None:
        """Parse $skip option."""
        query.skip = SkipOption(value=value)

    def _parse_count(self, query: ODataQuery, value: str) -> None:
        """Parse $count option."""
        query.count = value.lower() == "true"


# Singleton instance for convenience
_parser = ODataQueryParser()


def parse_odata_query(query_params: dict[str, Any] | str) -> ODataQuery:
    """
    Parse OData query parameters into ODataQuery object.

    Args:
        query_params: Dictionary of query parameters or raw query string

    Returns:
        ODataQuery object
    """
    if isinstance(query_params, str):
        return _parser.parse_from_string(query_params)
    return _parser.parse(query_params)
