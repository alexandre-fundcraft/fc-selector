"""
Tests for OData ViewSet mixin.

Covers fc_selector/django/drf/viewsets/selector_mixin.py
"""

from dataclasses import dataclass

import pytest
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.test import APIRequestFactory

from fc_selector.core.dtos.base import BaseODataDTO
from fc_selector.django.drf.viewsets import ODataSelectorViewSetMixin
from fc_selector.django.drf.viewsets.selector_mixin import (
    ODATA_PARAMETERS,
    build_odata_response,
    get_odata_openapi_parameters,
)
from fc_selector.django.selector import ODataSelector
from tests.integration.support.models import ODataTestModel


class TestODataParameters:
    """Tests for OData parameter definitions."""

    def test_odata_parameters_list(self):
        """ODATA_PARAMETERS contains expected parameters."""
        param_names = [p["name"] for p in ODATA_PARAMETERS]
        assert "$filter" in param_names
        assert "$select" in param_names
        assert "$expand" in param_names
        assert "$orderby" in param_names
        assert "$top" in param_names
        assert "$skip" in param_names
        assert "$count" in param_names

    def test_odata_parameters_have_descriptions(self):
        """All parameters have descriptions."""
        for param in ODATA_PARAMETERS:
            assert "description" in param
            assert len(param["description"]) > 10  # Meaningful description


class TestGetODataOpenApiParameters:
    """Tests for get_odata_openapi_parameters."""

    def test_returns_list(self):
        """Returns list of parameters."""
        params = get_odata_openapi_parameters()
        assert isinstance(params, list)

    def test_parameters_have_names(self):
        """Each parameter has a name."""
        params = get_odata_openapi_parameters()
        # If drf-spectacular not available, returns empty list
        if params:
            for param in params:
                assert hasattr(param, "name")


class TestBuildODataResponse:
    """Tests for build_odata_response helper."""

    @pytest.fixture
    def request_factory(self):
        """Request factory fixture."""
        return APIRequestFactory()

    def test_basic_response_structure(self, request_factory):
        """Response has OData structure."""
        request = request_factory.get("/odata/posts/")
        request.META["HTTP_HOST"] = "localhost"

        data = [{"id": 1, "title": "Test"}]
        response = build_odata_response(
            request=request,
            serializer_data=data,
            query_string="$top=10",
            entity_set_name="posts",
        )

        assert "@odata.context" in response
        assert "value" in response
        assert response["value"] == data

    def test_response_context_url(self, request_factory):
        """Context URL is correctly formatted."""
        request = request_factory.get("/odata/posts/")
        request.META["HTTP_HOST"] = "localhost"

        response = build_odata_response(
            request=request,
            serializer_data=[],
            query_string="",
            entity_set_name="posts",
        )

        assert "posts" in response["@odata.context"]
        assert "$metadata" in response["@odata.context"]

    def test_next_link_when_full_page(self, request_factory):
        """nextLink added when results equal $top."""
        request = request_factory.get("/odata/posts/")
        request.META["HTTP_HOST"] = "localhost"

        # 10 items, $top=10 - might have more
        data = [{"id": i} for i in range(10)]
        response = build_odata_response(
            request=request,
            serializer_data=data,
            query_string="$top=10&$skip=0",
            entity_set_name="posts",
        )

        assert "@odata.nextLink" in response
        assert "$skip=10" in response["@odata.nextLink"]

    def test_no_next_link_when_partial_page(self, request_factory):
        """No nextLink when results less than $top."""
        request = request_factory.get("/odata/posts/")
        request.META["HTTP_HOST"] = "localhost"

        # 5 items, $top=10 - no more
        data = [{"id": i} for i in range(5)]
        response = build_odata_response(
            request=request,
            serializer_data=data,
            query_string="$top=10&$skip=0",
            entity_set_name="posts",
        )

        assert "@odata.nextLink" not in response

    def test_pagination_preserves_other_params(self, request_factory):
        """nextLink preserves other query params."""
        request = request_factory.get("/odata/posts/")
        request.META["HTTP_HOST"] = "localhost"

        data = [{"id": i} for i in range(10)]
        response = build_odata_response(
            request=request,
            serializer_data=data,
            query_string="$filter=active eq true&$top=10&$skip=0",
            entity_set_name="posts",
        )

        assert "$filter" in response["@odata.nextLink"]


