"""Fluent query construction with one state slot per option.

Fluent operations use only core types. Historical OData string methods are
compatibility entry points: parsing and export live in protocols.odata.builder.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Self, cast

from fc_selector.core.ast.nodes import And, BoolOp, Node, Or
from fc_selector.core.filters import Expand, Expression, OrderBy
from fc_selector.core.intent import ExpandIntent, FilterIntent, OrderIntent, PaginationIntent, QueryIntent, SelectIntent


class QueryBuilder:
    """Build detached QueryIntents; text is parsed only when needed."""

    def __init__(self, query_string: str = "", filter_parser: Callable[[str], Node] | None = None):
        self._filter: str | Node | None = None
        self._select: list[str] | None = None
        self._expand: str | ExpandIntent | None = None
        self._orderby: str | OrderIntent | None = None
        self._top: int | None = None
        self._skip: int | None = None
        self._count: bool | None = None
        self._filter_parser = filter_parser
        if query_string and query_string.strip():
            from fc_selector.compat import populate_query_builder  # noqa: PLC0415

            populate_query_builder(self, query_string)

    def _parse_filter(self, text: str) -> Node:
        if self._filter_parser is not None:
            return self._filter_parser(text)
        from fc_selector.compat import parse_filter  # noqa: PLC0415

        return cast(Node, parse_filter(text))

    def filter(self, expression: str) -> Self:
        """Replace the filter with lazily parsed text (compatibility API)."""
        self._filter = expression
        return self

    def _combine(self, value: str | Node, *, conjunction: bool) -> Self:
        if self._filter is None or self._filter == "":
            self._filter = value
        elif isinstance(self._filter, str) and isinstance(value, str):
            operator = "and" if conjunction else "or"
            self._filter = f"({self._filter}) {operator} ({value})"
        else:
            left = self._parse_filter(self._filter) if isinstance(self._filter, str) else self._filter
            right = self._parse_filter(value) if isinstance(value, str) else value
            self._filter = BoolOp(op=And() if conjunction else Or(), left=left, right=right)
        return self

    def and_filter(self, expression: str) -> Self:
        return self._combine(expression, conjunction=True)

    def or_filter(self, expression: str) -> Self:
        return self._combine(expression, conjunction=False)

    @staticmethod
    def _expression_ast(expression: Expression, method: str) -> Node:
        if not isinstance(expression, Expression):
            raise TypeError(
                f"{method}() expects an Expression, got {type(expression).__name__}. "
                "Use Field('name').eq('value') to create expressions."
            )
        return deepcopy(expression.to_ast())

    def where(self, expression: Expression) -> Self:
        self._filter = self._expression_ast(expression, "where")
        return self

    def and_where(self, expression: Expression) -> Self:
        return self._combine(self._expression_ast(expression, "and_where"), conjunction=True)

    def or_where(self, expression: Expression) -> Self:
        return self._combine(self._expression_ast(expression, "or_where"), conjunction=False)

    def select(self, *fields: str) -> Self:
        self._select = [f.strip() for f in fields[0].split(",")] if len(fields) == 1 else list(fields)
        return self

    def expand(self, *relations: str | Expand) -> Self:
        if any(isinstance(r, Expand) for r in relations):
            if not all(isinstance(r, Expand) for r in relations):
                raise TypeError(
                    "expand() cannot mix Expand objects with strings. Use either all strings or all Expand objects."
                )
            self._expand = ExpandIntent(
                {r.relation: deepcopy(r.to_intent()) for r in relations if isinstance(r, Expand)}
            )
        else:
            self._expand = ",".join(str(r).strip() for r in relations)
        return self

    def orderby(self, *fields: str | OrderBy) -> Self:
        if any(isinstance(f, OrderBy) for f in fields):
            if not all(isinstance(f, OrderBy) for f in fields):
                raise TypeError(
                    "orderby() cannot mix OrderBy objects with strings. Use either all strings or all OrderBy objects."
                )
            self._orderby = OrderIntent.from_tuples([(f.field, f.direction) for f in fields if isinstance(f, OrderBy)])
        else:
            self._orderby = ",".join(str(f).strip() for f in fields)
        return self

    def top(self, count: int) -> Self:
        self._top = count
        return self

    def skip(self, count: int) -> Self:
        self._skip = count
        return self

    def count(self, include: bool = True) -> Self:
        self._count = include
        return self

    def build(self) -> QueryIntent:
        """Return a detached intent, including mutable containers inside AST nodes."""
        filter_intent = None
        if self._filter is not None and self._filter != "":
            text = self._filter if isinstance(self._filter, str) else None
            filter_intent = FilterIntent(
                expression=text, ast=self._parse_filter(self._filter) if isinstance(self._filter, str) else self._filter
            )
        expand = self._expand
        orderby = self._orderby
        if isinstance(expand, str) or isinstance(orderby, str):
            from fc_selector.compat import parse_builder_options  # noqa: PLC0415

            expand, orderby = parse_builder_options(expand, orderby)
        pagination = None
        if self._top is not None or self._skip is not None or self._count:
            pagination = PaginationIntent(self._top, self._skip, self._count or False)
        return deepcopy(
            QueryIntent(
                filter_intent, SelectIntent(self._select) if self._select else None, expand, orderby, pagination
            )
        )

    def to_dict(self) -> dict[str, str]:
        """Export textual options; fluent AST export is deliberately unsupported."""
        from fc_selector.compat import builder_to_params  # noqa: PLC0415

        return cast(dict[str, str], builder_to_params(self))

    def build_query_string(self) -> str:
        from fc_selector.compat import builder_to_query_string  # noqa: PLC0415

        return cast(str, builder_to_query_string(self))

    def __str__(self) -> str:
        return self.build_query_string()

    def __repr__(self) -> str:
        return f"QueryBuilder({self.build_query_string()!r})"
