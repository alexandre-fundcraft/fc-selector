"""
Protocol-agnostic query intent models.

This module defines the QueryIntent data structures that represent
queries in a protocol-independent way. These models serve as the
canonical internal representation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Sequence, cast

if TYPE_CHECKING:
    from fc_selector.core.ast.nodes import Node


@dataclass
class FilterIntent:
    """
    Protocol-agnostic filter representation.

    Attributes:
        expression: Raw filter expression string (informational)
        ast: Pre-built AST node (required for execution)
    """

    expression: str | None = None
    ast: Node | None = None

    def has_filter(self) -> bool:
        """Check if any filter is defined (must have AST)."""
        return self.ast is not None


@dataclass
class SelectIntent:
    """
    Fields to include in the result.

    Attributes:
        fields: List of field names to select
    """

    fields: list[str] = field(default_factory=list)

    def has_fields(self) -> bool:
        """Check if any fields are selected."""
        return len(self.fields) > 0


@dataclass
class ExpandIntent:
    """
    Related entities to include (eager loading).

    Attributes:
        relations: Dict mapping relation name to nested QueryIntent
    """

    relations: dict[str, QueryIntent] = field(default_factory=dict)

    def has_relations(self) -> bool:
        """Check if any relations are expanded."""
        return len(self.relations) > 0


@dataclass
class OrderField:
    """
    Single field ordering specification.
    """

    field: str
    direction: Literal["asc", "desc"] = "asc"


@dataclass
class OrderIntent:
    """
    Sorting specification.
    """

    fields: list[OrderField] = field(default_factory=list)

    def has_ordering(self) -> bool:
        """Check if any ordering is specified."""
        return len(self.fields) > 0

    @classmethod
    def from_tuples(cls, tuples: Sequence[tuple[str, str]]) -> OrderIntent:
        """
        Create from list of (field, direction) tuples.
        """
        fields = [
            OrderField(field=f, direction=cast(Literal["asc", "desc"], d if d in ("asc", "desc") else "asc"))
            for f, d in tuples
        ]
        return cls(fields=fields)


@dataclass
class PaginationIntent:
    """
    Pagination specification.
    """

    limit: int | None = None
    offset: int | None = None
    include_count: bool = False

    def has_pagination(self) -> bool:
        """Check if any pagination is specified."""
        return self.limit is not None or self.offset is not None


@dataclass
class QueryIntent:
    """
    Protocol-agnostic query representation.

    Attributes:
        filter: Filter conditions
        select: Fields to include
        expand: Related entities to eager load
        orderby: Sorting specification
        pagination: Pagination parameters
    """

    filter: FilterIntent | None = None
    select: SelectIntent | None = None
    expand: ExpandIntent | None = None
    orderby: OrderIntent | None = None
    pagination: PaginationIntent | None = None
