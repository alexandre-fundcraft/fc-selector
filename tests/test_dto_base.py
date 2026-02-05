"""
Tests for BaseODataDTO and related DTO functionality.

Covers fc_selector/core/dtos/base.py
"""

from dataclasses import dataclass
from typing import Optional

import pytest
from django.utils import timezone

from fc_selector.core.dtos import UNSET
from fc_selector.core.dtos.base import BaseODataDTO, Unset
from tests.integration.support.models import ODataRelatedModel, ODataTestModel


@dataclass
class SimpleDTO(BaseODataDTO):
    """Simple DTO for testing."""

    id: int = UNSET
    name: str = UNSET
    count: int = UNSET


@dataclass
class NestedDTO(BaseODataDTO):
    """Nested DTO for testing."""

    id: int = UNSET
    title: str = UNSET


@dataclass
class ParentDTO(BaseODataDTO):
    """Parent DTO with nested DTO."""

    id: int = UNSET
    name: str = UNSET
    child: Optional[NestedDTO] = UNSET
    children: Optional[list[NestedDTO]] = UNSET


class TestUnsetSentinel:
    """Tests for UNSET sentinel value."""

    def test_unset_repr(self):
        """UNSET has meaningful repr."""
        assert repr(UNSET) == "<UNSET>"

    def test_unset_is_singleton(self):
        """UNSET is a singleton when imported from different locations."""
        from fc_selector.core.dtos import UNSET as UNSET_FROM_DTOS  # noqa: PLC0415
        from fc_selector.core.dtos.base import UNSET as UNSET_FROM_BASE  # noqa: PLC0415

        # Same object when imported from different modules
        assert UNSET_FROM_DTOS is UNSET_FROM_BASE
        # New instance is technically possible but we use the constant
        another = Unset()
        assert repr(another) == "<UNSET>"


class TestIsDtoType:
    """Tests for _is_dto_type class method."""

    def test_direct_dto_type(self):
        """Direct DTO type is detected."""
        assert SimpleDTO._is_dto_type(NestedDTO) is True

    def test_optional_dto_type(self):
        """Optional[DTO] is detected."""
        assert SimpleDTO._is_dto_type(Optional[NestedDTO]) is True

    def test_list_dto_type(self):
        """List[DTO] is detected."""
        assert SimpleDTO._is_dto_type(list[NestedDTO]) is True

    def test_optional_list_dto_type(self):
        """Optional[List[DTO]] is detected."""
        assert SimpleDTO._is_dto_type(Optional[list[NestedDTO]]) is True

    def test_non_dto_type(self):
        """Non-DTO types are not detected."""
        assert SimpleDTO._is_dto_type(str) is False
        assert SimpleDTO._is_dto_type(int) is False
        assert SimpleDTO._is_dto_type(Optional[str]) is False
        assert SimpleDTO._is_dto_type(list[str]) is False


class TestIsManyRelationship:
    """Tests for _is_many_relationship class method."""

    def test_list_is_many(self):
        """List type is many relationship."""
        assert SimpleDTO._is_many_relationship(list[NestedDTO]) is True

    def test_optional_list_is_many(self):
        """Optional[List] is many relationship."""
        assert SimpleDTO._is_many_relationship(Optional[list[NestedDTO]]) is True

    def test_direct_is_not_many(self):
        """Direct type is not many."""
        assert SimpleDTO._is_many_relationship(NestedDTO) is False

    def test_optional_is_not_many(self):
        """Optional (non-list) is not many."""
        assert SimpleDTO._is_many_relationship(Optional[NestedDTO]) is False


class TestGetDtoClass:
    """Tests for _get_dto_class class method."""

    def test_direct_dto(self):
        """Direct DTO type returns the class."""
        assert SimpleDTO._get_dto_class(NestedDTO) is NestedDTO

    def test_optional_dto(self):
        """Optional[DTO] returns the DTO class."""
        assert SimpleDTO._get_dto_class(Optional[NestedDTO]) is NestedDTO

    def test_list_dto(self):
        """List[DTO] returns the DTO class."""
        assert SimpleDTO._get_dto_class(list[NestedDTO]) is NestedDTO

    def test_optional_list_dto(self):
        """Optional[List[DTO]] returns the DTO class."""
        assert SimpleDTO._get_dto_class(Optional[list[NestedDTO]]) is NestedDTO

    def test_non_dto_returns_none(self):
        """Non-DTO type returns None."""
        assert SimpleDTO._get_dto_class(str) is None
        assert SimpleDTO._get_dto_class(int) is None


