"""
Mixin classes for adding OData functionality to Django REST Framework components.
"""

import logging
from typing import Any

from django.db.models import QuerySet
from django.http import Http404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from .exceptions import (
    ODataExpandError,
    ODataFilterError,
)
from .optimization import optimize_queryset_for_expand, optimize_queryset_for_select
from .utils import (
    apply_odata_query_params,
    build_odata_metadata,
    parse_expand_fields_v2,
    parse_odata_query,
)

logger = logging.getLogger(__name__)


class ODataSerializerMixin:
    """
    Mixin for serializers to add OData-specific functionality.
    """

    def get_odata_context(self) -> dict[str, Any]:
        """
        Get OData context information for the serializer.

        Returns:
            Dictionary containing OData context
        """
        context = {
            "odata_version": "4.0",
            "service_root": getattr(
                self.context.get("request"), "build_absolute_uri", lambda x: x
            )("/odata/"),
        }

        if hasattr(self, "Meta") and hasattr(self.Meta, "model"):
            context["entity_set"] = self.Meta.model.__name__.lower() + "s"
            context["entity_type"] = self.Meta.model.__name__

        return context

    def to_representation(self, instance):
        """
        Add OData-specific representation logic.
        """
        data = super().to_representation(instance)

        # Add @odata.context if this is a single entity response
        request = self.context.get("request")
        if request and hasattr(self, "Meta") and hasattr(self.Meta, "model"):
            # Handle both DRF requests and mock requests safely
            query_params = getattr(request, "query_params", getattr(request, "GET", {}))
            headers = getattr(request, "headers", getattr(request, "META", {}))

            include_context = query_params.get("$format") == "json" or headers.get(
                "Accept", headers.get("HTTP_ACCEPT", "")
            ).startswith("application/json")

            if include_context and hasattr(instance, "pk"):
                odata_context = self.get_odata_context()
                data["@odata.context"] = (
                    f"{odata_context['service_root']}$metadata#{odata_context['entity_set']}/$entity"
                )

        return data

    # Note: Field selection and expansion are now handled by
    # NativeFieldSelectionMixin and NativeFieldExpansionMixin
    # No need for FlexFields-specific parameter mapping


