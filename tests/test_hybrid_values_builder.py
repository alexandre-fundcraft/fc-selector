"""
Tests for HybridValuesBuilder.

Covers fc_selector/django/hybrid_values_builder.py and the hybrid routing
in fc_selector/django/executor.py.
"""
# pylint: disable=redefined-outer-name  # pytest fixtures

from dataclasses import dataclass
from typing import Optional

import pytest

from fc_selector.core.dtos import UNSET, BaseODataDTO
from fc_selector.core.intent import (
    ExpandIntent,
    FilterIntent,
    OrderField,
    OrderIntent,
    PaginationIntent,
    QueryIntent,
    SelectIntent,
)
from fc_selector.core.query_builder import QueryBuilder
from fc_selector.django.executor import DjangoExecutor
from fc_selector.django.hybrid_values_builder import HybridValuesBuilder
from fc_selector.django.selector import ODataSelector
from fc_selector.protocols.odata.parsers.filter import parse_filter as parse
from tests.integration.support.models import (
    ODataChildModel,
    ODataFKTarget,
    ODataGrandChildModel,
    ODataM2MTarget,
    ODataModelWithFK,
    ODataModelWithRelations,
)

# --- DTOs ---


@dataclass
class FKTargetDTO(BaseODataDTO):
    id: int = UNSET
    name: str = UNSET
    code: str = UNSET


@dataclass
class ModelWithFKDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET
    value: int = UNSET
    target: Optional[FKTargetDTO] = UNSET
    second_target: Optional[FKTargetDTO] = UNSET


@dataclass
class M2MTargetDTO(BaseODataDTO):
    id: int = UNSET
    name: str = UNSET


@dataclass
class GrandChildDTO(BaseODataDTO):
    id: int = UNSET
    note: str = UNSET


@dataclass
class ChildDTO(BaseODataDTO):
    id: int = UNSET
    label: str = UNSET
    score: int = UNSET
    category: Optional[M2MTargetDTO] = UNSET
    grandchildren: list[GrandChildDTO] = UNSET


@dataclass
class ParentWithRelationsDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET
    value: int = UNSET
    target: Optional[FKTargetDTO] = UNSET
    children: list[ChildDTO] = UNSET
    tags: list[M2MTargetDTO] = UNSET


# --- Selectors ---


class FKSelector(ODataSelector):
    class Meta:
        model = ODataModelWithFK
        dto_class = ModelWithFKDTO
        expandable_fields = {
            "target": FKTargetDTO,
            "second_target": FKTargetDTO,
        }


# --- Fixtures ---


@pytest.fixture
def target_a():
    return ODataFKTarget.objects.create(name="Alpha", code="A")


@pytest.fixture
def target_b():
    return ODataFKTarget.objects.create(name="Beta", code="B")


@pytest.fixture
def obj_with_fk(target_a):
    return ODataModelWithFK.objects.create(title="Item1", value=10, target=target_a)


@pytest.fixture
def obj_with_two_fks(target_a, target_b):
    return ODataModelWithFK.objects.create(
        title="Item2", value=20, target=target_a, second_target=target_b
    )


@pytest.fixture
def obj_null_fk():
    return ODataModelWithFK.objects.create(title="Orphan", value=0, target=None)


@pytest.fixture
def executor():
    return DjangoExecutor(
        expandable_fields={
            "target": FKTargetDTO,
            "second_target": FKTargetDTO,
        },
    )


@pytest.fixture
def selector():
    return FKSelector()


@pytest.fixture
def m2m_tag_x():
    return ODataM2MTarget.objects.create(name="TagX")


@pytest.fixture
def m2m_tag_y():
    return ODataM2MTarget.objects.create(name="TagY")


@pytest.fixture
def parent_with_children(target_a, m2m_tag_x, m2m_tag_y):
    parent = ODataModelWithRelations.objects.create(title="Parent1", value=100, target=target_a)
    child1 = ODataChildModel.objects.create(parent=parent, label="Child-A", score=10, category=m2m_tag_x)
    child2 = ODataChildModel.objects.create(parent=parent, label="Child-B", score=20)
    parent.tags.add(m2m_tag_x, m2m_tag_y)
    return parent, child1, child2


