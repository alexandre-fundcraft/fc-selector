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
from tests.integration.support.models import ODataFKTarget, ODataModelWithFK

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


# --- Tests: classify_relations ---


@pytest.mark.django_db
class TestClassifyRelations:
    def test_forward_fk_classified(self):
        expand = ExpandIntent(relations={"target": QueryIntent()})
        forward, reverse = HybridValuesBuilder.classify_relations(
            ODataModelWithFK, expand, {}
        )
        assert "target" in forward
        assert reverse == []

    def test_reverse_relation_classified(self):
        expand = ExpandIntent(relations={"odatamodelwithfk_set": QueryIntent()})
        forward, reverse = HybridValuesBuilder.classify_relations(
            ODataFKTarget, expand, {}
        )
        assert forward == {}
        assert "odatamodelwithfk_set" in reverse

    def test_mixed_classification(self):
        """One forward + one reverse -> both classified."""
        expand = ExpandIntent(
            relations={
                "target": QueryIntent(),
                # related_items doesn't exist on this model, but we're testing classification
            }
        )
        forward, reverse = HybridValuesBuilder.classify_relations(
            ODataModelWithFK, expand, {}
        )
        assert "target" in forward


# --- Tests: HybridValuesBuilder.execute ---


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

    def test_reverse_relation_returns_none(self, target_a, obj_with_fk, executor):
        """Reverse FK -> try_hybrid returns None."""
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={"odatamodelwithfk_set": QueryIntent()}
            ),
        )
        qs = ODataFKTarget.objects.all()
        executor_for_target = DjangoExecutor(
            expandable_fields={"odatamodelwithfk_set": ModelWithFKDTO},
        )
        result = executor_for_target.try_hybrid(qs, intent, FKTargetDTO)

        assert result is None

    def test_mixed_forward_reverse_returns_none(self, target_a, obj_with_fk):
        """One forward + one reverse -> try_hybrid returns None."""
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "target": QueryIntent(),
                    "nonexistent_reverse": QueryIntent(),
                }
            ),
        )
        executor = DjangoExecutor(
            expandable_fields={
                "target": FKTargetDTO,
                "nonexistent_reverse": ModelWithFKDTO,
            },
        )
        qs = ODataModelWithFK.objects.all()
        result = executor.try_hybrid(qs, intent, ModelWithFKDTO)

        assert result is None

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
