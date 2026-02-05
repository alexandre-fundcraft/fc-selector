"""
Data models for OData query options.

Defines dataclasses for representing OData query parameters in a structured way.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueryOption:
    """Base class for OData query options."""

    value: Any
    name: str = ""

    @staticmethod
    def validate() -> bool:
        """Validate the query option."""
        raise NotImplementedError


@dataclass
class FilterOption(QueryOption):
    """Represents $filter query option."""

    name: str = "$filter"
    ast: Any | None = None  # Parsed AST tree from filter parser

    def validate(self) -> bool:
        """Validate filter option."""
        return isinstance(self.value, str) and len(self.value) > 0


@dataclass
class SelectOption(QueryOption):
    """Represents $select query option."""

    name: str = "$select"
    fields: list[str] = field(default_factory=list)

    def validate(self) -> bool:
        """Validate select option."""
        return isinstance(self.value, (str, list))


@dataclass
class ExpandOption(QueryOption):
    """Represents $expand query option."""

    name: str = "$expand"
    nested_options: dict[str, dict[str, Any]] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validate expand option."""
        return isinstance(self.value, (str, dict))


@dataclass
class OrderByOption(QueryOption):
    """Represents $orderby query option."""

    name: str = "$orderby"
    fields: list[tuple] = field(default_factory=list)

    def validate(self) -> bool:
        """Validate orderby option."""
        return isinstance(self.value, str)


@dataclass
class PaginationOption(QueryOption):
    """Base class for pagination options."""

    def validate(self) -> bool:
        """Validate pagination option."""
        try:
            int(self.value)
            return int(self.value) >= 0
        except (ValueError, TypeError):
            return False


@dataclass
class TopOption(PaginationOption):
    """Represents $top query option."""

    name: str = "$top"


@dataclass
class SkipOption(PaginationOption):
    """Represents $skip query option."""

    name: str = "$skip"


@dataclass
class ODataQuery:
    """Represents a complete OData query."""

    filter: FilterOption | None = None
    select: SelectOption | None = None
    expand: ExpandOption | None = None
    orderby: OrderByOption | None = None
    top: TopOption | None = None
    skip: SkipOption | None = None
    count: bool | None = None

    def validate(self) -> bool:
        """Validate all query options."""
        options = [
            self.filter,
            self.select,
            self.expand,
            self.orderby,
            self.top,
            self.skip,
        ]
        return all(opt is None or opt.validate() for opt in options)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result = {}
        if self.filter:
            result["$filter"] = self.filter.value
        if self.select:
            result["$select"] = self.select.value
        if self.expand:
            result["$expand"] = self.expand.value
        if self.orderby:
            result["$orderby"] = self.orderby.value
        if self.top:
            result["$top"] = self.top.value
        if self.skip:
            result["$skip"] = self.skip.value
        if self.count is not None:
            result["$count"] = self.count
        return result