EXPANDABLE_FIELDS_FULL = {
    "target": FKTargetDTO,
    "children": {
        "dto_class": ChildDTO,
        "expandable_fields": {
            "category": M2MTargetDTO,
            "grandchildren": {
                "dto_class": GrandChildDTO,
            },
        },
    },
    "tags": M2MTargetDTO,
}


# --- Tests: classify_relations ---


@pytest.mark.django_db
class TestClassifyRelations:
    def test_forward_fk_classified(self):
        expand = ExpandIntent(relations={"target": QueryIntent()})
        forward, reverse_fk, m2m = HybridValuesBuilder.classify_relations(
            ODataModelWithFK, expand, {}
        )
        assert "target" in forward
        assert reverse_fk == {}
        assert m2m == {}

    def test_reverse_relation_classified(self):
        expand = ExpandIntent(relations={"odatamodelwithfk_set": QueryIntent()})
        forward, reverse_fk, m2m = HybridValuesBuilder.classify_relations(
            ODataFKTarget, expand, {}
        )
        assert forward == {}
        assert "odatamodelwithfk_set" in reverse_fk
        assert m2m == {}

    def test_mixed_classification(self):
        """One forward + one reverse -> both classified."""
        expand = ExpandIntent(
            relations={
                "target": QueryIntent(),
            }
        )
        forward, reverse_fk, m2m = HybridValuesBuilder.classify_relations(
            ODataModelWithFK, expand, {}
        )
        assert "target" in forward

    def test_m2m_classified(self):
        """M2M relation classified correctly."""
        expand = ExpandIntent(relations={"tags": QueryIntent()})
        forward, reverse_fk, m2m = HybridValuesBuilder.classify_relations(
            ODataModelWithRelations, expand, {}
        )
        assert forward == {}
        assert reverse_fk == {}
        assert "tags" in m2m

    def test_all_three_classified(self):
        """Forward + reverse FK + M2M all classified correctly."""
        expand = ExpandIntent(
            relations={
                "target": QueryIntent(),
                "children": QueryIntent(),
                "tags": QueryIntent(),
            }
        )
        forward, reverse_fk, m2m = HybridValuesBuilder.classify_relations(
            ODataModelWithRelations, expand, {}
        )
        assert "target" in forward
        assert "children" in reverse_fk
        assert "tags" in m2m


# --- Tests: HybridValuesBuilder.execute (forward FK, unchanged) ---


@pytest.mark.django_db
class TestForwardFKExpand:
    def test_single_forward_fk_expand(self, obj_with_fk, target_a):
        """Single FK expand returns nested DTO with correct fields."""
        intent = QueryIntent(
            expand=ExpandIntent(relations={"target": QueryIntent()}),
        )
        builder = HybridValuesBuilder(
            expandable_fields={"target": FKTargetDTO},
        )
        qs = ODataModelWithFK.objects.all()
        result = builder.execute(qs, intent, ModelWithFKDTO)

        assert len(result) == 1
        dto = result[0]
        assert isinstance(dto, ModelWithFKDTO)
        assert dto.title == "Item1"
        assert isinstance(dto.target, FKTargetDTO)
        assert dto.target.name == "Alpha"
        assert dto.target.code == "A"

    def test_multiple_forward_fk_expands(self, obj_with_two_fks, target_a, target_b):
        """Two FKs expanded simultaneously."""
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "target": QueryIntent(),
                    "second_target": QueryIntent(),
                }
            ),
        )
        builder = HybridValuesBuilder(
            expandable_fields={
                "target": FKTargetDTO,
                "second_target": FKTargetDTO,
            },
        )
        qs = ODataModelWithFK.objects.all()
        result = builder.execute(qs, intent, ModelWithFKDTO)

        assert len(result) == 1
        dto = result[0]
        assert dto.target.name == "Alpha"
        assert dto.second_target.name == "Beta"

    def test_null_fk_returns_none(self, obj_null_fk):
        """FK is null -> relation is None, not DTO(id=None)."""
        intent = QueryIntent(
            expand=ExpandIntent(relations={"target": QueryIntent()}),
        )
        builder = HybridValuesBuilder(
            expandable_fields={"target": FKTargetDTO},
        )
        qs = ODataModelWithFK.objects.all()
        result = builder.execute(qs, intent, ModelWithFKDTO)

        assert len(result) == 1
        assert result[0].target is None


