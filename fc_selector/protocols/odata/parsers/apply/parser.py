"""OData $apply Parser.

Parses the $apply query option which specifies collection transformations like
groupby, aggregate, and filter. This parser supports chained transformations
(e.g., "filter(...)/groupby(...)") and nested filter expressions."""

import re

from fc_selector.core import ast
from fc_selector.core.exceptions import QueryError
from fc_selector.protocols.odata.parsers.filter import parse_filter

_WITH_AS_SPLIT_PATTERN = re.compile(r"\s*with\s*|\s*as\s*")


def _split_on_top_level_char(s: str, splitter: str) -> list[str]:
    """Splits a string by `splitter` only when not inside parentheses."""
    parts: list[str] = []
    current_part = []
    paren_depth = 0
    for char in s:
        if char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1

        if char == splitter and paren_depth == 0:
            parts.append("".join(current_part).strip())
            current_part = []
        else:
            current_part.append(char)
    parts.append("".join(current_part).strip())
    return [p for p in parts if p]


def parse_apply(value: str) -> ast.Apply:
    """
    Parse OData $apply parameter.

    Args:
        value: The $apply value string (e.g., "filter(status eq 'published')/groupby((domain), aggregate($count as n))")

    Returns:
        An Apply AST node representing the parsed transformations.

    Raises:
        QueryError: If the $apply expression is empty or contains unknown syntax.
    """
    if not value or not value.strip():
        raise QueryError("empty $apply expression")

    transformations: list[ast.ApplyTransformation] = []

    # Split by '/' at top level (outside parentheses)
    segments = _split_on_top_level_char(value, "/")

    for segment in segments:
        segment_lower = segment.lower()
        if segment_lower.startswith("filter(") and segment_lower.endswith(")"):
            inner_expr = segment[len("filter(") : -1].strip()
            filter_ast = parse_filter(inner_expr)  # Reuse existing $filter parser
            transformations.append(ast.ApplyFilter(ast=filter_ast))
        elif segment_lower.startswith("groupby(") and segment_lower.endswith(")"):
            inner_expr = segment[len("groupby(") : -1].strip()
            fields_part, _, aggregate_part = inner_expr.partition(", aggregate(")

            if not fields_part.startswith("(") or not fields_part.endswith(")"):
                raise QueryError(f"Invalid groupby fields format: {fields_part}")

            fields = [f.strip() for f in fields_part[1:-1].split(",") if f.strip()]

            parsed_aggregates: list[ast.ApplyAggregateSpec] | None = None
            if aggregate_part:
                # Strip trailing ' )' from aggregate part (it was ', aggregate(' + rest + ')')
                if not aggregate_part.endswith(")"):
                    raise QueryError(f"Invalid aggregate format: {aggregate_part}")
                aggregate_inner = aggregate_part[:-1].strip()

                # Split by comma at top level within aggregate
                agg_items = _split_on_top_level_char(aggregate_inner, ",")

                parsed_aggregates = []
                for item in agg_items:
                    # Split "field with method as alias" into its 3 logical parts
                    with_parts = item.split(" with ", 1)
                    if len(with_parts) == 2:  # "field with method as alias"
                        source_method_part, as_part = with_parts
                        source_field = source_method_part.strip()

                        as_split = as_part.split(" as ", 1)
                        if len(as_split) == 2:  # "method as alias"
                            method, alias = as_split
                            method = method.strip()
                            alias = alias.strip()
                            parsed_aggregates.append(ast.ApplyAggregateSpec(source_field, method, alias))
                        else:
                            raise QueryError(f"Invalid aggregate item format: {item}")
                    elif item.lower().startswith("$count as "):  # "$count as total"
                        as_split = item.split(" as ", 1)
                        if len(as_split) == 2:
                            method = "count"
                            alias = as_split[1].strip()
                            source_field = None
                            parsed_aggregates.append(
                                ast.ApplyAggregateSpec(source_field=source_field, method=method, alias=alias)
                            )
                        else:
                            raise QueryError(f"Invalid aggregate item format: {item}")
                    else:
                        raise QueryError(f"Invalid aggregate item format: {item}")

            transformations.append(ast.ApplyGroupBy(fields=fields, aggregate=parsed_aggregates))

        elif segment_lower.startswith("aggregate(") and segment_lower.endswith(")"):
            # Handle bare aggregate transformation (no groupby clause)
            inner_expr = segment[len("aggregate(") : -1].strip()

            agg_items = _split_on_top_level_char(inner_expr, ",")
            parsed_aggregates = []
            for item in agg_items:
                # Split "field with method as alias" into its 3 logical parts
                with_parts = item.split(" with ", 1)
                if len(with_parts) == 2:  # "field with method as alias"
                    source_method_part, as_part = with_parts
                    source_field = source_method_part.strip()

                    as_split = as_part.split(" as ", 1)
                    if len(as_split) == 2:  # "method as alias"
                        method, alias = as_split
                        method = method.strip()
                        alias = alias.strip()
                        parsed_aggregates.append(ast.ApplyAggregateSpec(source_field, method, alias))
                    else:
                        raise QueryError(f"Invalid aggregate item format: {item}")
                elif item.lower().startswith("$count as "):  # "$count as total"
                    as_split = item.split(" as ", 1)
                    if len(as_split) == 2:
                        method = "count"
                        alias = as_split[1].strip()
                        source_field = None
                        parsed_aggregates.append(
                            ast.ApplyAggregateSpec(source_field=source_field, method=method, alias=alias)
                        )
                    else:
                        raise QueryError(f"Invalid aggregate item format: {item}")
                else:
                    raise QueryError(f"Invalid aggregate item format: {item}")
            transformations.append(ast.ApplyGroupBy(fields=[], aggregate=parsed_aggregates))

        else:
            raise QueryError(f"Unknown $apply segment: {segment}")

    return ast.Apply(transformations=transformations)
