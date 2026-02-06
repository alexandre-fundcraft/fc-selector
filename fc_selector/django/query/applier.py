"""
Django OData query applier.

Applies OData queries to Django QuerySets using the unified DjangoExecutor.
This module acts as a compatibility wrapper for the legacy dictionary-based API.
"""

import logging
from typing import Any

from django.db.models import QuerySet

from fc_selector.core import exceptions as core_ex
from fc_selector.django.executor import DjangoExecutor
from fc_selector.exceptions import (
    ODataFieldNotFoundError,
    ODataFilterError,
    ODataInvalidPaginationError,
    ODataInvalidValueError,
)
from fc_selector.protocols.odata.converters import odata_query_to_intent
from fc_selector.protocols.odata.parsers.query.parser import parse_odata_query

logger = logging.getLogger(__name__)


class QueryApplier:
    """
    Applies OData queries to Django QuerySets.
    Now wraps DjangoExecutor for unified execution.
    """

    def __init__(self):
        """Initialize query applier."""
        self.executor = DjangoExecutor()

    def apply(self, queryset: QuerySet, query_params: dict[str, Any] | str) -> QuerySet:
        """
        Apply OData query parameters to a Django QuerySet.

        Args:
            queryset: Django QuerySet to filter
            query_params: Dictionary or string containing OData query parameters

        Returns:
            Filtered QuerySet
        """
        if not query_params:
            return queryset

        try:
            # 1. Parse -> ODataQuery
            odata_query = parse_odata_query(query_params)

            # 2. Convert ODataQuery -> QueryIntent
            intent = odata_query_to_intent(odata_query)

            # Ensure AST is populated for filters (lazy parsing handling)
            if intent.filter and intent.filter.expression and not intent.filter.ast:
                from fc_selector.protocols.odata.parsers.filter import parse_filter

                intent.filter.ast = parse_filter(intent.filter.expression)

            # 3. Execute Intent -> QuerySet
            return self.executor.execute(queryset, intent)

        except core_ex.FieldNotFoundError as e:
            raise ODataFieldNotFoundError(
                field_name=e.field_name,
                model_name=e.model_name or queryset.model.__name__,
                original_exception=e,
            ) from e

        except core_ex.InvalidValueError as e:
            if e.context in ["$top", "$skip"]:
                raise ODataInvalidPaginationError(
                    parameter=e.context,
                    value=str(e.value),
                    original_exception=e,
                ) from e

            raise ODataInvalidValueError(
                value=str(e.value),
                expected_type=str(e.expected_type) if e.expected_type else "unknown",
                field=e.context or "unknown",
                original_exception=e,
            ) from e

        except core_ex.SelectorError as e:
            raise ODataFilterError(
                message=str(e),
                code="QueryError",
                target="$filter",
                original_exception=e,
            ) from e

        except (ValueError, TypeError, AttributeError, KeyError) as e:
            # Catch type conversion, attribute access, and dictionary key errors
            # that may occur during query parsing or execution
            logger.error("Error processing OData query parameters: %s", e)
            raise ODataFilterError(
                message=f"Error processing OData query: {str(e)}",
                code="InvalidQuery",
                target="$filter",
                original_exception=e,
            ) from e


# Singleton instance
_applier = QueryApplier()


def apply_odata_query_params(queryset: QuerySet, query_params: dict[str, Any] | str) -> QuerySet:
    """
    Apply OData query parameters to a Django QuerySet.
    """
    return _applier.apply(queryset, query_params)