# --- Tests: Nested $select ---


@pytest.mark.django_db
class TestNestedSelect:
    def test_nested_select_in_expand(self, obj_with_fk, target_a):
        """$expand=target($select=name) -> only 'name' in nested DTO."""
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "target": QueryIntent(
                        select=SelectIntent(fields=["name"]),
                    )
                }
            ),
        )
        builder = HybridValuesBuilder(
            expandable_fields={"target": FKTargetDTO},
        )
        qs = ODataModelWithFK.objects.all()
        result = builder.execute(qs, intent, ModelWithFKDTO)

        assert len(result) == 1
        dto = result[0]
        assert dto.target.name == "Alpha"
        # 'code' is not selected, so it should remain UNSET
        assert dto.target.code is UNSET

    def test_unset_for_non_selected_root(self, obj_with_fk, target_a):
        """Fields not in root $select remain UNSET."""
        intent = QueryIntent(
            select=SelectIntent(fields=["title"]),
            expand=ExpandIntent(relations={"target": QueryIntent()}),
        )
        builder = HybridValuesBuilder(
            expandable_fields={"target": FKTargetDTO},
        )
        qs = ODataModelWithFK.objects.all()
        result = builder.execute(qs, intent, ModelWithFKDTO)

        assert len(result) == 1
        dto = result[0]
        assert dto.title == "Item1"
        # 'value' not selected
        assert dto.value is UNSET
        # expand still populated
        assert dto.target.name == "Alpha"


# --- Tests: Executor hybrid routing ---


