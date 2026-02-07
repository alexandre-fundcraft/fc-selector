"""
Tests for DTO utilities.
"""

import dataclasses

from fc_selector.core.dtos.utils import get_dto_fields


class MockDTOWithInternalMethod:
    """Mock DTO with _get_dto_fields method."""

    @classmethod
    def _get_dto_fields(cls):
        yield "field1"
        yield "field2"


class MockDTOWithAnnotations:
    """Mock DTO with __annotations__ but not dataclass."""
    name: str
    age: int


@dataclasses.dataclass
class MockDataclassDTO:
    """Mock dataclass DTO."""
    id: int
    title: str


class MockEmptyDTO:
    """Mock DTO with nothing."""
    pass


def test_get_dto_fields_with_internal_method():
    """Test get_dto_fields with _get_dto_fields."""
    fields = get_dto_fields(MockDTOWithInternalMethod)
    assert fields == ["field1", "field2"]


def test_get_dto_fields_with_annotations():
    """Test get_dto_fields with __annotations__."""
    fields = get_dto_fields(MockDTOWithAnnotations)
    assert "name" in fields
    assert "age" in fields


def test_get_dto_fields_with_dataclass():
    """Test get_dto_fields with dataclass."""
    fields = get_dto_fields(MockDataclassDTO)
    assert "id" in fields
    assert "title" in fields


def test_get_dto_fields_empty():
    """Test get_dto_fields with empty class."""
    fields = get_dto_fields(MockEmptyDTO)
    assert fields == []


def test_get_dto_fields_none():
    """Test get_dto_fields with None."""
    fields = get_dto_fields(None)
    assert fields == []
