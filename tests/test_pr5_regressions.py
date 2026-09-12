"""Regression contracts for PR 5 review feedback."""

from copy import deepcopy
from dataclasses import dataclass

import pytest
from django.db.models import Value

from fc_selector.core import QueryBuilder
from fc_selector.core.dtos import UNSET, BaseODataDTO
from fc_selector.core.exceptions import InvalidFieldError
from fc_selector.core.filters import Expand
from fc_selector.django.executor import DjangoExecutor
from fc_selector.django.selector import ODataSelector
from tests.integration.support.models import ODataChildModel, ODataFKTarget, ODataModelWithFK, ODataModelWithRelations


@dataclass
class AliasDTO(BaseODataDTO):
    display: str = UNSET


@dataclass
class RootDTO(BaseODataDTO):
    target: AliasDTO = UNSET


@pytest.mark.django_db
@pytest.mark.parametrize("values_mode", [False, True])
@pytest.mark.parametrize("entry", ["dicts", "dtos", "one", "executor"])
def test_nested_alias_projection(values_mode, entry):
    target = ODataFKTarget.objects.create(name="Visible", code="v")
    ODataModelWithFK.objects.create(title="Root", value=1, target=target)

    class Selector(ODataSelector):
        class Meta:
            model = ODataModelWithFK
            dto_class = RootDTO
            expandable_fields = {"target": {"dto_class": AliasDTO, "field_aliases": {"display": "name"}}}

    selector = Selector()
    selector.values_mode = values_mode
    builder = QueryBuilder().expand(Expand("target").select("display"))
    if entry == "executor":
        result = selector._executor.materialize(selector.get_queryset(), builder.build(), RootDTO)[0].to_dict()
    elif entry == "one":
        result = selector.get_one(builder).to_dict()
    elif entry == "dtos":
        result = selector.query_as_dtos("$expand=target($select=display)")[0].to_dict()
    else:
        result = selector.query_as_dicts("$expand=target($select=display)")[0]
    assert result == {"target": {"display": "Visible"}}


@pytest.mark.django_db
@pytest.mark.parametrize("values_mode", [False, True])
def test_property_dictionary_fallback(monkeypatch, values_mode):
    monkeypatch.setattr(ODataFKTarget, "display", property(lambda obj: obj.name.upper()), raising=False)
    ODataFKTarget.objects.create(name="Visible", code="v")

    class Selector(ODataSelector):
        class Meta:
            model = ODataFKTarget
            dto_class = AliasDTO

    selector = Selector()
    selector.values_mode = values_mode
    assert selector.query_as_dicts("$select=display") == [{"display": "VISIBLE"}]


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["target/missing", "target/name/missing", "missing/name"])
@pytest.mark.parametrize("allowed", [None, ["target", "missing"]])
def test_invalid_related_projection_fails_before_evaluation(path, allowed):
    executor = DjangoExecutor(allowed_fields=allowed)
    with pytest.raises(InvalidFieldError):
        executor.prepare(ODataModelWithFK.objects.all(), QueryBuilder().select(path).build())


@pytest.mark.django_db
def test_valid_related_path_and_annotation():
    executor = DjangoExecutor()
    executor.prepare(ODataModelWithFK.objects.all(), QueryBuilder().select("target/name").build())
    executor.prepare(ODataModelWithFK.objects.annotate(label=Value("ok")), QueryBuilder().select("label").build())


@dataclass
class AliasChildrenDTO(BaseODataDTO):
    children: list[AliasDTO] = UNSET


@pytest.mark.django_db
@pytest.mark.parametrize("values_mode", [False, True])
def test_collection_alias_projection(values_mode):
    parent = ODataModelWithRelations.objects.create(title="Parent", value=1)
    ODataChildModel.objects.create(parent=parent, label="Child", score=1)

    class Selector(ODataSelector):
        class Meta:
            model = ODataModelWithRelations
            dto_class = AliasChildrenDTO
            expandable_fields = {"children": {"dto_class": AliasDTO, "field_aliases": {"display": "label"}}}

    selector = Selector()
    selector.values_mode = values_mode
    assert selector.query_as_dicts("$expand=children($select=display)") == [{"children": [{"display": "Child"}]}]


def test_multilevel_mapping_is_scoped_and_does_not_mutate_inputs():
    intent = QueryBuilder().expand(Expand("children").expand(Expand("target").select("display"))).build()

    @dataclass
    class TreeDTO(BaseODataDTO):
        children: list[RootDTO] = UNSET

    mappings = {"children": {"nested_mappings": {"target": {"field_mapping": {"name": "display"}}}}}
    before = deepcopy((intent, mappings))
    result = TreeDTO.from_object({"children": [{"target": {"name": "Leaf"}}]}, intent, nested_mappings=mappings)
    assert result.to_dict() == {"children": [{"target": {"display": "Leaf"}}]}
    assert (intent, mappings) == before
