"""
Protocol-agnostic query intent models.

This module defines the QueryIntent data structures that represent
queries in a protocol-independent way. These models serve as the
canonical internal representation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Sequence, cast

from fc_selector.core.ast.nodes import And, BoolOp

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

    def get_relation_names(self) -> list[str]:
        """Get list of relation names being expanded."""
        return list(self.relations.keys())


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

    def is_empty(self) -> bool:
        """Check if the query intent has no specifications."""
        return (
            (self.filter is None or not self.filter.has_filter())
            and (self.select is None or not self.select.has_fields())
            and (self.expand is None or not self.expand.has_relations())
            and (self.orderby is None or not self.orderby.has_ordering())
            and (self.pagination is None or not self.pagination.has_pagination())
        )

    def merge_with(self, other: QueryIntent) -> QueryIntent:
        """
        Merge another QueryIntent into this one.

        The other intent's values take precedence for simple fields.
        For filters, they are combined with AND.
        """
        merged_filter = None
        if self.filter and other.filter:
            # Combine filters with AND
            if self.filter.ast and other.filter.ast:
                merged_filter = FilterIntent(ast=BoolOp(op=And(), left=self.filter.ast, right=other.filter.ast))
            else:
                # Prioritize 'other' if it has AST, otherwise 'self'
                merged_filter = other.filter if other.filter.ast else self.filter
        else:
            merged_filter = other.filter if other.filter else self.filter

        return QueryIntent(
            filter=merged_filter,
            select=other.select if other.select else self.select,
            expand=other.expand if other.expand else self.expand,
            orderby=other.orderby if other.orderby else self.orderby,
            pagination=other.pagination if other.pagination else self.pagination,
        )
