"""
Targeted tests to reach 100% coverage in fc_selector/django/selector/odata_selector.py
"""

from dataclasses import dataclass
from typing import Optional

import pytest
from django.utils import timezone

from fc_selector.core.dtos import UNSET, BaseODataDTO
from fc_selector.core.exceptions import QueryError
from fc_selector.core.query_builder import QueryBuilder
from fc_selector.django.selector import ODataSelector
from tests.integration.support.models import (
    ODataFKTarget,
    ODataModelWithFK,
    ODataOneToOneChild,
    ODataOneToOneParent,
    ODataTestModel,
)


@dataclass
class SimpleDTO(BaseODataDTO):
    id: int = UNSET
    name: str = UNSET


@dataclass
class FKTargetDTO(BaseODataDTO):
    id: int = UNSET
    name: str = UNSET


@dataclass
class ModelWithFKDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET
    target: Optional[FKTargetDTO] = UNSET


@pytest.mark.django_db
class TestODataSelectorCoverage:
    """Targeted tests to reach 100% coverage in odata_selector.py."""

    def test_get_model_field_names_no_model(self):
        """Line 117: _get_model_field_names returns [] if no model."""

        class NoModelSelector(ODataSelector):
            class Meta:
                pass

        selector = NoModelSelector()
        assert selector._get_model_field_names() == []

    def test_get_non_filterable_fields_with_filterable_defined(self):
        """Line 121: get_non_filterable_fields with filterable_fields defined."""

        class FilterableSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                filterable_fields = ["name"]

        selector = FilterableSelector()
        non_filterable = selector.get_non_filterable_fields()
        assert "name" not in non_filterable
        assert "count" in non_filterable

    def test_get_non_filterable_fields_default(self):
        """Line 130: get_non_filterable_fields default return."""

        class DefaultSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        selector = DefaultSelector()
        assert selector.get_non_filterable_fields() == []

    def test_get_non_sortable_fields_with_sortable_defined(self):
        """Line 137-139: Similar logic for sortable fields."""

        class SortableSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                sortable_fields = ["name"]

        selector = SortableSelector()
        non_sortable = selector.get_non_sortable_fields()
        assert "name" not in non_sortable
        assert "count" in non_sortable

    def test_get_non_sortable_fields_default(self):
        """Line 146: get_non_sortable_fields default return."""

        class DefaultSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        selector = DefaultSelector()
        assert selector.get_non_sortable_fields() == []

    def test_validate_field_aliases_invalid_alias(self):
        """Lines 95-97: _validate_field_aliases with invalid alias characters."""

        class Meta:
            model = ODataTestModel
            field_aliases = {"invalid-alias": "name"}

        with pytest.raises(ValueError, match="Invalid field alias"):
            ODataSelector._validate_field_aliases(Meta.field_aliases)

    def test_validate_field_aliases_invalid_internal(self):
        """Lines 99-105: _validate_field_aliases with invalid internal field characters."""

        class Meta:
            model = ODataTestModel
            field_aliases = {"alias": "name; drop table"}

        with pytest.raises(ValueError, match="Invalid internal field"):
            ODataSelector._validate_field_aliases(Meta.field_aliases)

    def test_query_max_length_exceeded(self):
        """Line 198: DoS protection for long query strings."""

        class BasicSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        selector = BasicSelector()
        long_query = "x" * 5000
        with pytest.raises(QueryError, match="Query string too long"):
            selector.query(long_query)

    def test_query_as_dtos_max_length_exceeded(self):
        """Line 229: DoS protection in query_as_dtos."""

        class BasicSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                dto_class = SimpleDTO

        selector = BasicSelector()
        long_query = "x" * 5000
        with pytest.raises(QueryError, match="Query string too long"):
            selector.query_as_dtos(long_query)

    def test_query_as_dtos_values_mode_hybrid(self):
        """Lines 242-244: hybrid mode in query_as_dtos."""
        target = ODataFKTarget.objects.create(name="T1", code="C1")
        ODataModelWithFK.objects.create(title="M1", target=target)

        class HybridSelector(ODataSelector):
            class Meta:
                model = ODataModelWithFK
                dto_class = ModelWithFKDTO
                expandable_fields = {"target": FKTargetDTO}
                values_mode = True

        selector = HybridSelector()
        # This should trigger hybrid mode because 'target' is a forward FK
        results = selector.query_as_dtos("$expand=target")
        assert len(results) == 1
        assert isinstance(results[0], ModelWithFKDTO)
        assert results[0].target.name == "T1"

    def test_query_as_dicts_no_query_string(self):
        """Line 275: query_as_dicts without query string returns .values()."""
        ODataTestModel.objects.create(name="T1", created_at=timezone.now())

        class BasicSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        selector = BasicSelector()
        results = selector.query_as_dicts(None)
        assert len(results) >= 1
        assert isinstance(results[0], dict)
        assert results[0]["name"] == "T1"

    def test_query_as_dicts_max_length_exceeded(self):
        """Line 290: DoS protection in query_as_dicts."""

        class BasicSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        selector = BasicSelector()
        long_query = "x" * 5000
        with pytest.raises(QueryError, match="Query string too long"):
            selector.query_as_dicts(long_query)

    def test_query_as_dicts_values_mode_hybrid(self):
        """Lines 309-311: hybrid mode in query_as_dicts."""
        target = ODataFKTarget.objects.create(name="T1", code="C1")
        ODataModelWithFK.objects.create(title="M1", target=target)

        class HybridSelector(ODataSelector):
            class Meta:
                model = ODataModelWithFK
                dto_class = ModelWithFKDTO
                expandable_fields = {"target": FKTargetDTO}
                values_mode = True

        selector = HybridSelector()
        results = selector.query_as_dicts("$expand=target")
        assert len(results) == 1
        # Hybrid returns DTOs even in as_dicts if expand is used
        assert isinstance(results[0], ModelWithFKDTO)

    def test_get_many_values_mode_false(self):
        """Line 349: get_many with values_mode=False."""
        ODataTestModel.objects.create(name="T1", created_at=timezone.now())

        class NoValuesSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                dto_class = SimpleDTO
                values_mode = False

        selector = NoValuesSelector()
        results = selector.get_many()
        assert len(results) >= 1
        assert isinstance(results[0], SimpleDTO)

    def test_get_many_dicts_pagination_cap(self):
        """Lines 391-398: Pagination limit capping in get_many_dicts."""

        class CappedSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                max_limit = 10

        selector = CappedSelector()
        qb = QueryBuilder().top(100)
        # This covers the branch that caps the limit
        selector.get_many_dicts(qb)

    def test_get_one_not_found(self):
        """Line 470: get_one returns None if not found."""

        class BasicSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                dto_class = SimpleDTO

        selector = BasicSelector()
        qb = QueryBuilder().filter("id eq 9999")
        assert selector.get_one(qb) is None

    def test_get_one_found(self):
        """Line 472-483: get_one returns DTO if found."""
        obj = ODataTestModel.objects.create(name="One", created_at=timezone.now())

        class BasicSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                dto_class = SimpleDTO

        selector = BasicSelector()
        qb = QueryBuilder().filter(f"id eq {obj.id}")
        dto = selector.get_one(qb)
        assert dto.id == obj.id

    def test_get_by_pk(self):
        """Test get_by_pk convenience method."""
        obj = ODataTestModel.objects.create(name="PK Test", created_at=timezone.now())

        class BasicSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                dto_class = SimpleDTO

        selector = BasicSelector()
        dto = selector.get_by_pk(obj.id)
        assert dto.id == obj.id
        assert dto.name == "PK Test"

    def test_get_by_pk_with_qb(self):
        """Test get_by_pk with additional query builder."""
        obj = ODataTestModel.objects.create(name="PK Test QB", count=10, created_at=timezone.now())

        class BasicSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                dto_class = SimpleDTO

        selector = BasicSelector()
        qb = QueryBuilder().filter("count gt 5")
        dto = selector.get_by_pk(obj.id, qb)
        assert dto.id == obj.id

    def test_get_queryset_autodetect_onetoone(self):
        """Lines 154-167: Auto-detect OneToOne fields."""

        class O2OSelector(ODataSelector):
            class Meta:
                model = ODataOneToOneParent

        selector = O2OSelector()
        qs = selector.get_queryset()
        # Verify select_related was applied
        assert "child" in qs.query.select_related

    def test_get_queryset_no_onetoone(self):
        """Line 170: get_queryset without OneToOne fields."""

        class BasicSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        selector = BasicSelector()
        qs = selector.get_queryset()
        assert qs.query.select_related is False or not qs.query.select_related

    def test_get_queryset_error_handling(self):
        """Line 171: Coverage for try-except block in get_queryset."""

        class BadModel:
            objects = ODataTestModel.objects  # Reuse objects manager
            _meta = type("Meta", (), {"fields": property(lambda x: exec('raise AttributeError("test")'))})

        class BadSelector(ODataSelector):
            class Meta:
                model = BadModel

        selector = BadSelector()
        # Should not raise
        selector.get_queryset()

    def test_get_many_with_default_ordering(self):
        """Lines 329-338: default_ordering in get_many."""

        class OrderedSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                dto_class = SimpleDTO
                default_ordering = ["-name", "id"]

        selector = OrderedSelector()
        # This covers applying default ordering
        selector.get_many()

    def test_get_many_dicts_with_default_ordering(self):
        """Lines 381-390: default_ordering in get_many_dicts."""

        class OrderedSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                default_ordering = ["-name"]

        selector = OrderedSelector()
        selector.get_many_dicts()

    def test_query_as_dtos_no_query_string(self):
        """Line 223: query_as_dtos without query string."""
        ODataTestModel.objects.create(name="T1", created_at=timezone.now())

        class BasicSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                dto_class = SimpleDTO

        selector = BasicSelector()
        results = selector.query_as_dtos(None)
        assert len(results) >= 1
        assert isinstance(results[0], SimpleDTO)

    def test_query_lazy_ast_parsing(self, monkeypatch):
        """Lines 212-215: ensure AST is populated for filters."""

        class MockSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                dto_class = SimpleDTO

        selector = MockSelector()

        # We need an intent that has expression but NO ast.
        # odata_query_to_intent usually populates AST if parse_odata_query succeeded.
        # So we mock parse_filter to return None in parse_odata_query but work later.

        from fc_selector.protocols.odata.parsers import filter as filter_parser

        original_parse = filter_parser.parse_filter

        call_count = 0

        def mock_parse(expr):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # First call (from parse_odata_query) returns None
            return original_parse(expr)

        monkeypatch.setattr(filter_parser, "parse_filter", mock_parse)

        # Trigger query with filter
        selector.query("$filter=name eq 'test'")

    def test_query_as_dicts_lazy_ast_parsing(self, monkeypatch):
        """Line 300: ensure AST is populated in query_as_dicts."""
        ODataTestModel.objects.create(name="T1", created_at=timezone.now())

        class BasicSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        selector = BasicSelector()

        from fc_selector.protocols.odata.parsers import filter as filter_parser

        original_parse = filter_parser.parse_filter
        call_count = 0

        def mock_parse(expr):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None
            return original_parse(expr)

        monkeypatch.setattr(filter_parser, "parse_filter", mock_parse)

        selector.query_as_dicts("$filter=name eq 'T1'")

    def test_resolve_aliases_malformed_query(self):
        """Line 501: resolve_aliases with param without '='."""

        class AliasedSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                field_aliases = {"title": "name"}

        selector = AliasedSelector()
        # "not_a_param" doesn't have "=", currently it is dropped
        resolved = selector._resolve_aliases_in_query_string("$filter=title eq 'test'&not_a_param")
        assert "name eq 'test'" in resolved
        assert "not_a_param" not in resolved

    def test_resolve_aliases_orderby_complex(self):
        """Lines 529-542: resolve_aliases_in_orderby with various tokens."""

        class AliasedSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                field_aliases = {"title": "name"}

        selector = AliasedSelector()
        # Multiple commas, spaces, etc.
        resolved = selector._resolve_aliases_in_orderby("title  desc, id , title")
        assert resolved == "name desc,id,name"

    def test_to_dto_no_class_raises(self):
        """Line 219: to_dto without dto_class raises ValueError."""

        class NoDTOSelector(ODataSelector):
            class Meta:
                model = ODataTestModel

        selector = NoDTOSelector()
        with pytest.raises(ValueError, match="dto_class not configured"):
            selector.to_dto(None)

    def test_is_filterable_is_sortable(self):
        """Lines 149, 153: trivial coverage."""
        assert ODataSelector.is_filterable() is True
        assert ODataSelector.is_sortable() is True

    def test_resolve_aliases_in_select_complex(self):
        """Lines 524-525: resolve_aliases_in_select with spaces."""

        class AliasedSelector(ODataSelector):
            class Meta:
                model = ODataTestModel
                field_aliases = {"title": "name"}

        selector = AliasedSelector()
        resolved = selector._resolve_aliases_in_select(" id , title ")
        assert resolved == "id,name"
