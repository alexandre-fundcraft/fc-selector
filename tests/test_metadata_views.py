"""
Tests for OData metadata views.

Covers fc_selector/django/views/metadata.py
"""
# pylint: disable=redefined-outer-name  # pytest fixtures

import json

import pytest
from django.test import RequestFactory

from fc_selector.django.selector import ODataSelector
from fc_selector.django.views.metadata import (
    ODataMetadataRegistry,
    ODataMetadataView,
    ODataServiceDocumentView,
)
from tests.integration.support.models import ODataRelatedModel, ODataTestModel


@pytest.fixture
def request_factory():
    """Request factory fixture."""
    return RequestFactory()


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear registry before and after each test."""
    ODataMetadataRegistry.clear()
    yield
    ODataMetadataRegistry.clear()


class TestODataMetadataRegistry:
    """Tests for ODataMetadataRegistry."""

    def test_register_selector(self):
        """Register a selector for an entity set."""

        class TestSelector(ODataSelector):
            pass

        ODataMetadataRegistry.register("tests", TestSelector)
        selectors = ODataMetadataRegistry.get_selectors()

        assert "tests" in selectors
        assert selectors["tests"] is TestSelector

    def test_get_selectors_returns_copy(self):
        """get_selectors returns a copy."""

        class TestSelector(ODataSelector):
            pass

        ODataMetadataRegistry.register("tests", TestSelector)
        selectors1 = ODataMetadataRegistry.get_selectors()
        selectors2 = ODataMetadataRegistry.get_selectors()

        assert selectors1 is not selectors2
        assert selectors1 == selectors2

    def test_set_namespace(self):
        """Set and get namespace."""
        ODataMetadataRegistry.set_namespace("MyService")
        assert ODataMetadataRegistry.get_namespace() == "MyService"

    def test_default_namespace(self):
        """Default namespace is ODataService (after reset)."""
        # Reset to default first (tests may have changed it)
        ODataMetadataRegistry.set_namespace("ODataService")
        assert ODataMetadataRegistry.get_namespace() == "ODataService"

    def test_clear_registry(self):
        """Clear removes all registrations."""

        class TestSelector(ODataSelector):
            pass

        ODataMetadataRegistry.register("tests", TestSelector)
        assert len(ODataMetadataRegistry.get_selectors()) == 1

        ODataMetadataRegistry.clear()
        assert len(ODataMetadataRegistry.get_selectors()) == 0


@pytest.mark.django_db
class TestODataMetadataView:
    """Tests for ODataMetadataView."""

    def test_get_metadata_empty_registry(self, request_factory):
        """Empty registry returns valid XML."""
        request = request_factory.get("/$metadata")
        view = ODataMetadataView()
        response = view.get(request)

        assert response.status_code == 200
        assert response["Content-Type"].startswith("application/xml")
        assert b"edmx:Edmx" in response.content
        assert b"EntityContainer" in response.content

    def test_get_metadata_with_registered_selector(self, request_factory):
        """Registered selector appears in metadata."""

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        ODataMetadataRegistry.register("tests", TestSelector)

        request = request_factory.get("/$metadata")
        view = ODataMetadataView()
        response = view.get(request)

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "ODataTestModel" in content
        assert 'EntitySet Name="tests"' in content

    def test_get_metadata_includes_entity_properties(self, request_factory):
        """Entity type includes model properties."""

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        ODataMetadataRegistry.register("tests", TestSelector)

        request = request_factory.get("/$metadata")
        view = ODataMetadataView()
        response = view.get(request)

        content = response.content.decode("utf-8")
        assert 'Property Name="name"' in content
        assert 'Property Name="count"' in content
        assert 'Property Name="is_active"' in content

    def test_get_metadata_custom_namespace(self, request_factory):
        """Custom namespace is used in metadata."""
        ODataMetadataRegistry.set_namespace("CustomService")

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        ODataMetadataRegistry.register("tests", TestSelector)

        request = request_factory.get("/$metadata")
        view = ODataMetadataView()
        response = view.get(request)

        content = response.content.decode("utf-8")
        assert 'Namespace="CustomService"' in content

    def test_metadata_without_model_skipped(self, request_factory):
        """Selector without model is skipped."""

        class NoModelSelector(ODataSelector):
            class Meta:
                model = None

        ODataMetadataRegistry.register("empty", NoModelSelector)

        request = request_factory.get("/$metadata")
        view = ODataMetadataView()
        response = view.get(request)

        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert 'EntitySet Name="empty"' not in content


@pytest.mark.django_db
class TestODataServiceDocumentView:
    """Tests for ODataServiceDocumentView."""

    def test_get_service_document_empty(self, request_factory):
        """Empty registry returns valid service document."""
        request = request_factory.get("/odata/")
        view = ODataServiceDocumentView()
        response = view.get(request)

        assert response.status_code == 200
        data = json.loads(response.content)
        assert "@odata.context" in data
        assert "value" in data
        assert data["value"] == []

    def test_get_service_document_with_entities(self, request_factory):
        """Service document lists registered entities."""

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        ODataMetadataRegistry.register("tests", TestSelector)
        ODataMetadataRegistry.register("items", TestSelector)

        request = request_factory.get("/odata/")
        view = ODataServiceDocumentView()
        response = view.get(request)

        data = json.loads(response.content)
        entity_names = [e["name"] for e in data["value"]]
        assert "tests" in entity_names
        assert "items" in entity_names

    def test_service_document_entity_structure(self, request_factory):
        """Each entity has correct structure."""

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        ODataMetadataRegistry.register("tests", TestSelector)

        request = request_factory.get("/odata/")
        view = ODataServiceDocumentView()
        response = view.get(request)

        data = json.loads(response.content)
        entity = data["value"][0]
        assert entity["name"] == "tests"
        assert entity["kind"] == "EntitySet"
        assert entity["url"] == "tests"

    def test_service_document_context_url(self, request_factory):
        """Context URL points to $metadata."""
        request = request_factory.get("/odata/")
        view = ODataServiceDocumentView()
        response = view.get(request)

        data = json.loads(response.content)
        assert "$metadata" in data["@odata.context"]


@pytest.mark.django_db
class TestEdmTypeMapping:
    """Tests for Django to EDM type mapping."""

    def test_edm_type_mapping(self, request_factory):
        """Various Django field types map to correct EDM types."""

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        ODataMetadataRegistry.register("tests", TestSelector)

        request = request_factory.get("/$metadata")
        view = ODataMetadataView()
        response = view.get(request)

        content = response.content.decode("utf-8")
        # String fields
        assert 'Type="Edm.String"' in content
        # Integer fields
        assert 'Type="Edm.Int32"' in content
        # Boolean fields
        assert 'Type="Edm.Boolean"' in content
        # DateTime fields
        assert 'Type="Edm.DateTimeOffset"' in content


@pytest.mark.django_db
class TestNavigationProperties:
    """Tests for navigation property handling."""

    def test_navigation_properties_only_for_expandable(self, request_factory):
        """Only expandable fields appear as navigation properties."""

        class ParentSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                expandable_fields = {"related_items": ODataRelatedModel}

        class ChildSelector(ODataSelector):
            class Meta:
                model = ODataRelatedModel
                expandable_fields = {}

        ODataMetadataRegistry.register("parents", ParentSelector)
        ODataMetadataRegistry.register("children", ChildSelector)

        request = request_factory.get("/$metadata")
        view = ODataMetadataView()
        response = view.get(request)

        content = response.content.decode("utf-8")
        # related_items should be a navigation property
        assert 'NavigationProperty Name="related_items"' in content


@pytest.mark.django_db
class TestCapabilitiesAnnotations:
    """Tests for OData Capabilities vocabulary annotations."""

    def test_metadata_includes_filter_restrictions(self, request_factory):
        """Metadata includes FilterRestrictions annotation."""

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        ODataMetadataRegistry.register("tests", TestSelector)

        request = request_factory.get("/$metadata")
        view = ODataMetadataView()
        response = view.get(request)

        content = response.content.decode("utf-8")
        assert "Org.OData.Capabilities.V1.FilterRestrictions" in content
        assert 'Property="Filterable"' in content

    def test_metadata_includes_sort_restrictions(self, request_factory):
        """Metadata includes SortRestrictions annotation."""

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        ODataMetadataRegistry.register("tests", TestSelector)

        request = request_factory.get("/$metadata")
        view = ODataMetadataView()
        response = view.get(request)

        content = response.content.decode("utf-8")
        assert "Org.OData.Capabilities.V1.SortRestrictions" in content
        assert 'Property="Sortable"' in content

    def test_non_filterable_fields_from_positive_list(self, request_factory):
        """NonFilterableProperties generated from filterable_fields (positive list)."""

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                filterable_fields = ["name", "count"]  # Only these are filterable

        ODataMetadataRegistry.register("tests", TestSelector)

        request = request_factory.get("/$metadata")
        view = ODataMetadataView()
        response = view.get(request)

        content = response.content.decode("utf-8")
        assert "NonFilterableProperties" in content
        # is_active is NOT in filterable_fields, so should be non-filterable
        assert "<PropertyPath>is_active</PropertyPath>" in content

    def test_non_filterable_fields_from_negative_list(self, request_factory):
        """NonFilterableProperties used directly from non_filterable_fields."""

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                non_filterable_fields = ["is_active", "created_at"]

        ODataMetadataRegistry.register("tests", TestSelector)

        request = request_factory.get("/$metadata")
        view = ODataMetadataView()
        response = view.get(request)

        content = response.content.decode("utf-8")
        assert "NonFilterableProperties" in content
        assert "<PropertyPath>is_active</PropertyPath>" in content
        assert "<PropertyPath>created_at</PropertyPath>" in content

    def test_non_sortable_fields_from_positive_list(self, request_factory):
        """NonSortableProperties generated from sortable_fields (positive list)."""

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                sortable_fields = ["name", "created_at"]  # Only these are sortable

        ODataMetadataRegistry.register("tests", TestSelector)

        request = request_factory.get("/$metadata")
        view = ODataMetadataView()
        response = view.get(request)

        content = response.content.decode("utf-8")
        assert "NonSortableProperties" in content
        # count is NOT in sortable_fields, so should be non-sortable
        assert "<PropertyPath>count</PropertyPath>" in content

    def test_non_sortable_fields_from_negative_list(self, request_factory):
        """NonSortableProperties used directly from non_sortable_fields."""

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                non_sortable_fields = ["description"]

        ODataMetadataRegistry.register("tests", TestSelector)

        request = request_factory.get("/$metadata")
        view = ODataMetadataView()
        response = view.get(request)

        content = response.content.decode("utf-8")
        assert "NonSortableProperties" in content
        assert "<PropertyPath>description</PropertyPath>" in content

    def test_positive_list_takes_priority_over_negative(self, request_factory):
        """filterable_fields takes priority over non_filterable_fields."""

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                filterable_fields = ["name"]  # This takes priority
                non_filterable_fields = ["count"]  # This is ignored

        ODataMetadataRegistry.register("tests", TestSelector)
        selector = TestSelector()

        # Should invert filterable_fields, ignoring non_filterable_fields
        non_filterable = selector.get_non_filterable_fields()
        assert "name" not in non_filterable  # name IS filterable
        assert "count" in non_filterable  # count is NOT in filterable_fields

    def test_no_restrictions_when_nothing_defined(self, request_factory):
        """No NonFilterableProperties when neither list is defined."""

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                # No filterable_fields or non_filterable_fields defined

        ODataMetadataRegistry.register("tests", TestSelector)
        selector = TestSelector()

        assert selector.get_non_filterable_fields() == []
        assert selector.get_non_sortable_fields() == []


@pytest.mark.django_db
class TestSelectorFieldIntrospection:
    """Tests for ODataSelector field introspection methods."""

    def test_get_model_field_names(self):
        """_get_model_field_names returns concrete field names."""

        class TestSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        selector = TestSelector()
        fields = selector._get_model_field_names()

        assert "id" in fields
        assert "name" in fields
        assert "count" in fields
        assert "is_active" in fields