class ODataMixin:
    """
    Mixin for ViewSets to add OData query support.
    """

    def get_odata_query_params(self) -> dict[str, Any]:
        """
        Extract and parse OData query parameters from the request.

        Returns:
            Dictionary containing parsed OData query parameters
        """
        # Handle both DRF request (has query_params) and Django request (has GET)
        query_params = getattr(self.request, "query_params", self.request.GET)
        return parse_odata_query(query_params)

    def apply_odata_query(self, queryset: QuerySet) -> QuerySet:
        """
        Apply OData query parameters to the queryset.

        Args:
            queryset: Base queryset to filter

        Returns:
            Filtered and ordered queryset

        Raises:
            ODataFilterError: If filter parsing or execution fails
        """
        odata_params = self.get_odata_query_params()

        try:
            queryset = apply_odata_query_params(queryset, odata_params)

            # Add any custom business logic here
            # For example, only show published posts to non-staff users
            user = getattr(self.request, "user", None)
            if user and not user.is_staff:
                if hasattr(queryset.model, "status"):
                    queryset = queryset.filter(status="published")
            return queryset
        except Exception as e:
            logger.error(f"Error applying OData query: {e}")
            # Convert generic exceptions to OData-specific errors
            if isinstance(e, (ODataFilterError, ODataExpandError)):
                raise  # Re-raise OData errors as-is
            else:
                # Wrap unexpected exceptions in ODataFilterError
                raise ODataFilterError(
                    message=f"Unexpected error processing OData query: {str(e)}",
                    code="InternalError",
                    original_exception=e,
                ) from e

    def get_queryset(self):
        """
        Get the queryset with OData query parameters applied and optimized for field selection and expanded relations.
        """
        queryset = super().get_queryset()

        # Apply optimizations using the extracted functions
        try:
            queryset = self._apply_odata_optimizations(queryset)
        except (ODataFilterError, ODataExpandError):
            # Re-raise to be caught by list/retrieve methods
            raise

        # Apply OData query parameters
        return self.apply_odata_query(queryset)

    def _apply_odata_optimizations(self, queryset):
        """
        Apply OData optimizations using the extracted optimization functions.

        This method replaces the inline optimization logic with calls to the
        extracted functions for better maintainability and reusability.
        """
        odata_params = self.get_odata_query_params()

        # Parse expand fields for optimization
        expand_fields = {}
        if "$expand" in odata_params:
            expand_value = odata_params["$expand"]
            if isinstance(expand_value, list):
                expand_value = expand_value[0] if expand_value else ""
            if expand_value:
                try:
                    expand_fields = parse_expand_fields_v2(expand_value)
                    # Validate expand fields exist on the model
                    self._validate_expand_fields(expand_fields, queryset.model)
                except ODataExpandError:
                    # Re-raise OData errors to be caught by list/retrieve methods
                    raise
                except Exception as e:
                    logger.warning(f"Error parsing $expand parameter: {e}")
                    # Continue without expand optimization for unexpected errors

        # Apply field selection optimization
        if "$select" in odata_params:
            select_fields = odata_params["$select"]
            if isinstance(select_fields, str):
                select_fields = [f.strip() for f in select_fields.split(",")]
            queryset = optimize_queryset_for_select(
                queryset, select_fields, expand_fields
            )

        # Apply expansion optimization with error handling
        if expand_fields:
            try:
                queryset = optimize_queryset_for_expand(queryset, expand_fields)
            except Exception as e:
                # Check if this is a FieldError from select_related/prefetch_related
                error_msg = str(e).lower()
                if (
                    "select_related" in error_msg
                    or "prefetch_related" in error_msg
                    or "cannot find" in error_msg
                    or "invalid parameter" in error_msg
                ):
                    # Extract field name from error message
                    field_name = "unknown"

                    # Try different patterns to extract field name
                    if "given in select_related:" in str(e):
                        try:
                            field_part = (
                                str(e)
                                .split("given in select_related:")[1]
                                .split("'")[1]
                            )
                            field_name = field_part
                        except (IndexError, ValueError):
                            pass
                    elif "cannot find" in str(e) and "on" in str(e):
                        try:
                            # Pattern: "Cannot find 'field_name' on Model object"
                            field_part = str(e).split("'")[1]
                            field_name = field_part
                        except (IndexError, ValueError):
                            pass
                    elif "invalid parameter to prefetch_related" in str(e):
                        try:
                            # Pattern: "... 'field_name' is an invalid parameter to prefetch_related()"
                            field_part = str(e).split("'")[1]
                            field_name = field_part
                        except (IndexError, ValueError):
                            pass

                    # Get valid field choices
                    model = queryset.model
                    valid_fields = [
                        f.name
                        for f in model._meta.get_fields()
                        if hasattr(f, "related_model")
                    ]

                    raise ODataExpandError(
                        field_name=field_name,
                        model_name=model.__name__,
                        valid_fields=valid_fields,
                        original_exception=e,
                    ) from e
                else:
                    # Re-raise other exceptions
                    raise

        return queryset

    # Removed _build_only_fields_list - now handled by optimize_queryset_for_select

    # Removed _optimize_queryset_for_expansions - now handled by _apply_odata_optimizations

    def _validate_expand_fields(self, expand_fields: dict[str, Any], model):
        """
        Validate that expand fields exist on the model.

        Args:
            expand_fields: Dictionary of fields to expand
            model: Django model class

        Raises:
            ODataExpandError: If any expand field doesn't exist
        """
        if not expand_fields:
            return

        # Get all valid relation fields on the model
        valid_fields = []
        for field in model._meta.get_fields():
            if hasattr(field, "related_model"):
                valid_fields.append(field.name)

        # Check each expand field
        for field_name in expand_fields.keys():
            if field_name not in valid_fields:
                raise ODataExpandError(
                    field_name=field_name,
                    model_name=model.__name__,
                    valid_fields=valid_fields,
                )

    # Removed all optimization methods - now handled by extracted functions

    def get_serializer_context(self):
        """
        Add OData context to serializer.
        """
        context = super().get_serializer_context()
        context["odata_params"] = self.get_odata_query_params()
        return context

    def list(self, request, *args, **kwargs):
        """
        Enhanced list method with OData response formatting.
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())
        except (ODataFilterError, ODataExpandError) as e:
            # Return OData-compliant error response
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.detail.get("error", {}).get("details", []),
                    }
                },
                status=e.status_code,
            )

        # Handle $count parameter (only include count when explicitly requested)
        odata_params = self.get_odata_query_params()
        include_count = (
            "$count" in odata_params and odata_params["$count"].lower() == "true"
        )

        # Calculate count if requested (BEFORE pagination to reflect total items)
        total_count = None
        if include_count:
            total_count = queryset.count()

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)

            # Get the paginated response from DRF
            paginated_response = self.get_paginated_response(serializer.data)

            # Transform DRF pagination format to OData format
            # DRF format: {"count": X, "next": "...", "previous": "...", "results": [...]}
            # OData format: {"@odata.context": "...", "@odata.count": X, "value": [...]}
            response_data = {"value": serializer.data}

            # Add count if requested
            if include_count:
                response_data["@odata.count"] = total_count

            # Add OData context for paginated responses
            if hasattr(self, "get_serializer_class"):
                serializer_class = self.get_serializer_class()
                if hasattr(serializer_class, "Meta") and hasattr(
                    serializer_class.Meta, "model"
                ):
                    model_name = serializer_class.Meta.model.__name__.lower()
                    response_data["@odata.context"] = (
                        f"{request.build_absolute_uri('/odata/')}$metadata#{model_name}s"
                    )

            # Optionally preserve DRF's next/previous links for client convenience
            # (Not part of OData spec, but useful for backward compatibility)
            if "next" in paginated_response.data:
                response_data["@odata.nextLink"] = paginated_response.data["next"]
            if "previous" in paginated_response.data:
                response_data["@odata.previousLink"] = paginated_response.data[
                    "previous"
                ]

            return Response(response_data)

        # Non-paginated response
        serializer = self.get_serializer(queryset, many=True)
        response_data = {"value": serializer.data}

        # Add count if requested
        if include_count:
            response_data["@odata.count"] = total_count

        # Add OData context
        if hasattr(self, "get_serializer_class"):
            serializer_class = self.get_serializer_class()
            if hasattr(serializer_class, "Meta") and hasattr(
                serializer_class.Meta, "model"
            ):
                model_name = serializer_class.Meta.model.__name__.lower()
                response_data["@odata.context"] = (
                    f"{request.build_absolute_uri('/odata/')}$metadata#{model_name}s"
                )

        return Response(response_data)

    def retrieve(self, request, *args, **kwargs):
        """
        Enhanced retrieve method with OData response formatting.
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except (ODataFilterError, ODataExpandError) as e:
            # Return OData-compliant error response
            return Response(
                {
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.detail.get("error", {}).get("details", []),
                    }
                },
                status=e.status_code,
            )
        except Http404:
            # Return OData-style 404 response
            return Response(
                {
                    "error": {
                        "code": "NotFound",
                        "message": "The requested resource was not found.",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["get"], url_path=r"\$metadata")
    def metadata(self, request):
        """
        Return OData metadata document.
        """
        try:
            serializer_class = self.get_serializer_class()
            model_class = getattr(serializer_class.Meta, "model", None)

            if not model_class:
                return Response(
                    {
                        "error": {
                            "code": "InternalError",
                            "message": "No model class found for metadata generation.",
                        }
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            metadata = build_odata_metadata(model_class, serializer_class)

            # Build full OData metadata document
            metadata_doc = {
                "$Version": "4.0",
                "$EntityContainer": f"{model_class._meta.app_label}.Container",
                f"{model_class._meta.app_label}": {
                    "$Alias": "Self",
                    "$Kind": "Schema",
                    model_class.__name__: {
                        "$Kind": "EntityType",
                        "$Key": [
                            "id"
                        ],  # Assume 'id' is the key, could be made configurable
                        **{
                            prop_name: {"$Type": prop_info["type"]}
                            for prop_name, prop_info in metadata["properties"].items()
                        },
                    },
                    "Container": {
                        "$Kind": "EntityContainer",
                        f"{model_class.__name__.lower()}s": {
                            "$Collection": True,
                            "$Type": f"Self.{model_class.__name__}",
                        },
                    },
                },
            }

            return Response(metadata_doc, content_type="application/json")

        except Exception as e:
            logger.error(f"Error generating metadata: {e}")
            return Response(
                {
                    "error": {
                        "code": "InternalError",
                        "message": "Error generating metadata document.",
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="")
    def service_document(self, request):
        """
        Return OData service document.
        """
        try:
            serializer_class = self.get_serializer_class()
            model_class = getattr(serializer_class.Meta, "model", None)

            if not model_class:
                return Response(
                    {
                        "error": {
                            "code": "InternalError",
                            "message": "No model class found for service document generation.",
                        }
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            service_doc = {
                "@odata.context": f"{request.build_absolute_uri('/odata/')}$metadata",
                "value": [
                    {
                        "name": f"{model_class.__name__.lower()}s",
                        "kind": "EntitySet",
                        "url": f"{model_class.__name__.lower()}s",
                    }
                ],
            }

            return Response(service_doc)

        except Exception as e:
            logger.error(f"Error generating service document: {e}")
            return Response(
                {
                    "error": {
                        "code": "InternalError",
                        "message": "Error generating service document.",
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
