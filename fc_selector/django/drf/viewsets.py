"""
OData-compatible ViewSets that extend Django REST Framework functionality.
"""

from django.conf import settings
from django.db import connection, reset_queries
from django.urls import reverse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .mixins import ODataMixin
from .schema import ODataAutoSchema
from .serializers import ODataModelSerializer


class ODataViewSet(ODataMixin, viewsets.ViewSet):
    """
    Base OData ViewSet that provides OData query support for non-model viewsets.

    This viewset provides:
    - OData query parameter parsing and application
    - OData-formatted responses
    - $metadata endpoint support
    - Service document endpoint support

    ## Supported OData Query Parameters

    ### `$filter` - Filter results
    - Examples: `?$filter=status eq 'active'`, `?$filter=age gt 18`
    - Operators: eq, ne, gt, ge, lt, le, and, or, not, contains, startswith, endswith

    ### `$select` - Select specific fields
    - Examples: `?$select=id,name`, `?$select=id,title,author`

    ### `$expand` - Expand related entities
    - Examples: `?$expand=author`, `?$expand=author,category`

    ### `$orderby` - Sort results
    - Examples: `?$orderby=created_at desc`, `?$orderby=title`

    ### `$top` - Limit number of results
    - Examples: `?$top=10`, `?$top=25`

    ### `$skip` - Skip N results (pagination)
    - Examples: `?$skip=10`, `?$skip=20&$top=10`

    ### `$count` - Include total count
    - Examples: `?$count=true`

    All parameters can be combined: `?$filter=status eq 'published'&$select=id,title&$top=10&$count=true`
    """

    schema = ODataAutoSchema()

    def get_odata_entity_set_name(self) -> str:
        """
        Get the entity set name for this viewset.
        Override this method to provide custom entity set names.
        """
        if hasattr(self, "basename"):
            return self.basename
        return self.__class__.__name__.replace("ViewSet", "").lower() + "s"

    def get_odata_entity_type_name(self) -> str:
        """
        Get the entity type name for this viewset.
        Override this method to provide custom entity type names.
        """
        entity_set = self.get_odata_entity_set_name()
        return entity_set.rstrip("s").title()

    def list(self, request, *args, **kwargs):
        """
        Enhanced list method with OData collection formatting.
        """
        # Reset queries to track only this request
        if settings.DEBUG:
            reset_queries()

        # Get base response from parent
        response = super().list(request, *args, **kwargs)

        # Wrap in OData collection format if needed
        if isinstance(response.data, list):
            # Check if count should be included (only when explicitly requested)
            odata_params = self.get_odata_query_params()
            include_count = (
                "$count" in odata_params and odata_params["$count"].lower() == "true"
            )

            # Build OData response
            odata_response = {
                "@odata.context": self._get_collection_context_url(),
                "value": response.data,
            }

            # Add count if requested
            if include_count:
                odata_response["@odata.count"] = len(response.data)

            # Add debug queries if in debug mode
            if settings.DEBUG and hasattr(connection, 'queries'):
                queries = connection.queries
                odata_response["@debug"] = {
                    "query_count": len(queries),
                    "queries": [
                        {
                            "sql": q['sql'],
                            "time": q['time']
                        }
                        for q in queries
                    ],
                    "total_time": f"{sum(float(q['time']) for q in queries):.4f}"
                }

            response.data = odata_response

        return response

    def _get_collection_context_url(self) -> str:
        """Generate OData context URL for collections."""
        entity_set = self.get_odata_entity_set_name()
        base_url = self.request.build_absolute_uri("/odata/")
        return f"{base_url}$metadata#{entity_set}"