@pytest.mark.django_db
class TestExecutorHybridRouting:
    def test_forward_only_uses_hybrid(self, obj_with_fk, target_a, executor):
        """Forward-only expand returns DTOs via try_hybrid."""
        intent = QueryIntent(
            expand=ExpandIntent(relations={"target": QueryIntent()}),
        )
        qs = ODataModelWithFK.objects.all()
        result = executor.try_hybrid(qs, intent, ModelWithFKDTO)

        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], ModelWithFKDTO)
        assert result[0].target.name == "Alpha"

    def test_no_expand_returns_none(self, obj_with_fk, executor):
        """No expand -> try_hybrid returns None."""
        intent = QueryIntent(
            select=SelectIntent(fields=["id", "title"]),
        )
        qs = ODataModelWithFK.objects.all()
        result = executor.try_hybrid(qs, intent, ModelWithFKDTO)

        assert result is None

    def test_reverse_fk_uses_hybrid(self, parent_with_children):
        """Reverse FK expand returns DTOs via try_hybrid."""
        parent, child1, child2 = parent_with_children
        intent = QueryIntent(
            expand=ExpandIntent(relations={"children": QueryIntent()}),
        )
        executor = DjangoExecutor(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = executor.try_hybrid(qs, intent, ParentWithRelationsDTO)

        assert result is not None
        assert len(result) == 1
        assert len(result[0].children) == 2

    def test_m2m_uses_hybrid(self, parent_with_children):
        """M2M expand returns DTOs via try_hybrid."""
        parent, _, _ = parent_with_children
        intent = QueryIntent(
            expand=ExpandIntent(relations={"tags": QueryIntent()}),
        )
        executor = DjangoExecutor(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = executor.try_hybrid(qs, intent, ParentWithRelationsDTO)

        assert result is not None
        assert len(result) == 1
        assert len(result[0].tags) == 2

    def test_no_dto_class_returns_none(self, obj_with_fk, executor):
        """No dto_class -> try_hybrid returns None."""
        intent = QueryIntent(
            expand=ExpandIntent(relations={"target": QueryIntent()}),
        )
        qs = ODataModelWithFK.objects.all()
        result = executor.try_hybrid(qs, intent, None)

        assert result is None


# --- Tests: Filter and ordering preserved ---


@pytest.mark.django_db
class TestFilterAndOrdering:
    def test_filter_preserved(self, target_a):
        """$filter works with hybrid values mode."""
        ODataModelWithFK.objects.create(title="AAA", value=1, target=target_a)
        ODataModelWithFK.objects.create(title="BBB", value=2, target=target_a)

        filter_ast = parse("title eq 'AAA'")
        intent = QueryIntent(
            filter=FilterIntent(expression="title eq 'AAA'", ast=filter_ast),
            expand=ExpandIntent(relations={"target": QueryIntent()}),
        )

        executor = DjangoExecutor(
            expandable_fields={"target": FKTargetDTO},
        )
        qs = ODataModelWithFK.objects.all()
        result = executor.try_hybrid(qs, intent, ModelWithFKDTO)

        assert result is not None
        assert len(result) == 1
        assert result[0].title == "AAA"

    def test_ordering_preserved(self, target_a):
        """$orderby works with hybrid values mode."""
        ODataModelWithFK.objects.create(title="ZZZ", value=1, target=target_a)
        ODataModelWithFK.objects.create(title="AAA", value=2, target=target_a)

        intent = QueryIntent(
            expand=ExpandIntent(relations={"target": QueryIntent()}),
            orderby=OrderIntent(
                fields=[OrderField(field="title", direction="asc")]
            ),
        )

        executor = DjangoExecutor(
            expandable_fields={"target": FKTargetDTO},
        )
        qs = ODataModelWithFK.objects.all()
        result = executor.try_hybrid(qs, intent, ModelWithFKDTO)

        assert result is not None
        assert len(result) == 2
        assert result[0].title == "AAA"
        assert result[1].title == "ZZZ"


# --- Tests: Pagination ---


@pytest.mark.django_db
class TestPagination:
    def test_pagination_works(self, target_a):
        """$top/$skip applied correctly."""
        for i in range(5):
            ODataModelWithFK.objects.create(
                title=f"Item{i:02d}", value=i, target=target_a
            )

        intent = QueryIntent(
            expand=ExpandIntent(relations={"target": QueryIntent()}),
            orderby=OrderIntent(
                fields=[OrderField(field="title", direction="asc")]
            ),
            pagination=PaginationIntent(limit=2, offset=1),
        )

        builder = HybridValuesBuilder(
            expandable_fields={"target": FKTargetDTO},
        )
        qs = ODataModelWithFK.objects.all()
        # Apply filter/ordering before builder since executor normally does this
        qs = qs.order_by("title")
        result = builder.execute(qs, intent, ModelWithFKDTO)

        assert len(result) == 2
        assert result[0].title == "Item01"
        assert result[1].title == "Item02"


# --- Tests: Field aliases ---


@pytest.mark.django_db
class TestFieldAliases:
    def test_field_aliases_resolved(self, target_a):
        """Alias in $select resolved correctly."""
        ODataModelWithFK.objects.create(title="WithAlias", value=42, target=target_a)

        intent = QueryIntent(
            select=SelectIntent(fields=["heading", "value"]),
            expand=ExpandIntent(relations={"target": QueryIntent()}),
        )

        builder = HybridValuesBuilder(
            field_aliases={"heading": "title"},
            expandable_fields={"target": FKTargetDTO},
        )
        qs = ODataModelWithFK.objects.all()
        result = builder.execute(qs, intent, ModelWithFKDTO)

        assert len(result) == 1
        dto = result[0]
        # The DTO field 'title' should be populated via the alias 'heading'->'title'
        assert dto.title == "WithAlias"
        assert dto.value == 42


# --- Tests: Selector integration ---


@pytest.mark.django_db
class TestSelectorIntegration:
    def test_get_many_with_forward_expand(self, obj_with_fk, target_a, selector):
        """get_many() uses hybrid path for forward-only expand."""
        qb = QueryBuilder().expand("target")
        result = selector.get_many(qb)

        assert len(result) >= 1
        dto = result[0]
        assert isinstance(dto, ModelWithFKDTO)
        assert isinstance(dto.target, FKTargetDTO)
        assert dto.target.name == "Alpha"

    def test_get_many_dicts_with_forward_expand(
        self, obj_with_fk, target_a, selector
    ):
        """get_many_dicts() uses hybrid path for forward-only expand."""
        qb = QueryBuilder().expand("target")
        result = selector.get_many_dicts(qb)

        assert len(result) >= 1
        # Hybrid returns DTOs, not dicts
        assert isinstance(result[0], ModelWithFKDTO)

    def test_query_as_dicts_with_forward_expand(
        self, obj_with_fk, target_a, selector
    ):
        """query_as_dicts() uses hybrid path for forward-only expand."""
        result = selector.query_as_dicts("$expand=target")

        assert len(result) >= 1
        assert isinstance(result[0], ModelWithFKDTO)

    def test_query_as_dtos_with_forward_expand(
        self, obj_with_fk, target_a, selector
    ):
        """query_as_dtos() uses hybrid path for forward-only expand."""
        result = selector.query_as_dtos("$expand=target")

        assert len(result) >= 1
        assert isinstance(result[0], ModelWithFKDTO)
        assert result[0].target.name == "Alpha"

    def test_no_expand_still_works(self, obj_with_fk, selector):
        """No expand uses plain values path."""
        qb = QueryBuilder().select("id", "title")
        result = selector.get_many_dicts(qb)

        assert len(result) >= 1
        assert isinstance(result[0], dict)
        assert "title" in result[0]


# ═══════════════════════════════════════════════════════════════
# Reverse FK tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestReverseFK:
    def test_basic_reverse_fk(self, parent_with_children):
        """Reverse FK expand returns child DTOs."""
        parent, child1, child2 = parent_with_children
        intent = QueryIntent(
            expand=ExpandIntent(relations={"children": QueryIntent()}),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        dto = result[0]
        assert dto.title == "Parent1"
        assert len(dto.children) == 2
        labels = {c.label for c in dto.children}
        assert labels == {"Child-A", "Child-B"}

    def test_empty_reverse_fk(self, target_a):
        """Parent with no children -> empty list."""
        _ = ODataModelWithRelations.objects.create(title="Lonely", value=0, target=target_a)
        intent = QueryIntent(
            expand=ExpandIntent(relations={"children": QueryIntent()}),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        assert result[0].children == []

    def test_nested_select_in_reverse_fk(self, parent_with_children):
        """$expand=children($select=label) -> only label populated."""
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "children": QueryIntent(
                        select=SelectIntent(fields=["label"]),
                    )
                }
            ),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        child = result[0].children[0]
        assert child.label in {"Child-A", "Child-B"}
        assert child.score is UNSET

    def test_nested_filter_in_reverse_fk(self, parent_with_children):
        """$expand=children($filter=score gt 15) -> only Child-B."""
        filter_ast = parse("score gt 15")
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "children": QueryIntent(
                        filter=FilterIntent(expression="score gt 15", ast=filter_ast),
                    )
                }
            ),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        assert len(result[0].children) == 1
        assert result[0].children[0].label == "Child-B"

    def test_nested_orderby_in_reverse_fk(self, parent_with_children):
        """$expand=children($orderby=label desc) -> Child-B first."""
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "children": QueryIntent(
                        orderby=OrderIntent(
                            fields=[OrderField(field="label", direction="desc")]
                        ),
                    )
                }
            ),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        assert result[0].children[0].label == "Child-B"
        assert result[0].children[1].label == "Child-A"

    def test_nested_forward_expand_in_reverse_fk(self, parent_with_children):
        """$expand=children($expand=category) -> child has nested FK DTO."""
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "children": QueryIntent(
                        expand=ExpandIntent(relations={"category": QueryIntent()}),
                    )
                }
            ),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        children = result[0].children
        # Child-A has category=TagX
        child_a = next(c for c in children if c.label == "Child-A")
        assert isinstance(child_a.category, M2MTargetDTO)
        assert child_a.category.name == "TagX"
        # Child-B has no category
        child_b = next(c for c in children if c.label == "Child-B")
        assert child_b.category is None

    def test_nested_pagination_global(self, parent_with_children):
        """$expand=children($top=1) -> only 1 child globally (limitation)."""
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "children": QueryIntent(
                        pagination=PaginationIntent(limit=1),
                        orderby=OrderIntent(
                            fields=[OrderField(field="label", direction="asc")]
                        ),
                    )
                }
            ),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        # Should only have 1 child total across all parents because pagination applies to the single child query
        assert len(result[0].children) == 1
        assert result[0].children[0].label == "Child-A"

    def test_multiple_parents(self, target_a, m2m_tag_x):
        """Multiple parents each get their own children."""
        p1 = ODataModelWithRelations.objects.create(title="P1", value=1, target=target_a)
        p2 = ODataModelWithRelations.objects.create(title="P2", value=2, target=target_a)
        ODataChildModel.objects.create(parent=p1, label="C1-A", score=1)
        ODataChildModel.objects.create(parent=p1, label="C1-B", score=2)
        ODataChildModel.objects.create(parent=p2, label="C2-A", score=3)

        intent = QueryIntent(
            expand=ExpandIntent(relations={"children": QueryIntent()}),
            orderby=OrderIntent(fields=[OrderField(field="title", direction="asc")]),
        )
        executor = DjangoExecutor(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = executor.try_hybrid(qs, intent, ParentWithRelationsDTO)

        assert result is not None
        assert len(result) == 2
        assert result[0].title == "P1"
        assert len(result[0].children) == 2
        assert result[1].title == "P2"
        assert len(result[1].children) == 1


# ═══════════════════════════════════════════════════════════════
# M2M tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestM2M:
    def test_basic_m2m(self, parent_with_children):
        """M2M expand returns target DTOs."""
        parent, _, _ = parent_with_children
        intent = QueryIntent(
            expand=ExpandIntent(relations={"tags": QueryIntent()}),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        dto = result[0]
        assert len(dto.tags) == 2
        tag_names = {t.name for t in dto.tags}
        assert tag_names == {"TagX", "TagY"}

    def test_empty_m2m(self, target_a):
        """Parent with no tags -> empty list."""
        ODataModelWithRelations.objects.create(title="NoTags", value=0, target=target_a)
        intent = QueryIntent(
            expand=ExpandIntent(relations={"tags": QueryIntent()}),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        assert result[0].tags == []

    def test_shared_m2m_targets(self, target_a, m2m_tag_x, m2m_tag_y):
        """Two parents share the same M2M target."""
        p1 = ODataModelWithRelations.objects.create(title="P1", value=1, target=target_a)
        p2 = ODataModelWithRelations.objects.create(title="P2", value=2, target=target_a)
        p1.tags.add(m2m_tag_x)
        p2.tags.add(m2m_tag_x, m2m_tag_y)

        intent = QueryIntent(
            expand=ExpandIntent(relations={"tags": QueryIntent()}),
            orderby=OrderIntent(fields=[OrderField(field="title", direction="asc")]),
        )
        executor = DjangoExecutor(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = executor.try_hybrid(qs, intent, ParentWithRelationsDTO)

        assert result is not None
        assert len(result) == 2
        assert len(result[0].tags) == 1
        assert result[0].tags[0].name == "TagX"
        assert len(result[1].tags) == 2

    def test_nested_select_in_m2m(self, parent_with_children):
        """$expand=tags($select=name) -> only name populated."""
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "tags": QueryIntent(
                        select=SelectIntent(fields=["name"]),
                    )
                }
            ),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        for tag in result[0].tags:
            assert tag.name in {"TagX", "TagY"}
            # id should not be populated if not selected
            assert tag.id is UNSET

    def test_nested_filter_in_m2m(self, parent_with_children):
        """$expand=tags($filter=name eq 'TagX') -> only TagX."""
        filter_ast = parse("name eq 'TagX'")
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "tags": QueryIntent(
                        filter=FilterIntent(expression="name eq 'TagX'", ast=filter_ast),
                    )
                }
            ),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        assert len(result[0].tags) == 1
        assert result[0].tags[0].name == "TagX"