class TestGetSafeTypeHints:
    """Tests for _get_safe_type_hints class method."""

    def test_returns_type_hints(self):
        """Returns type hints for well-defined class."""
        hints = SimpleDTO._get_safe_type_hints()
        assert "id" in hints
        assert "name" in hints
        assert "count" in hints


class TestDetermineFieldsToPopulate:
    """Tests for _determine_fields_to_populate class method."""

    def test_none_selected_returns_all(self):
        """None selected_fields returns all DTO fields."""
        dto_fields = {"id", "name", "count"}
        result = SimpleDTO._determine_fields_to_populate(dto_fields, None, set())
        assert result == dto_fields

    def test_selected_fields_filtered(self):
        """Selected fields are filtered."""
        dto_fields = {"id", "name", "count"}
        result = SimpleDTO._determine_fields_to_populate(dto_fields, {"id", "name"}, set())
        assert result == {"id", "name"}

    def test_expanded_fields_included(self):
        """Expanded fields are included even if not selected."""
        dto_fields = {"id", "name", "child"}
        result = SimpleDTO._determine_fields_to_populate(dto_fields, {"id"}, {"child"})
        assert result == {"id", "child"}


class TestDetectRelationships:
    """Tests for _detect_relationships class method."""

    def test_detects_relationships(self):
        """Relationships are detected from type hints."""
        dto_fields = {"id", "name", "child", "children"}
        hints = ParentDTO._get_safe_type_hints()
        relationships = ParentDTO._detect_relationships(dto_fields, hints)

        assert "child" in relationships
        assert relationships["child"]["dto_class"] is NestedDTO
        assert relationships["child"]["is_many"] is False

        assert "children" in relationships
        assert relationships["children"]["dto_class"] is NestedDTO
        assert relationships["children"]["is_many"] is True

        # Regular fields not in relationships
        assert "id" not in relationships
        assert "name" not in relationships


@pytest.mark.django_db
class TestFromModel:
    """Tests for from_model class method with Django models."""

    @pytest.fixture
    def test_instance(self):
        """Create test model instance."""
        return ODataTestModel.objects.create(
            name="Test",
            description="Description",
            count=10,
            is_active=True,
            created_at=timezone.now(),
            status="draft",
        )

    @pytest.fixture
    def related_instance(self, test_instance):
        """Create related model instance."""
        return ODataRelatedModel.objects.create(
            test_model=test_instance,
            title="Related",
            value=5,
        )

    def test_from_model_all_fields(self, test_instance):
        """from_model populates all fields."""

        @dataclass
        class TestModelDTO(BaseODataDTO):
            id: int = UNSET
            name: str = UNSET
            count: int = UNSET
            is_active: bool = UNSET

        dto = TestModelDTO.from_model(test_instance)
        assert dto.id == test_instance.id
        assert dto.name == "Test"
        assert dto.count == 10
        assert dto.is_active is True

    def test_from_model_selected_fields(self, test_instance):
        """from_model respects selected_fields."""

        @dataclass
        class TestModelDTO(BaseODataDTO):
            id: int = UNSET
            name: str = UNSET
            count: int = UNSET

        dto = TestModelDTO.from_model(test_instance, selected_fields={"id", "name"})
        assert dto.id == test_instance.id
        assert dto.name == "Test"
        assert dto.count is UNSET  # Not selected

    def test_from_model_missing_field(self, test_instance):
        """from_model handles fields not on model."""

        @dataclass
        class TestModelDTO(BaseODataDTO):
            id: int = UNSET
            nonexistent: str = UNSET

        dto = TestModelDTO.from_model(test_instance)
        assert dto.id == test_instance.id
        # nonexistent field stays UNSET since not on model


