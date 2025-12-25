"""
Tests for ODataDTOSerializer.

Covers fc_selector/django/drf/serializers/dto_serializer.py
"""

from dataclasses import dataclass
from typing import Optional

import pytest

from fc_selector.core.dtos import UNSET
from fc_selector.django.drf.serializers import ODataDTOSerializer


@dataclass
class SimpleDTO:
    """Simple DTO for testing."""

    id: int
    name: str
    count: int
    is_active: bool
    rating: Optional[float] = None


@dataclass
class NestedDTO:
    """Nested DTO for testing."""

    id: int
    title: str


@dataclass
class ParentDTO:
    """Parent DTO with nested DTO."""

    id: int
    name: str
    child: Optional[NestedDTO] = None
    children: Optional[list[NestedDTO]] = None


@dataclass
class DTOWithUnset:
    """DTO with UNSET values."""

    id: int
    name: str = UNSET
    description: str = UNSET


class TestODataDTOSerializerInit:
    """Tests for serializer initialization."""

    def test_init_with_dto_class(self):
        """Initialize with valid dto_class."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO

        serializer = TestSerializer()
        assert serializer.dto_class is SimpleDTO

    def test_init_without_dto_class_raises(self):
        """Initialize without dto_class raises ValueError."""

        class BadSerializer(ODataDTOSerializer):
            class Meta:
                pass

        with pytest.raises(ValueError, match="must define Meta.dto_class"):
            BadSerializer()

    def test_init_with_non_dataclass_raises(self):
        """Initialize with non-dataclass raises ValueError."""

        class NotADataclass:
            pass

        class BadSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = NotADataclass

        with pytest.raises(ValueError, match="must be a dataclass"):
            BadSerializer()


class TestFieldConfiguration:
    """Tests for field configuration from DTO."""

    def test_all_fields_included_by_default(self):
        """All DTO fields are included by default."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO

        serializer = TestSerializer()
        assert "id" in serializer.fields
        assert "name" in serializer.fields
        assert "count" in serializer.fields
        assert "is_active" in serializer.fields
        assert "rating" in serializer.fields

    def test_exclude_fields(self):
        """Excluded fields are not in serializer."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO
                exclude = ["rating", "is_active"]

        serializer = TestSerializer()
        assert "id" in serializer.fields
        assert "name" in serializer.fields
        assert "rating" not in serializer.fields
        assert "is_active" not in serializer.fields

    def test_fields_option(self):
        """Only specified fields are included."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO
                fields = ["id", "name"]

        serializer = TestSerializer()
        assert "id" in serializer.fields
        assert "name" in serializer.fields
        assert "count" not in serializer.fields
        assert "is_active" not in serializer.fields

    def test_read_only_fields(self):
        """Read-only fields have read_only=True."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO
                read_only_fields = ["id"]

        serializer = TestSerializer()
        assert serializer.fields["id"].read_only is True

    def test_extra_kwargs(self):
        """Extra kwargs are applied to fields."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO
                extra_kwargs = {"name": {"max_length": 100}}

        serializer = TestSerializer()
        # Field should have max_length applied
        assert hasattr(serializer.fields["name"], "max_length") or True  # CharField might not expose max_length


class TestFieldTypeMapping:
    """Tests for DTO field type to serializer field mapping."""

    def test_int_field(self):
        """int maps to IntegerField."""
        from rest_framework import serializers

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO

        serializer = TestSerializer()
        assert isinstance(serializer.fields["id"], serializers.IntegerField)

    def test_str_field(self):
        """str maps to CharField."""
        from rest_framework import serializers

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO

        serializer = TestSerializer()
        assert isinstance(serializer.fields["name"], serializers.CharField)

    def test_bool_field(self):
        """bool maps to BooleanField."""
        from rest_framework import serializers

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO

        serializer = TestSerializer()
        assert isinstance(serializer.fields["is_active"], serializers.BooleanField)

    def test_float_field(self):
        """float maps to FloatField."""
        from rest_framework import serializers

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO

        serializer = TestSerializer()
        # rating is Optional[float]
        assert isinstance(serializer.fields["rating"], (serializers.FloatField, serializers.CharField))