class ODataModelViewSet(ODataMixin, viewsets.ReadOnlyModelViewSet):
    """
    OData-compatible ModelViewSet that provides READ-ONLY operations with OData query support.

    **IMPORTANT: This viewset is READ-ONLY by design. It does NOT support write operations
    (create, update, partial_update, destroy). Use ODataReadOnlyModelViewSet for clarity.**

    This viewset provides:
    - Read-only access to model instances (list, retrieve ONLY)
    - OData query parameter support ($filter, $orderby, $top, $skip, etc.)
    - Dynamic field selection and expansion
    - OData-formatted responses with proper context
    - $metadata and service document endpoints

    Note: This extends ReadOnlyModelViewSet, so POST, PUT, PATCH, DELETE are not available.

    ## Supported OData Query Parameters

    ### `$filter` - Filter results using OData expressions
    Filter your data using OData v4 filter syntax.

    **Comparison Operators:**
    - `eq` - Equal: `?$filter=status eq 'published'`
    - `ne` - Not equal: `?$filter=status ne 'draft'`
    - `gt` - Greater than: `?$filter=age gt 18`
    - `ge` - Greater than or equal: `?$filter=price ge 100`
    - `lt` - Less than: `?$filter=age lt 65`
    - `le` - Less than or equal: `?$filter=price le 1000`

    **Logical Operators:**
    - `and` - Logical AND: `?$filter=status eq 'published' and age gt 18`
    - `or` - Logical OR: `?$filter=status eq 'draft' or status eq 'published'`
    - `not` - Logical NOT: `?$filter=not (status eq 'archived')`

    **String Functions:**
    - `contains` - Contains: `?$filter=contains(title, 'OData')`
    - `startswith` - Starts with: `?$filter=startswith(name, 'John')`
    - `endswith` - Ends with: `?$filter=endswith(email, '@example.com')`

    ### `$select` - Select specific fields to return
    Reduce response size by selecting only the fields you need.

    **Examples:**
    - `?$select=id,title` - Return only id and title
    - `?$select=id,name,email,created_at` - Return multiple fields

    ### `$expand` - Expand related entities (eager loading)
    Include related entities in the response to reduce the number of requests.

    **Examples:**
    - `?$expand=author` - Include full author object
    - `?$expand=author,category` - Expand multiple relations
    - `?$expand=author($select=id,name)` - Expand with nested $select

    ### `$orderby` - Sort results
    Sort results by one or more fields in ascending or descending order.

    **Examples:**
    - `?$orderby=created_at` - Sort by created_at ascending (default)
    - `?$orderby=created_at desc` - Sort by created_at descending
    - `?$orderby=status,created_at desc` - Multi-field sort (status asc, then created_at desc)

    ### `$top` - Limit number of results (LIMIT)
    Limit the number of results returned. Use with `$skip` for pagination.

    **Examples:**
    - `?$top=10` - Return first 10 results
    - `?$top=25` - Return first 25 results

    ### `$skip` - Skip N results (OFFSET)
    Skip the first N results. Use with `$top` for pagination.

    **Pagination Examples:**
    - Page 1: `?$top=10&$skip=0`
    - Page 2: `?$top=10&$skip=10`
    - Page 3: `?$top=10&$skip=20`

    **Formula:** `skip = (page_number - 1) * page_size`

    ### `$count` - Include total count in response
    Add `@odata.count` to the response with the total number of results (before pagination).

    **Examples:**
    - `?$count=true` - Include total count
    - `?$top=10&$count=true` - Get 10 results + total count

    ### Combining Parameters
    All parameters can be combined for powerful queries:

    ```
    ?$filter=status eq 'published' and age gt 18
     &$select=id,title,author,created_at
     &$expand=author($select=id,name)
     &$orderby=created_at desc
     &$top=10
     &$skip=20
     &$count=true
    ```

    This returns:
    - Only published posts where age > 18
    - With fields: id, title, author (expanded), created_at
    - Sorted by created_at descending
    - Results 21-30 (page 3 with 10 per page)
    - Including total count
    """

    serializer_class = ODataModelSerializer
    schema = ODataAutoSchema()

    def get_odata_entity_set_name(self) -> str:
        """
        Get the entity set name for this model.
        """
        if hasattr(self.get_serializer_class(), "Meta") and hasattr(
            self.get_serializer_class().Meta, "model"
        ):
            model = self.get_serializer_class().Meta.model
            return model.__name__.lower() + "s"
        return super().get_odata_entity_set_name()

    def get_odata_entity_type_name(self) -> str:
        """
        Get the entity type name for this model.
        """
        if hasattr(self.get_serializer_class(), "Meta") and hasattr(
            self.get_serializer_class().Meta, "model"
        ):
            model = self.get_serializer_class().Meta.model
            return model.__name__
        return super().get_odata_entity_type_name()

    def list(self, request, *args, **kwargs):
        """
        Enhanced list method with OData collection formatting and debug info.
        """
        # Reset queries to track only this request
        if settings.DEBUG:
            reset_queries()

        # Get base response from parent
        response = super().list(request, *args, **kwargs)

        # Wrap in OData collection format if needed
        if isinstance(response.data, list):
            # Check if count should be included (only when explicitly requested)
            odata_params = self.get_odata_query_params()
            include_count = (
                "$count" in odata_params and odata_params["$count"].lower() == "true"
            )

            # Build OData response
            odata_response = {
                "@odata.context": self._get_collection_context_url(),
                "value": response.data,
            }

            # Add count if requested
            if include_count:
                odata_response["@odata.count"] = len(response.data)

            # Add debug queries if in debug mode
            if settings.DEBUG and hasattr(connection, 'queries'):
                queries = connection.queries
                odata_response["@debug"] = {
                    "query_count": len(queries),
                    "queries": [
                        {
                            "sql": q['sql'],
                            "time": q['time']
                        }
                        for q in queries
                    ],
                    "total_time": f"{sum(float(q['time']) for q in queries):.4f}"
                }

            response.data = odata_response

        return response

    def _get_collection_context_url(self) -> str:
        """Generate OData context URL for collections."""
        entity_set = self.get_odata_entity_set_name()
        base_url = self.request.build_absolute_uri("/odata/")
        return f"{base_url}$metadata#{entity_set}"

    @action(
        detail=True,
        methods=["get"],
        url_path=r"\$links/(?P<navigation_property>[\w-]+)",
    )
    def get_navigation_links(self, request, navigation_property=None, pk=None):
        """
        Get navigation property links for an entity.
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)

            # Check if the navigation property exists
            nav_props = getattr(serializer, "get_navigation_properties", lambda: {})()
            if navigation_property not in nav_props:
                return Response(
                    {
                        "error": {
                            "code": "BadRequest",
                            "message": f'Navigation property "{navigation_property}" does not exist.',
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get the related objects
            if hasattr(instance, navigation_property):
                related_obj = getattr(instance, navigation_property)

                if related_obj is None:
                    links = {"value": []}
                elif hasattr(related_obj, "all"):  # Many-to-many or reverse foreign key
                    links = {
                        "value": [
                            {
                                "url": reverse(
                                    f"{self.basename}-detail",
                                    kwargs={"pk": obj.pk},
                                    request=request,
                                )
                            }
                            for obj in related_obj.all()
                        ]
                    }
                else:  # Single related object
                    links = {
                        "value": [
                            {
                                "url": reverse(
                                    f"{self.basename}-detail",
                                    kwargs={"pk": related_obj.pk},
                                    request=request,
                                )
                            }
                        ]
                    }

                return Response(links)
            else:
                return Response(
                    {
                        "error": {
                            "code": "BadRequest",
                            "message": f'Navigation property "{navigation_property}" is not accessible.',
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except (AttributeError, KeyError) as e:
            return Response(
                {
                    "error": {
                        "code": "BadRequest",
                        "message": f"Invalid navigation property access: {str(e)}",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (AttributeError, KeyError) as e:
            return Response(
                {
                    "error": {
                        "code": "BadRequest",
                        "message": f"Invalid navigation property access: {str(e)}",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": {"code": "InternalError", "message": str(e)}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], url_path=r"(?P<navigation_property>[\w-]+)")
    def get_navigation_property(self, request, navigation_property=None, pk=None):
        """
        Get navigation property values for an entity.
        """
        try:
            instance = self.get_object()

            # Check if the navigation property exists
            if not hasattr(instance, navigation_property):
                return Response(
                    {
                        "error": {
                            "code": "BadRequest",
                            "message": f'Navigation property "{navigation_property}" does not exist.',
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            related_obj = getattr(instance, navigation_property)

            if related_obj is None:
                return Response(None, status=status.HTTP_204_NO_CONTENT)
            elif hasattr(related_obj, "all"):  # QuerySet or related manager
                # Apply OData query parameters to the related queryset
                queryset = self.apply_odata_query(related_obj.all())

                # Get appropriate serializer for the related model
                related_serializer_class = self._get_related_serializer_class(
                    navigation_property
                )
                if related_serializer_class:
                    serializer = related_serializer_class(
                        queryset, many=True, context=self.get_serializer_context()
                    )
                    return Response(
                        {
                            "@odata.context": f"{request.build_absolute_uri('/odata/')}$metadata#{navigation_property}",
                            "value": serializer.data,
                        }
                    )
                else:
                    # Fallback to basic serialization
                    return Response(
                        {
                            "@odata.context": f"{request.build_absolute_uri('/odata/')}$metadata#{navigation_property}",
                            "value": list(queryset.values()),
                        }
                    )
            else:  # Single related object
                related_serializer_class = self._get_related_serializer_class(
                    navigation_property
                )
                if related_serializer_class:
                    serializer = related_serializer_class(
                        related_obj, context=self.get_serializer_context()
                    )
                    data = serializer.data
                    data["@odata.context"] = (
                        f"{request.build_absolute_uri('/odata/')}$metadata#{navigation_property}/$entity"
                    )
                    return Response(data)
                else:
                    # Fallback to basic serialization
                    return Response(
                        {
                            "@odata.context": (
                                f"{request.build_absolute_uri('/odata/')}"
                                f"$metadata#{navigation_property}/$entity"
                            ),
                            **{
                                field.name: getattr(related_obj, field.name)
                                for field in related_obj._meta.fields
                            },
                        }
                    )

        except Exception as e:
            return Response(
                {"error": {"code": "InternalError", "message": str(e)}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_related_serializer_class(self, navigation_property):
        """
        Get the serializer class for a navigation property.
        """
        serializer = self.get_serializer()
        if hasattr(serializer, "Meta") and hasattr(
            serializer.Meta, "expandable_fields"
        ):
            expandable_fields = serializer.Meta.expandable_fields
            if navigation_property in expandable_fields:
                config = expandable_fields[navigation_property]
                if isinstance(config, tuple) and len(config) > 0:
                    # Try to import the serializer class
                    serializer_path = config[0]
                    try:
                        module_path, class_name = serializer_path.rsplit(".", 1)
                        module = __import__(module_path, fromlist=[class_name])
                        return getattr(module, class_name)
                    except (ImportError, AttributeError):
                        pass
        return None


class ODataReadOnlyModelViewSet(ODataMixin, viewsets.ReadOnlyModelViewSet):
    """
    OData-compatible ReadOnlyModelViewSet for read-only entity sets.

    This viewset provides:
    - Read-only access to model instances
    - OData query parameter support
    - Dynamic field selection and expansion
    - OData-formatted responses
    """

    serializer_class = ODataModelSerializer

    def get_odata_entity_set_name(self) -> str:
        """Get the entity set name for this model."""
        if hasattr(self.get_serializer_class(), "Meta") and hasattr(
            self.get_serializer_class().Meta, "model"
        ):
            model = self.get_serializer_class().Meta.model
            return model.__name__.lower() + "s"
        return self.__class__.__name__.replace("ViewSet", "").lower() + "s"

    def get_odata_entity_type_name(self) -> str:
        """Get the entity type name for this model."""
        if hasattr(self.get_serializer_class(), "Meta") and hasattr(
            self.get_serializer_class().Meta, "model"
        ):
            model = self.get_serializer_class().Meta.model
            return model.__name__
        return self.__class__.__name__.replace("ViewSet", "").title()


# Convenience function for creating OData viewsets
def create_odata_viewset(model_class, serializer_class=None, read_only=False, **kwargs):
    """
    Factory function to create OData viewsets for Django models.

    Args:
        model_class: Django model class
        serializer_class: Optional custom serializer class
        read_only: If True, creates a ReadOnlyModelViewSet
        **kwargs: Additional viewset options

    Returns:
        ODataModelViewSet or ODataReadOnlyModelViewSet subclass
    """
    base_class = ODataReadOnlyModelViewSet if read_only else ODataModelViewSet

    class_attrs = {
        "queryset": model_class.objects.all(),
    }

    if serializer_class:
        class_attrs["serializer_class"] = serializer_class

    # Add any additional attributes
    class_attrs.update(kwargs)

    # Create the viewset class
    viewset_name = f"{model_class.__name__}ODataViewSet"
    viewset_class = type(viewset_name, (base_class,), class_attrs)

    return viewset_class


def build_odata_response(request, serializer_data, query_string, entity_set_name, selector=None):
    """
    Build OData-compliant response with pagination, count, and debug info.

    Args:
        request: Django request object
        serializer_data: Serialized data to return
        query_string: OData query string
        entity_set_name: Name of the entity set (posts, authors, etc.)
        selector: Optional selector instance for count queries

    Returns:
        dict: OData response with @odata.context, value, @odata.count, @odata.nextLink, @debug
    """
    response_data = {
        "@odata.context": f"{request.build_absolute_uri('/odata/')}$metadata#{entity_set_name}",
        "value": serializer_data
    }

    # Parse query string
    parsed_qs = {}
    for param in query_string.split('&'):
        if '=' in param:
            key, value = param.split('=', 1)
            parsed_qs[key] = value

    # Add OData count if requested
    if '$count' in parsed_qs and parsed_qs.get('$count', '').lower() == 'true':
        if selector:
            # Remove $count from query to get accurate count
            count_query = '&'.join([f"{k}={v}" for k, v in parsed_qs.items() if k != '$count'])
            total_count = selector.query(count_query).count()
            response_data["@odata.count"] = total_count

    # Add pagination links (nextLink)
    top = int(parsed_qs.get('$top', 50))
    skip = int(parsed_qs.get('$skip', 0))

    # Check if there are more results
    if len(serializer_data) == top:  # If we got exactly 'top' results, there might be more
        next_skip = skip + top
        # Build next link
        next_params = parsed_qs.copy()
        next_params['$skip'] = str(next_skip)
        next_query = '&'.join([f"{k}={v}" for k, v in next_params.items()])
        response_data["@odata.nextLink"] = f"{request.build_absolute_uri(request.path)}?{next_query}"

    # Add debug queries if in debug mode
    if settings.DEBUG and hasattr(connection, 'queries'):
        queries = connection.queries
        response_data["@debug"] = {
            "query_count": len(queries),
            "queries": [
                {
                    "sql": q['sql'],
                    "time": q['time']
                }
                for q in queries
            ],
            "total_time": f"{sum(float(q['time']) for q in queries):.4f}"
        }

    return response_data


class ODataSelectorViewSetMixin:
    """
    Mixin to add OData support to ViewSets using the Selector + DTO pattern.
    
    Requires:
    - selector_class: The Selector class to use
    - odata_entity_set_name: Name of the entity set for OData metadata
    """
    selector_class = None
    odata_entity_set_name = None

    def get_selector(self):
        if self.selector_class is None:
            raise NotImplementedError(f"{self.__class__.__name__} must define 'selector_class'")
        return self.selector_class()

    def list(self, request, *args, **kwargs):
        """
        List entities with full OData support.
        """
        # Reset queries to track only this request
        if settings.DEBUG:
            reset_queries()

        # Get OData query string from request
        query_string = request.META.get('QUERY_STRING', '')

        # Use selector to query database with OData parameters
        selector = self.get_selector()
        dtos = selector.query_as_dtos(query_string)

        # Serialize DTOs to JSON
        serializer = self.get_serializer(dtos, many=True)

        # Build OData response with pagination
        response_data = build_odata_response(
            request=request,
            serializer_data=serializer.data,
            query_string=query_string,
            entity_set_name=self.odata_entity_set_name,
            selector=selector
        )

        return Response(response_data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """
        Retrieve a single entity with OData support.
        """
        # Get OData query string
        query_string = request.META.get('QUERY_STRING', '')

        # Use selector
        selector = self.get_selector()

        # Query with OData params, then filter by pk
        queryset = selector.query(query_string)
        instance = queryset.filter(pk=pk).first()

        if not instance:
            return Response(
                {'detail': 'Not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Extract field selections
        selected_fields = selector._extract_selected_fields(query_string)
        expanded_fields = selector._extract_expanded_fields(query_string)

        # Convert to DTO
        dto = selector.to_dto(instance, selected_fields, expanded_fields)

        # Serialize
        serializer = self.get_serializer(dto)

        return Response(serializer.data)