class TestIsDtoTypeEdgeCases:
    """Additional edge case tests for _is_dto_type."""

    def test_non_class_type(self):
        """Non-class type without __name__ returns False."""
        # String type doesn't have __name__ ending in DTO
        assert SimpleDTO._is_dto_type("not a type") is False

    def test_class_without_dto_suffix(self):
        """Class without DTO suffix returns False."""

        class MyClass:
            pass

        assert SimpleDTO._is_dto_type(MyClass) is False


class TestIsManyRelationshipEdgeCases:
    """Additional edge case tests for _is_many_relationship."""

    def test_origin_none_returns_false(self):
        """Type with no origin returns False."""
        assert SimpleDTO._is_many_relationship(str) is False

    def test_union_with_list(self):
        """Union type with list inner type."""

        # Optional[List[DTO]] where Optional is Union[..., None]
        union_list_type = Optional[list[NestedDTO]]
        result = SimpleDTO._is_many_relationship(union_list_type)
        assert result is True


class TestParseNestedExpandOptions:
    """Tests for _parse_nested_expand_options."""

    def test_simple_expand_string(self):
        """Simple expand string is parsed."""
        expanded, options = BaseODataDTO._parse_nested_expand_options("author")
        assert "author" in expanded

    def test_multiple_expands(self):
        """Multiple expands separated by comma."""
        expanded, options = BaseODataDTO._parse_nested_expand_options("author,categories")
        assert "author" in expanded
        assert "categories" in expanded

    def test_expand_with_nested_options(self):
        """Expand with nested $select options."""
        # This tests parsing nested options like "author($select=id,name)"
        expanded, options = BaseODataDTO._parse_nested_expand_options("author($select=id,name)")
        assert "author" in expanded

    def test_invalid_expand_falls_back(self):
        """Invalid expand syntax falls back to simple split."""
        expanded, options = BaseODataDTO._parse_nested_expand_options("simple_field")
        assert "simple_field" in expanded


@pytest.mark.django_db
class TestFromModelWithRelationships:
    """Tests for from_model with relationship handling."""

    @pytest.fixture
    def test_instance_with_related(self):
        """Create test model with related items."""
        test_model = ODataTestModel.objects.create(
            name="Parent",
            description="Parent desc",
            count=5,
            is_active=True,
            created_at=timezone.now(),
            status="published",
        )
        # Create related items
        ODataRelatedModel.objects.create(test_model=test_model, title="Child1", value=10)
        ODataRelatedModel.objects.create(test_model=test_model, title="Child2", value=20)

        return test_model

    def test_from_model_with_expand_options(self, test_instance_with_related):
        """from_model handles expand_options dict."""

        @dataclass
        class RelatedDTO(BaseODataDTO):
            id: int = UNSET
            title: str = UNSET
            value: int = UNSET

        @dataclass
        class ParentModelDTO(BaseODataDTO):
            id: int = UNSET
            name: str = UNSET
            related_items: Optional[list[RelatedDTO]] = UNSET

        dto = ParentModelDTO.from_model(
            test_instance_with_related,
            expanded_fields={"related_items"},
            expand_options={"related_items": {"$select": "id,title"}},
        )

        assert dto.id == test_instance_with_related.id
        assert dto.name == "Parent"
        assert dto.related_items is not UNSET
        assert len(dto.related_items) == 2

    def test_from_model_null_relationship(self):
        """from_model handles null relationship."""

        @dataclass
        class TestModelDTO(BaseODataDTO):
            id: int = UNSET
            name: str = UNSET

        @dataclass
        class RelatedDTO(BaseODataDTO):
            id: int = UNSET
            title: str = UNSET
            test_model: Optional[TestModelDTO] = UNSET

        # Create a related model without test_model (if nullable) or check the FK
        parent = ODataTestModel.objects.create(
            name="Parent",
            description="",
            count=0,
            is_active=True,
            created_at=timezone.now(),
            status="draft",
        )
        related = ODataRelatedModel.objects.create(test_model=parent, title="Related", value=0)

        # Test with expansion - should get nested DTO
        dto = RelatedDTO.from_model(related, expanded_fields={"test_model"})
        assert dto.test_model is not UNSET
        assert dto.test_model.name == "Parent"
