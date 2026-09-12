"""
OData Selector ViewSet Mixin.

Provides OData support using the Selector + DTO pattern for hexagonal architecture.
"""

from urllib.parse import urlencode

from django.core.exceptions import FieldError, ValidationError
from rest_framework import status
from rest_framework.response import Response

from fc_selector.core import exceptions as core_ex
from fc_selector.exceptions import (
    ODataFieldNotFoundError,
    ODataFilterError,
    ODataInvalidPaginationError,
    ODataInvalidValueError,
)
from fc_selector.protocols.odata.builder import dto_options
from fc_selector.protocols.odata.parsers.query import MAX_SKIP_VALUE, MAX_TOP_VALUE, parse_query_params

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

    parsed_qs = parse_query_params(query_string)

    if parsed_qs.get("$count", "").lower() == "true":
        if total_count is not None:
            # Use pre-calculated count (when RLS or additional filters are applied)
            response_data["@odata.count"] = total_count
        elif selector:
            # Count should be independent of pagination
            count_query = urlencode(
                {k: v for k, v in parsed_qs.items() if k not in ("$count", "$top", "$skip")}, safe="$"
            )
            response_data["@odata.count"] = selector.query(count_query).count()

    default = getattr(selector, "default_limit", DEFAULT_PAGE_SIZE) if selector else DEFAULT_PAGE_SIZE
    maximum = getattr(selector, "max_limit", MAX_TOP_VALUE) if selector else MAX_TOP_VALUE
    if not isinstance(default, int):
        default = DEFAULT_PAGE_SIZE
    if not isinstance(maximum, int):
        maximum = MAX_TOP_VALUE

    # Pagination links, with the same bounds the query parser enforces
    try:
        top = min(int(parsed_qs.get("$top", default)), maximum, MAX_TOP_VALUE)
        skip = min(int(parsed_qs.get("$skip", 0)), MAX_SKIP_VALUE)
    except (ValueError, TypeError):
        top, skip = DEFAULT_PAGE_SIZE, 0

    if top < 0:
        top = DEFAULT_PAGE_SIZE
    skip = max(skip, 0)

    # Exactly 'top' results means there may be more
    if (
        top > 0
        and len(serializer_data) == top
        and skip + top <= MAX_SKIP_VALUE
        and (total_count is None or skip + top < total_count)
    ):
        next_params = {**parsed_qs, "$skip": str(skip + top)}
        next_query = urlencode(next_params, safe="$")
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
            if exc.context in ("$top", "$skip"):
                raise ODataInvalidPaginationError(
                    parameter=exc.context,
                    value=str(exc.value),
                    original_exception=exc,
                ) from exc
            # Any other bad literal (e.g. a malformed datetime in $filter)
            raise ODataInvalidValueError(
                value=str(exc.value),
                expected_type=str(exc.expected_type) if exc.expected_type else "unknown",
                field=exc.context or "$filter",
                original_exception=exc,
            ) from exc
        raise ODataFilterError(message=str(exc), original_exception=exc) from exc

    def get_queryset(self):
        """Use an explicit view queryset when present, otherwise the selector scope."""
        if getattr(self, "queryset", None) is not None:
            return super().get_queryset()
        return self.get_selector().get_queryset()

    def list(self, request, *args, **kwargs):
        query_string = request.META.get("QUERY_STRING", "")
        selector = self.get_selector()
        try:
            queryset = self.filter_queryset(self.get_queryset())
            dtos = selector.query_as_dtos(query_string, base_queryset=queryset)
            total_count = None
            if parse_query_params(query_string).get("$count", "").lower() == "true":
                _, intent = selector._parse(query_string)
                intent.pagination = None
                intent.select = None
                intent.expand = None
                total_count = selector.execute(intent, queryset).count()
            serializer = self.get_serializer(dtos, many=True)
            data = build_odata_response(
                request, serializer.data, query_string, self.odata_entity_set_name, selector, total_count
            )
        except (core_ex.SelectorError, FieldError, ValidationError) as exc:
            self._reraise_as_odata_error(exc)
        return Response(data)

    def retrieve(self, request, *args, pk=None, **kwargs):
        selector = self.get_selector()
        query_string = request.META.get("QUERY_STRING", "")
        try:
            _, intent = selector._parse(query_string)
            queryset = self.filter_queryset(self.get_queryset())
            pk_field = queryset.model._meta.pk
            lookup = pk_field.to_python(pk)
            queryset = queryset.filter(pk=lookup)
            # Validate client pagination but never let it change identity lookup.
            intent = selector._executor.prepare(queryset, intent)
            intent.pagination = None
            instance = selector._executor._execute_prepared(queryset, intent).first()
            if instance is None:
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
            self.check_object_permissions(request, instance)
            selected, options = dto_options(intent)
            dto = selector.to_dto(instance, selected, set(options), options)
        except (core_ex.SelectorError, FieldError, ValidationError) as exc:
            self._reraise_as_odata_error(exc)
        return Response(self.get_serializer(dto).data)
