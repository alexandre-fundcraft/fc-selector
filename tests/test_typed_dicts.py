"""Tests for the auto-generated TypedDict via DTO.__td__."""

from dataclasses import dataclass
from typing import Optional, get_args, get_origin

import pytest

from fc_selector.core.dtos.base import UNSET, BaseODataDTO

# ── Test DTOs ─────────────────────────────────────────────────


@dataclass
class SimpleDTO(BaseODataDTO):
    id: int = UNSET
    name: str = UNSET
    count: int = UNSET


@dataclass
class NestedChildDTO(BaseODataDTO):
    id: int = UNSET
    label: str = UNSET


@dataclass
class ParentDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET
    child: Optional[NestedChildDTO] = UNSET


@dataclass
class ParentWithListDTO(BaseODataDTO):
    id: int = UNSET
    children: list[NestedChildDTO] | None = UNSET


@dataclass
class CircularADTO(BaseODataDTO):
    id: int = UNSET
    b: Optional["CircularBDTO"] = UNSET


@dataclass
class CircularBDTO(BaseODataDTO):
    id: int = UNSET
    a: Optional[CircularADTO] = UNSET


@dataclass
class NonDTOSuffix(BaseODataDTO):
    """DTO whose name does NOT end in 'DTO'."""

    id: int = UNSET
    value: float = UNSET


# ── Tests ─────────────────────────────────────────────────────


class TestTypedDictGeneration:
    def test_simple_dto_annotations(self):
        td = SimpleDTO.__td__
        assert td.__annotations__["id"] is int
        assert td.__annotations__["name"] is str
        assert td.__annotations__["count"] is int

    def test_simple_dto_total_false(self):
        td = SimpleDTO.__td__
        # total=False means all keys are optional
        assert td.__total__ is False

    def test_simple_dto_naming(self):
        td = SimpleDTO.__td__
        assert td.__name__ == "SimpleDict"

    def test_non_dto_suffix_naming(self):
        td = NonDTOSuffix.__td__
        assert td.__name__ == "NonDTOSuffixDict"

    def test_nested_dto_resolved(self):
        td = ParentDTO.__td__
        child_td = NestedChildDTO.__td__
        # The 'child' field should reference the child TypedDict, not the DTO
        child_annotation = td.__annotations__["child"]
        # Optional[NestedChildDict] → Union[NestedChildDict, None]
        args = get_args(child_annotation)
        assert child_td in args
        assert type(None) in args

    def test_list_of_dtos_resolved(self):
        td = ParentWithListDTO.__td__
        child_td = NestedChildDTO.__td__
        children_type = td.__annotations__["children"]
        # list[NestedChildDict] | None → Union[list[NestedChildDict], None]
        union_args = get_args(children_type)
        list_type = [a for a in union_args if a is not type(None)][0]
        assert get_origin(list_type) is list
        assert get_args(list_type) == (child_td,)

    def test_caching(self):
        td1 = SimpleDTO.__td__
        td2 = SimpleDTO.__td__
        assert td1 is td2

    def test_circular_reference_no_infinite_loop(self):
        """Circular DTOs should not cause infinite recursion."""
        td_a = CircularADTO.__td__
        assert td_a.__name__ == "CircularADict"
        # The circular reference should fall back to plain dict
        assert td_a.__annotations__["id"] is int

    def test_base_class_raises(self):
        with pytest.raises(AttributeError, match="only available on"):
            _ = BaseODataDTO.__td__

    def test_generated_td_is_proper_typeddict(self):
        """The generated class should behave as a TypedDict (regular dict at runtime)."""
        td = SimpleDTO.__td__
        # TypedDicts are subclasses of dict at the type level
        instance = td(id=1, name="test", count=5)
        assert instance["id"] == 1
        assert instance["name"] == "test"
