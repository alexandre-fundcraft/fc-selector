"""
Additional tests for fc_selector/django/hybrid_values_builder.py to improve coverage.
"""
import logging
from dataclasses import dataclass

import pytest

from fc_selector.core.dtos import UNSET, BaseODataDTO
from fc_selector.core.dtos.base import MAX_DTO_RECURSION_DEPTH
from fc_selector.core.intent import ExpandIntent, QueryIntent
from fc_selector.django.hybrid_values_builder import HybridValuesBuilder
from tests.integration.support.models import ODataModelWithFK, ODataModelWithRelations


@dataclass
class SimpleDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET

@dataclass
class RelationDTO(BaseODataDTO):
    id: int = UNSET
    name: str = UNSET

@pytest.mark.django_db
class TestHybridValuesBuilderCoverage:
    """Coverage tests for HybridValuesBuilder edge cases."""

    def test_classify_relations_unknown_relation(self, caplog):
        """Test classification of unknown relation triggers warning."""
        expand = ExpandIntent(relations={"unknown_rel": QueryIntent()})
        with caplog.at_level(logging.WARNING):
            forward, reverse, m2m = HybridValuesBuilder.classify_relations(
                ODataModelWithFK, expand, {}
            )
        assert "not a recognized" in caplog.text
        assert "unknown_rel" in caplog.text
        assert not forward
        assert not reverse
        assert not m2m

    def test_max_recursion_depth_reverse_fk(self):
        """Test recursion depth limit in _attach_reverse_fk_children."""
        builder = HybridValuesBuilder()
        # Mock depth to limit

        # We need a DTO with a PK
        dto = SimpleDTO(id=1)

        # We need relations to process
        relations = {"children": QueryIntent()}

        # We call the internal method directly with max depth
        builder._attach_reverse_fk_children(
            ODataModelWithRelations,
            [dto],
            relations,
            _depth=MAX_DTO_RECURSION_DEPTH
        )

        # Should return immediately, so 'children' attribute won't be set
        assert not hasattr(dto, "children")

    def test_max_recursion_depth_m2m(self):
        """Test recursion depth limit in _attach_m2m_children."""
        builder = HybridValuesBuilder()
        dto = SimpleDTO(id=1)
        relations = {"tags": QueryIntent()}

        builder._attach_m2m_children(
            ODataModelWithRelations,
            [dto],
            relations,
            _depth=MAX_DTO_RECURSION_DEPTH
        )

        assert not hasattr(dto, "tags")

    def test_collect_values_fields_implicit_fields(self):
        """Test _collect_values_fields without select or DTO class."""
        builder = HybridValuesBuilder()
        intent = QueryIntent()

        # Use a model with mixed fields
        fields = builder._collect_values_fields(
            ODataModelWithFK, intent, {}
        )

        assert "id" in fields
        assert "title" in fields
        # target (FK) should be included as the field name
        assert "target" in fields
        # target_id is added only if it's in forward_relations, which is empty here

        # Reverse relations and M2M should be excluded
        # ODataModelWithFK doesn't have them, let's check ODataModelWithRelations

        fields_rel = builder._collect_values_fields(
            ODataModelWithRelations, intent, {}
        )
        assert "tags" not in fields_rel # M2M
        assert "children" not in fields_rel # Reverse FK

    def test_collect_related_fields_no_relation(self):
        """Test _collect_related_fields with invalid relation."""
        builder = HybridValuesBuilder()
        fields = builder._collect_related_fields(
            ODataModelWithFK, "nonexistent", QueryIntent()
        )
        assert fields == []

    def test_unflatten_no_nested_dto_class(self):
        """Test _unflatten_and_build with missing nested DTO class."""
        # Expand defined in intent but not in expandable_fields config
        intent = QueryIntent(
            expand=ExpandIntent(relations={"target": QueryIntent()})
        )
        builder = HybridValuesBuilder(
            expandable_fields={} # Empty config
        )

        row = {"id": 1, "target__id": 2, "target__name": "Test"}
        # Should handle it gracefully, setting target=None

        # We need a DTO class that has 'target' field
        @dataclass
        class TestDTO(BaseODataDTO):
            id: int = UNSET
            target: RelationDTO = UNSET

        dto = builder._unflatten_and_build(row, TestDTO, intent, {"target": QueryIntent()})
        assert dto.target is None

    def test_extract_nested_all_none(self):
        """Test _extract_nested where all values are None."""
        builder = HybridValuesBuilder()
        row = {"rel__id": None, "rel__name": None}

        result = builder._extract_nested(
            row, "rel", RelationDTO, QueryIntent()
        )
        assert result is None

    def test_attach_reverse_fk_no_pks(self):
        """Test _attach_reverse_fk_children with DTOs having no PKs."""
        builder = HybridValuesBuilder()
        dtos = [SimpleDTO(id=UNSET)]
        relations = {"children": QueryIntent()}

        builder._attach_reverse_fk_children(
            ODataModelWithRelations, dtos, relations
        )
        # Should return early
        assert not hasattr(dtos[0], "children")

    def test_attach_reverse_fk_bad_info(self):
        """Test _attach_reverse_fk_children with bad relation info."""
        builder = HybridValuesBuilder()
        dtos = [SimpleDTO(id=1)]
        # "target" is a forward FK, so get_reverse_fk_info returns None
        relations = {"target": QueryIntent()}

        builder._attach_reverse_fk_children(
            ODataModelWithRelations, dtos, relations
        )
        # Should set empty list
        assert dtos[0].target == []

    def test_attach_reverse_fk_no_dto_class(self):
        """Test _attach_reverse_fk_children with no child DTO class configured."""
        builder = HybridValuesBuilder(expandable_fields={})
        dtos = [SimpleDTO(id=1)]
        relations = {"children": QueryIntent()} # children is valid reverse FK

        builder._attach_reverse_fk_children(
            ODataModelWithRelations, dtos, relations
        )
        # Should set empty list
        assert dtos[0].children == []

    def test_attach_m2m_no_pks(self):
        """Test _attach_m2m_children with DTOs having no PKs."""
        builder = HybridValuesBuilder()
        dtos = [SimpleDTO(id=UNSET)]
        relations = {"tags": QueryIntent()}

        builder._attach_m2m_children(
            ODataModelWithRelations, dtos, relations
        )
        assert not hasattr(dtos[0], "tags")

    def test_attach_m2m_bad_info(self):
        """Test _attach_m2m_children with bad relation info."""
        builder = HybridValuesBuilder()
        dtos = [SimpleDTO(id=1)]
        relations = {"title": QueryIntent()} # Not M2M

        builder._attach_m2m_children(
            ODataModelWithRelations, dtos, relations
        )
        # Should set empty list
        assert dtos[0].title == []

    def test_attach_m2m_no_dto_class(self):
        """Test _attach_m2m_children with no child DTO class."""
        builder = HybridValuesBuilder(expandable_fields={})
        dtos = [SimpleDTO(id=1)]
        relations = {"tags": QueryIntent()} # Valid M2M

        builder._attach_m2m_children(
            ODataModelWithRelations, dtos, relations
        )
        assert dtos[0].tags == []

    def test_get_expand_config_nested_deep_search(self):
        """Test _get_expand_config_nested finding config in parent's nested config."""
        # Setup complex config
        config = {
            "children": {
                "dto_class": SimpleDTO,
                "expandable_fields": {
                    "grandchildren": RelationDTO
                }
            }
        }
        builder = HybridValuesBuilder(expandable_fields=config)

        # Should find grandchildren config
        nested_config = builder._get_expand_config_nested("grandchildren")
        assert nested_config is not None
        assert nested_config["dto_class"] is RelationDTO

    def test_get_nested_expandable_fields_empty(self):
        """Test _get_nested_expandable_fields returns empty if no nested config."""
        config = {"target": RelationDTO} # No nested fields
        builder = HybridValuesBuilder(expandable_fields=config)

        nested = builder._get_nested_expandable_fields("target")
        assert nested == {}

    def test_recurse_into_children_empty(self):
        """Test _recurse_into_children returns early if empty list."""
        builder = HybridValuesBuilder()
        builder._recurse_into_children(None, [], {}, {}, "rel", 0)
        # Should just not crash