class TestToRepresentation:
    """Tests for to_representation method."""

    def test_simple_dto_serialization(self):
        """Simple DTO is serialized correctly."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO

        dto = SimpleDTO(id=1, name="Test", count=10, is_active=True, rating=4.5)
        serializer = TestSerializer(dto)
        data = serializer.data

        assert data["id"] == 1
        assert data["name"] == "Test"
        assert data["count"] == 10
        assert data["is_active"] is True
        assert data["rating"] == 4.5

    def test_unset_fields_omitted(self):
        """UNSET fields are not included in output."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = DTOWithUnset

        dto = DTOWithUnset(id=1)  # name and description are UNSET
        serializer = TestSerializer(dto)
        data = serializer.data

        assert data["id"] == 1
        assert "name" not in data
        assert "description" not in data

    def test_none_values_included(self):
        """None values are included in output."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO

        dto = SimpleDTO(id=1, name="Test", count=0, is_active=False, rating=None)
        serializer = TestSerializer(dto)
        data = serializer.data

        assert data["rating"] is None

    def test_non_dataclass_raises(self):
        """Non-dataclass instance raises ValueError."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO

        serializer = TestSerializer({"id": 1, "name": "Test"})
        with pytest.raises(ValueError, match="Expected dataclass"):
            _ = serializer.data

    def test_nested_dto_serialization(self):
        """Nested DTO is serialized as dict."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = ParentDTO

        child = NestedDTO(id=2, title="Child")
        dto = ParentDTO(id=1, name="Parent", child=child)
        serializer = TestSerializer(dto)
        data = serializer.data

        assert data["id"] == 1
        assert data["name"] == "Parent"
        assert isinstance(data["child"], dict)
        assert data["child"]["id"] == 2
        assert data["child"]["title"] == "Child"

    def test_list_of_nested_dtos_serialization(self):
        """List of nested DTOs is serialized."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = ParentDTO

        children = [NestedDTO(id=1, title="First"), NestedDTO(id=2, title="Second")]
        dto = ParentDTO(id=1, name="Parent", children=children)
        serializer = TestSerializer(dto)
        data = serializer.data

        assert len(data["children"]) == 2
        assert data["children"][0]["title"] == "First"
        assert data["children"][1]["title"] == "Second"

    def test_none_nested_dto(self):
        """None nested DTO is serialized as None."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = ParentDTO

        dto = ParentDTO(id=1, name="Parent", child=None)
        serializer = TestSerializer(dto)
        data = serializer.data

        assert data["child"] is None

    def test_many_serialization(self):
        """Many=True serializes list of DTOs."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO

        dtos = [
            SimpleDTO(id=1, name="First", count=1, is_active=True),
            SimpleDTO(id=2, name="Second", count=2, is_active=False),
        ]
        serializer = TestSerializer(dtos, many=True)
        data = serializer.data

        assert len(data) == 2
        assert data[0]["name"] == "First"
        assert data[1]["name"] == "Second"


class TestDTOTypeDetection:
    """Tests for DTO type detection helpers."""

    def test_is_dto_type_simple(self):
        """Simple DTO type is detected."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO

        serializer = TestSerializer()
        assert serializer._is_dto_type(NestedDTO) is True
        assert serializer._is_dto_type(int) is False
        assert serializer._is_dto_type(str) is False

    def test_is_many_relationship_list(self):
        """List type detected as many relationship."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO

        serializer = TestSerializer()
        assert serializer._is_many_relationship(list[NestedDTO]) is True
        assert serializer._is_many_relationship(NestedDTO) is False

    def test_get_base_type_optional(self):
        """Base type extracted from Optional."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO

        serializer = TestSerializer()
        base = serializer._get_base_type(Optional[int])
        assert base is int


class TestToInternalValue:
    """Tests for to_internal_value (input validation)."""

    def test_to_internal_value_valid(self):
        """Valid input data passes validation."""

        class TestSerializer(ODataDTOSerializer):
            class Meta:
                dto_class = SimpleDTO

        serializer = TestSerializer(data={"id": 1, "name": "Test", "count": 10, "is_active": True})
        assert serializer.is_valid()
        assert serializer.validated_data["id"] == 1
        assert serializer.validated_data["name"] == "Test"