@pytest.mark.django_db
class TestODataSelectorViewSetMixin:
    """Tests for ODataSelectorViewSetMixin."""

    def test_get_selector_not_implemented(self):
        """get_selector raises if selector_class not set."""

        class BadViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
            pass

        viewset = BadViewSet()
        with pytest.raises(NotImplementedError, match="selector_class"):
            viewset.get_selector()

    def test_get_selector_returns_instance(self):
        """get_selector returns selector instance."""

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        class TestViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
            selector_class = TestSelector

        viewset = TestViewSet()
        selector = viewset.get_selector()
        assert isinstance(selector, TestSelector)

    def test_get_list_schema_decorator(self):
        """get_list_schema_decorator returns callable."""

        class TestViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
            pass

        viewset = TestViewSet()
        decorator = viewset.get_list_schema_decorator()
        assert callable(decorator)

    def test_get_retrieve_schema_decorator(self):
        """get_retrieve_schema_decorator returns callable."""

        class TestViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
            pass

        viewset = TestViewSet()
        decorator = viewset.get_retrieve_schema_decorator()
        assert callable(decorator)

    def test_retrieve_returns_dto(self):
        """retrieve method returns serialized DTO."""

        @dataclass
        class TestDTO(BaseODataDTO):
            id: int
            name: str

        class TestDTOSerializer(serializers.Serializer):
            id = serializers.IntegerField()
            name = serializers.CharField()

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                dto_class = TestDTO

        class TestViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
            selector_class = TestSelector
            serializer_class = TestDTOSerializer
            odata_entity_set_name = "tests"

        # Create test instance
        instance = ODataTestModel.objects.create(
            name="Test",
            description="Desc",
            count=1,
            is_active=True,
            created_at=timezone.now(),
            status="draft",
        )

        # Create mock request
        factory = APIRequestFactory()
        request = factory.get(f"/odata/tests/{instance.id}/")
        request.META["QUERY_STRING"] = ""

        # Initialize viewset
        viewset = TestViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {"pk": instance.id}

        # Call retrieve
        response = viewset.retrieve(request, pk=instance.id)

        assert response.status_code == 200
        assert response.data["id"] == instance.id
        assert response.data["name"] == "Test"

    def test_retrieve_returns_404_when_not_found(self):
        """retrieve method returns 404 when entity not found."""

        @dataclass
        class TestDTO(BaseODataDTO):
            id: int
            name: str

        class TestDTOSerializer(serializers.Serializer):
            id = serializers.IntegerField()
            name = serializers.CharField()

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                dto_class = TestDTO

        class TestViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
            selector_class = TestSelector
            serializer_class = TestDTOSerializer
            odata_entity_set_name = "tests"

        # Create mock request with non-existent ID
        factory = APIRequestFactory()
        request = factory.get("/odata/tests/99999/")
        request.META["QUERY_STRING"] = ""

        # Initialize viewset
        viewset = TestViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {"pk": 99999}

        # Call retrieve with non-existent ID
        response = viewset.retrieve(request, pk=99999)

        assert response.status_code == 404
        assert "Not found" in response.data["detail"]

    def test_retrieve_with_select_expand(self):
        """retrieve method handles $select and $expand."""

        @dataclass
        class TestDTO(BaseODataDTO):
            id: int
            name: str

        class TestDTOSerializer(serializers.Serializer):
            id = serializers.IntegerField()
            name = serializers.CharField()

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                dto_class = TestDTO

        class TestViewSet(ODataSelectorViewSetMixin, viewsets.GenericViewSet):
            selector_class = TestSelector
            serializer_class = TestDTOSerializer
            odata_entity_set_name = "tests"

        # Create test instance
        instance = ODataTestModel.objects.create(
            name="Test",
            description="Desc",
            count=1,
            is_active=True,
            created_at=timezone.now(),
            status="draft",
        )

        # Create mock request with $select
        factory = APIRequestFactory()
        request = factory.get(f"/odata/tests/{instance.id}/?$select=id,name")
        request.META["QUERY_STRING"] = "$select=id,name"

        # Initialize viewset
        viewset = TestViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {"pk": instance.id}

        # Call retrieve
        response = viewset.retrieve(request, pk=instance.id)

        assert response.status_code == 200
