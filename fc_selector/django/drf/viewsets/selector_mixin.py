"""
OData Selector ViewSet Mixin.

Provides OData support using the Selector + DTO pattern for hexagonal architecture.
"""

from rest_framework import status
from rest_framework.response import Response

from fc_selector.core import exceptions as core_ex
from fc_selector.exceptions import (
    ODataFieldNotFoundError,
    ODataFilterError,
    ODataInvalidPaginationError,
)
from fc_selector.protocols.odata.parsers.query import MAX_SKIP_VALUE, MAX_TOP_VALUE

DEFAULT_PAGE_SIZE = 50


def build_odata_response(request, serializer_data, query_string, entity_set_name, selector=None, total_count=None):
    """
    Build OData-compliant response with pagination links and optional count.

    Args:
        request: Django request object
        serializer_data: Serialized data to return
        query_string: OData query string
        entity_set_name: Name of the entity set (posts, authors, etc.)
        selector: Optional selector instance for count queries
        total_count: Optional pre-calculated total count (use when additional filters
                     are applied that aren't in the query_string, e.g., RLS filters)

    Returns:
        dict: OData response with @odata.context, value, @odata.count, @odata.nextLink
    """
    response_data = {
        "@odata.context": f"{request.build_absolute_uri('/odata/')}$metadata#{entity_set_name}",
        "value": serializer_data,
    }

    parsed_qs = {}
    for param in query_string.split("&"):
        if "=" in param:
            key, value = param.split("=", 1)
            parsed_qs[key] = value

    if parsed_qs.get("$count", "").lower() == "true":
        if total_count is not None:
            # Use pre-calculated count (when RLS or additional filters are applied)
            response_data["@odata.count"] = total_count
        elif selector:
            # Count should be independent of pagination
            count_query = "&".join([f"{k}={v}" for k, v in parsed_qs.items() if k not in ("$count", "$top", "$skip")])
            response_data["@odata.count"] = selector.query(count_query).count()

    # Pagination links, with the same bounds the query parser enforces
    try:
        top = min(int(parsed_qs.get("$top", DEFAULT_PAGE_SIZE)), MAX_TOP_VALUE)
        skip = min(int(parsed_qs.get("$skip", 0)), MAX_SKIP_VALUE)
    except (ValueError, TypeError):
        top, skip = DEFAULT_PAGE_SIZE, 0

    if top < 0:
        top = DEFAULT_PAGE_SIZE
    skip = max(skip, 0)

    # Exactly 'top' results means there may be more
    if len(serializer_data) == top:
        next_params = {**parsed_qs, "$skip": str(skip + top)}
        next_query = "&".join([f"{k}={v}" for k, v in next_params.items()])
        response_data["@odata.nextLink"] = f"{request.build_absolute_uri(request.path)}?{next_query}"

    return response_data


class ODataSelectorViewSetMixin:
    """
    Mixin to add OData support to ViewSets using the Selector + DTO pattern.

    This mixin follows hexagonal architecture principles:
    - Uses ODataSelector for data access (no QuerySet exposure)
    - Returns DTOs instead of Django model instances
    - Supports full OData query syntax

    Requires:
    - selector_class: The Selector class to use
    - odata_entity_set_name: Name of the entity set for OData metadata

    Example:
        class BlogPostViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
            selector_class = BlogPostSelector
            odata_entity_set_name = "posts"
            serializer_class = BlogPostDTOSerializer

            # list() and retrieve() are provided by the mixin
    """

    selector_class = None
    odata_entity_set_name = None

    def get_selector(self):
        """Get an instance of the selector class."""
        if self.selector_class is None:
            raise NotImplementedError(f"{self.__class__.__name__} must define 'selector_class'")
        if not callable(self.selector_class):
            raise TypeError(f"selector_class must be callable, got {type(self.selector_class)}")
        return self.selector_class()  # skipcq: PYL-E1102 - Verified callable above

    @staticmethod
    def _reraise_as_odata_error(exc):
        """Translate a core selector error into its OData API equivalent."""
        if isinstance(exc, core_ex.InvalidFieldError):
            raise ODataFieldNotFoundError(
                field_name=exc.field_name,
                model_name=exc.model_name,
                original_exception=exc,
            ) from exc
        if isinstance(exc, core_ex.InvalidValueError):
            raise ODataInvalidPaginationError(
                parameter=exc.context or "$top",
                value=str(exc.value),
                original_exception=exc,
            ) from exc
        raise ODataFilterError(message=str(exc), original_exception=exc) from exc

    def list(self, request, *args, **kwargs):
        """
        List entities with full OData support.

        Supports: $filter, $select, $expand, $orderby, $top, $skip, $count

        Returns DTOs serialized to JSON with OData metadata.
        """
        query_string = request.META.get("QUERY_STRING", "")
        selector = self.get_selector()

        try:
            dtos = selector.query_as_dtos(query_string)
        except (core_ex.InvalidFieldError, core_ex.InvalidValueError, core_ex.QueryError) as e:
            self._reraise_as_odata_error(e)

        serializer = self.get_serializer(dtos, many=True)

        return Response(
            build_odata_response(
                request=request,
                serializer_data=serializer.data,
                query_string=query_string,
                entity_set_name=self.odata_entity_set_name,
                selector=selector,
            )
        )

    def retrieve(self, request, *args, pk=None, **kwargs):
        """
        Retrieve a single entity with OData support.

        Uses QueryBuilder to filter by pk without exposing QuerySet.
        """
        from fc_selector.core import QueryBuilder

        query_string = request.META.get("QUERY_STRING", "")
        selector = self.get_selector()

        # Build query with pk filter using pure OData syntax
        query = QueryBuilder(query_string).and_filter(f"id eq {pk}")

        try:
            dto = selector.get_one(query)
        except (core_ex.InvalidFieldError, core_ex.InvalidValueError, core_ex.QueryError) as e:
            self._reraise_as_odata_error(e)

        if not dto:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(self.get_serializer(dto).data)
