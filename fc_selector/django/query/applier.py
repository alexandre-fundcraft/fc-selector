"""
Django OData query applier.

Applies OData queries to Django QuerySets with optimization and error handling.
"""

import logging
from typing import Any

from django.db.models import QuerySet

from fc_selector.core.parsers.filter import parse_filter
from fc_selector.django.visitors import AstToDjangoQVisitor
from fc_selector.exceptions import (
    ODataFieldNotFoundError,
    ODataFilterError,
    ODataInvalidFilterSyntaxError,
    ODataInvalidOperatorError,
    ODataInvalidPaginationError,
)

logger = logging.getLogger(__name__)


class QueryApplier:
    """Applies OData queries to Django QuerySets."""

    def __init__(self):
        """Initialize query applier."""
        pass

    def apply(self, queryset: QuerySet, query_params: dict[str, Any]) -> QuerySet:
        """
        Apply OData query parameters to a Django QuerySet.

        Args:
            queryset: Django QuerySet to filter
            query_params: Dictionary containing OData query parameters

        Returns:
            Filtered QuerySet

        Raises:
            ODataFilterError: If the OData query is invalid
        """
        if not query_params:
            return queryset

        try:
            # Apply filtering using native parser and visitor
            if "$filter" in query_params:
                filter_ast = parse_filter(query_params["$filter"])
                visitor = AstToDjangoQVisitor(queryset.model)
                q_object = visitor.visit(filter_ast)
                queryset = queryset.filter(q_object)

            # Apply ordering
            if "$orderby" in query_params:
                queryset = self._apply_orderby(queryset, query_params)

            # Apply pagination
            if "$skip" in query_params:
                queryset = self._apply_skip(queryset, query_params)

            if "$top" in query_params:
                queryset = self._apply_top(queryset, query_params)

            return queryset

        except ODataInvalidPaginationError:
            # Re-raise pagination errors as-is, don't wrap them
            raise
        except ODataFilterError as e:
            # Convert parser exceptions to OData-specific errors
            filter_expr = query_params.get("$filter", "")
            if "field" in str(e).lower() and "not found" in str(e).lower():
                # Extract field name from error message if possible
                field_name = "unknown"
                if "field" in str(e):
                    try:
                        field_part = str(e).split("field")[1].split()[0].strip("'\"")
                        field_name = field_part
                    except (IndexError, AttributeError):
                        pass
                raise ODataFieldNotFoundError(
                    field_name=field_name,
                    model_name=queryset.model.__name__,
                    original_exception=e,
                ) from e
            elif "parsing" in str(e).lower() or "syntax" in str(e).lower():
                raise ODataInvalidFilterSyntaxError(
                    filter_expression=filter_expr, details=str(e), original_exception=e
                ) from e
            elif "operator" in str(e).lower():
                # Extract operator from filter expression
                operator = "unknown"
                if filter_expr:
                    # Simple heuristic to find operator
                    operators = [
                        " eq ",
                        " ne ",
                        " gt ",
                        " ge ",
                        " lt ",
                        " le ",
                        " and ",
                        " or ",
                        " not ",
                    ]
                    for op in operators:
                        if op in filter_expr:
                            operator = op.strip()
                            break
                raise ODataInvalidOperatorError(
                    operator=operator,
                    filter_expression=filter_expr,
                    original_exception=e,
                ) from e
            else:
                # Generic OData error
                raise ODataFilterError(
                    message=f"OData query error: {str(e)}",
                    code="QueryError",
                    target="$filter",
                    details={"filter_expression": filter_expr},
                    original_exception=e,
                ) from e
        except Exception as e:
            logger.error(f"Unexpected error applying OData query: {e}")
            filter_expr = query_params.get("$filter", "")
            raise ODataFilterError(
                message=f"Unexpected error processing OData query: {str(e)}",
                code="InternalError",
                target="$filter",
                details={"filter_expression": filter_expr},
                original_exception=e,
            ) from e

    @staticmethod
    def _apply_orderby(queryset: QuerySet, query_params: dict[str, Any]) -> QuerySet:
        """Apply $orderby parameter to queryset."""
        if "$orderby" not in query_params:
            return queryset

        order_fields = []
        for field in query_params["$orderby"].split(","):
            field = field.strip()
            if field.endswith(" desc"):
                order_fields.append("-" + field[:-5].strip())
            elif field.endswith(" asc"):
                order_fields.append(field[:-4].strip())
            else:
                order_fields.append(field)
        return queryset.order_by(*order_fields)

    @staticmethod
    def _apply_skip(queryset: QuerySet, query_params: dict[str, Any]) -> QuerySet:
        """Apply $skip parameter to queryset."""
        if "$skip" not in query_params:
            return queryset

        try:
            skip = int(query_params["$skip"])
            if skip < 0:
                raise ODataInvalidPaginationError(
                    parameter="$skip",
                    value=str(query_params["$skip"]),
                )
            if skip > 0:
                queryset = queryset[skip:]
        except (ValueError, TypeError) as e:
            raise ODataInvalidPaginationError(
                parameter="$skip",
                value=str(query_params["$skip"]),
                original_exception=e,
            ) from e
        return queryset

    @staticmethod
    def _apply_top(queryset: QuerySet, query_params: dict[str, Any]) -> QuerySet:
        """Apply $top parameter to queryset."""
        if "$top" not in query_params:
            return queryset

        try:
            top = int(query_params["$top"])
            if top < 0:
                raise ODataInvalidPaginationError(
                    parameter="$top",
                    value=str(query_params["$top"]),
                )
            if top >= 0:
                queryset = queryset[:top]
        except (ValueError, TypeError) as e:
            raise ODataInvalidPaginationError(
                parameter="$top",
                value=str(query_params["$top"]),
                original_exception=e,
            ) from e
        return queryset


# Singleton instance
_applier = QueryApplier()


def apply_odata_query_params(
    queryset: QuerySet, query_params: dict[str, Any]
) -> QuerySet:
    """
    Apply OData query parameters to a Django QuerySet.

    Args:
        queryset: Django QuerySet to filter
        query_params: Dictionary containing OData query parameters

    Returns:
        Filtered QuerySet

    Raises:
        ODataFilterError: If the OData query is invalid
    """
    return _applier.apply(queryset, query_params)