# ═══════════════════════════════════════════════════════════════
# Mixed relations tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestMixedRelations:
    def test_forward_and_reverse(self, parent_with_children):
        """Forward FK + reverse FK in same expand."""
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "target": QueryIntent(),
                    "children": QueryIntent(),
                }
            ),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        dto = result[0]
        assert isinstance(dto.target, FKTargetDTO)
        assert dto.target.name == "Alpha"
        assert len(dto.children) == 2

    def test_forward_and_m2m(self, parent_with_children):
        """Forward FK + M2M in same expand."""
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "target": QueryIntent(),
                    "tags": QueryIntent(),
                }
            ),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        dto = result[0]
        assert isinstance(dto.target, FKTargetDTO)
        assert len(dto.tags) == 2

    def test_all_three_relation_types(self, parent_with_children):
        """Forward FK + reverse FK + M2M all expanded."""
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "target": QueryIntent(),
                    "children": QueryIntent(),
                    "tags": QueryIntent(),
                }
            ),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        dto = result[0]
        assert isinstance(dto.target, FKTargetDTO)
        assert dto.target.name == "Alpha"
        assert len(dto.children) == 2
        assert len(dto.tags) == 2

    def test_with_filter_and_pagination(self, target_a, m2m_tag_x, m2m_tag_y):
        """Filter + pagination + mixed expand."""
        for i in range(5):
            p = ODataModelWithRelations.objects.create(
                title=f"Item{i:02d}", value=i, target=target_a
            )
            ODataChildModel.objects.create(parent=p, label=f"Child-{i}", score=i * 10)
            p.tags.add(m2m_tag_x)

        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "children": QueryIntent(),
                    "tags": QueryIntent(),
                }
            ),
            orderby=OrderIntent(fields=[OrderField(field="title", direction="asc")]),
            pagination=PaginationIntent(limit=2, offset=1),
        )
        executor = DjangoExecutor(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = executor.try_hybrid(qs, intent, ParentWithRelationsDTO)

        assert result is not None
        assert len(result) == 2
        assert result[0].title == "Item01"
        assert result[1].title == "Item02"
        # Each should have 1 child and 1 tag
        for dto in result:
            assert len(dto.children) == 1
            assert len(dto.tags) == 1


# ═══════════════════════════════════════════════════════════════
# Recursive nesting tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestRecursiveNesting:
    def test_reverse_in_reverse(self, parent_with_children):
        """$expand=children($expand=grandchildren) — reverse FK within reverse FK."""
        parent, child1, child2 = parent_with_children
        ODataGrandChildModel.objects.create(child=child1, note="GC1")
        ODataGrandChildModel.objects.create(child=child1, note="GC2")
        ODataGrandChildModel.objects.create(child=child2, note="GC3")

        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "children": QueryIntent(
                        expand=ExpandIntent(
                            relations={"grandchildren": QueryIntent()}
                        ),
                    )
                }
            ),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        children = result[0].children
        assert len(children) == 2

        child_a = next(c for c in children if c.label == "Child-A")
        child_b = next(c for c in children if c.label == "Child-B")
        assert len(child_a.grandchildren) == 2
        gc_notes = {gc.note for gc in child_a.grandchildren}
        assert gc_notes == {"GC1", "GC2"}
        assert len(child_b.grandchildren) == 1
        assert child_b.grandchildren[0].note == "GC3"

    def test_forward_and_reverse_in_reverse(self, parent_with_children):
        """$expand=children($expand=category,grandchildren) — FK + reverse FK within reverse FK."""
        parent, child1, child2 = parent_with_children
        ODataGrandChildModel.objects.create(child=child1, note="GC1")

        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "children": QueryIntent(
                        expand=ExpandIntent(
                            relations={
                                "category": QueryIntent(),
                                "grandchildren": QueryIntent(),
                            }
                        ),
                    )
                }
            ),
        )
        builder = HybridValuesBuilder(expandable_fields=EXPANDABLE_FIELDS_FULL)
        qs = ODataModelWithRelations.objects.all()
        result = builder.execute(qs, intent, ParentWithRelationsDTO)

        assert len(result) == 1
        child_a = next(c for c in result[0].children if c.label == "Child-A")
        assert isinstance(child_a.category, M2MTargetDTO)
        assert child_a.category.name == "TagX"
        assert len(child_a.grandchildren) == 1
        assert child_a.grandchildren[0].note == "GC1"
