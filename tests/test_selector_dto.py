"""
Tests for ODataSelector with automatic DTO conversion.
"""

from dataclasses import dataclass

import pytest
from django.utils import timezone

from fc_selector.core.dtos import UNSET, BaseODataDTO
from tests.integration.support.models import ODataRelatedModel, ODataTestModel


@dataclass
class ODataRelatedDTO(BaseODataDTO):
    """Test DTO for ODataRelatedModel."""

    id: int = UNSET
    title: str = UNSET
    value: int = UNSET
    test_model_id: int = UNSET


@dataclass
class ODataTestDTO(BaseODataDTO):
    """Test DTO for ODataTestModel."""

    id: int = UNSET
    name: str = UNSET
    description: str = UNSET
    count: int = UNSET
    rating: float = UNSET
    is_active: bool = UNSET
    status: str = UNSET
    related_items: list[ODataRelatedDTO] | None = UNSET


@pytest.mark.django_db
class TestBaseODataDTO:
    """Tests for BaseODataDTO automatic conversion."""

    def test_from_model_all_fields(self):
        """Test converting model to DTO with all fields."""

        test_obj = ODataTestModel.objects.create(
            name="Test Object",
            description="Test Description",
            count=10,
            rating=4.5,
            is_active=True,
            status="published",
            created_at=timezone.now(),
        )

        dto = ODataTestDTO.from_model(test_obj)

        assert dto.id == test_obj.id
        assert dto.name == test_obj.name
        assert dto.description == test_obj.description
        assert dto.count == test_obj.count
        assert dto.status == test_obj.status

    def test_from_model_selected_fields(self):
        """Test converting model with $select (only specific fields)."""

        test_obj = ODataTestModel.objects.create(
            name="Test Object",
            description="Test Description",
            count=10,
            created_at=timezone.now(),
        )

        dto = ODataTestDTO.from_model(test_obj, selected_fields={"id", "name"})

        # Selected fields should have values
        assert dto.id == test_obj.id
        assert dto.name == test_obj.name

        # Unselected fields should be UNSET
        assert dto.description is UNSET
        assert dto.count is UNSET
        assert dto.status is UNSET

    def test_from_model_expanded_many_relationship(self):
        """Test converting model with $expand for one-to-many relationship."""

        test_obj = ODataTestModel.objects.create(name="Test Object", count=5, created_at=timezone.now())

        # Create related items
        ODataRelatedModel.objects.create(test_model=test_obj, title="Related 1", value=100)
        ODataRelatedModel.objects.create(test_model=test_obj, title="Related 2", value=200)

        dto = ODataTestDTO.from_model(test_obj, expanded_fields={"related_items"})

        # Related items should be list of DTOs
        assert isinstance(dto.related_items, list)
        assert len(dto.related_items) == 2

        for related_dto in dto.related_items:
            assert isinstance(related_dto, ODataRelatedDTO)
            assert hasattr(related_dto, "id")
            assert hasattr(related_dto, "title")

    def test_from_model_selected_and_expanded(self):
        """Test combining $select and $expand."""

        test_obj = ODataTestModel.objects.create(
            name="Test Object",
            description="Description",
            count=10,
            created_at=timezone.now(),
        )

        ODataRelatedModel.objects.create(test_model=test_obj, title="Related", value=100)

        dto = ODataTestDTO.from_model(
            test_obj,
            selected_fields={"id", "name", "related_items"},
            expanded_fields={"related_items"},
        )

        # Selected regular fields
        assert dto.id == test_obj.id
        assert dto.name == test_obj.name

        # Unselected regular fields
        assert dto.description is UNSET
        assert dto.count is UNSET

        # Selected and expanded relationship
        assert isinstance(dto.related_items, list)
        assert len(dto.related_items) == 1
        assert isinstance(dto.related_items[0], ODataRelatedDTO)

    def test_sentinel_representation(self):
        """Test that UNSET sentinel has correct representation."""
        assert repr(UNSET) == "<UNSET>"

    def test_automatic_relationship_detection(self):
        """Test that relationships are automatically detected via type hints."""

        test_obj = ODataTestModel.objects.create(name="Test Object", count=10, created_at=timezone.now())

        dto = ODataTestDTO.from_model(test_obj, selected_fields={"id", "name", "related_items"})

        # Regular fields should have values
        assert dto.id == test_obj.id
        assert dto.name == test_obj.name

        # Relationships not expanded should be UNSET (not None)
        assert dto.related_items is UNSET  # One-to-many not expanded
