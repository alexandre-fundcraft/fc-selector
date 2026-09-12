"""Contracts for simplify-query-execution: compatibility and reusable intent state."""

from copy import deepcopy
from unittest.mock import Mock

import pytest

from fc_selector.core import QueryBuilder
from fc_selector.core.filters import Expand, Field
from fc_selector.django.executor import DjangoExecutor
from fc_selector.django.visitors.django_q_ext import NotEqual
from tests.integration.support.models import ODataFKTarget, ODataModelWithFK


@pytest.mark.parametrize("lhs", [(1,), [1]])
@pytest.mark.parametrize("rhs", [(2,), [2]])
def test_not_equal_parameter_sequences(lhs, rhs):
    lookup = NotEqual("value", 2)
    lookup.process_lhs = Mock(return_value=("lhs", lhs))
    lookup.process_rhs = Mock(return_value=("rhs", rhs))
    sql, params = lookup.as_sql(Mock(), Mock())
    assert sql == "lhs <> rhs"
    assert list(params) == [1, 2]


@pytest.mark.django_db
def test_executor_does_not_change_nested_caller_intent():
    intent = QueryBuilder().select("*").expand(Expand("target").select("*")).build()
    before = deepcopy(intent)
    executor = DjangoExecutor(
        allowed_fields=["title"],
        expandable_fields={
            "target": {"allowed_fields": ["name"]},
        },
    )
    executor.execute(ODataModelWithFK.objects.all(), intent)
    assert intent == before
    # Reuse is not constrained by the previous executor's projection.
    other = DjangoExecutor(allowed_fields=["value"], expandable_fields={"target": {}})
    other.execute(ODataModelWithFK.objects.all(), intent)
    assert intent == before


def test_build_detaches_nested_ast():
    builder = (
        QueryBuilder()
        .where(Field("value").is_in([1, 2]))
        .expand(Expand("target").filter(Field("name").is_in(["before"])))
    )
    first = builder.build()
    expected = deepcopy(first)
    first.filter.ast.right.val.clear()
    first.expand.relations["target"].filter.ast.right.val.clear()
    assert builder.build() == expected


@pytest.mark.django_db
def test_validation_is_read_only():
    intent = QueryBuilder().select("*").build()
    before = deepcopy(intent)
    DjangoExecutor(allowed_fields=["name"])._validate_intent(ODataFKTarget.objects.all(), intent)
    assert intent == before


@pytest.mark.django_db
@pytest.mark.parametrize("values_mode", [False, True])
@pytest.mark.parametrize("as_dicts", [False, True])
@pytest.mark.parametrize("textual", [False, True])
@pytest.mark.parametrize("shape,sql_count", [("forward", 1), ("children", 2), ("limited", 2)])
def test_materialization_parity(values_mode, as_dicts, textual, shape, sql_count, django_assert_num_queries):
    from fc_selector.core.filters import OrderBy  # noqa: PLC0415
    from fc_selector.django.selector import ODataSelector  # noqa: PLC0415
    from tests.integration.support.dtos import ChildDTO, FKTargetDTO, ParentWithRelationsDTO  # noqa: PLC0415
    from tests.integration.support.models import ODataChildModel, ODataModelWithRelations  # noqa: PLC0415

    class Selector(ODataSelector):
        class Meta:
            model = ODataModelWithRelations
            dto_class = ParentWithRelationsDTO
            expandable_fields = {"target": FKTargetDTO, "children": ChildDTO}
            default_ordering = ["id"]

    selector = Selector()
    selector.values_mode = values_mode
    target = ODataFKTarget.objects.create(name="T", code="secret")
    expected = []
    for i in range(3):
        parent = ODataModelWithRelations.objects.create(title=f"P{i}", target=target)
        for score in range(3):
            ODataChildModel.objects.create(parent=parent, label=f"C{score}", score=score)
        expected.append(
            {"title": f"P{i}", "target": {"name": "T"}}
            if shape == "forward"
            else {"title": f"P{i}", "children": [{"label": "C2"}, {"label": "C1"}][: 1 if shape == "limited" else 2]}
        )
    if shape == "forward":
        text = "$select=title&$expand=target($select=name)"
        builder = QueryBuilder().select("title").expand(Expand("target").select("name"))
    else:
        text = "$select=title&$expand=children($select=label;$filter=score gt 0;$orderby=score desc" + (
            ";$top=1)" if shape == "limited" else ")"
        )
        child = Expand("children").select("label").filter(Field("score").gt(0)).orderby(OrderBy("score").desc())
        if shape == "limited":
            child.top(1)
        builder = QueryBuilder().select("title").expand(child)
    with django_assert_num_queries(sql_count):
        if textual:
            result = selector.query_as_dicts(text) if as_dicts else selector.query_as_dtos(text)
        else:
            result = selector.get_many_dicts(builder) if as_dicts else selector.get_many(builder)
        actual = result if as_dicts else [dto.to_dict() for dto in result]
    assert actual == expected


def test_builder_replacements_and_lazy_parser():
    from fc_selector.core.filters import OrderBy  # noqa: PLC0415
    from fc_selector.protocols.odata.parsers.filter import parse_filter  # noqa: PLC0415

    parser = Mock(side_effect=parse_filter)
    builder = QueryBuilder(filter_parser=parser).filter("value eq 1")
    parser.assert_not_called()
    builder.build()
    parser.assert_called_once_with("value eq 1")
    builder.where(Field("value").eq(2)).expand(Expand("target")).orderby(OrderBy("value").desc())
    builder.filter("value eq 3").expand("second_target").orderby("title")
    assert builder.to_dict() == {"$filter": "value eq 3", "$expand": "second_target", "$orderby": "title"}
    built = builder.build()
    assert set(built.expand.relations) == {"second_target"}
    assert built.orderby.fields[0].field == "title"


@pytest.mark.django_db
@pytest.mark.parametrize("values_mode", [False, True])
def test_single_preparation_per_materialization(values_mode):
    from unittest.mock import patch  # noqa: PLC0415

    from tests.integration.support.dtos import FKSelector  # noqa: PLC0415

    selector = FKSelector()
    selector.values_mode = values_mode
    with patch.object(selector._executor, "prepare", wraps=selector._executor.prepare) as prepare:
        selector.query_as_dtos("$expand=target")
    assert prepare.call_count == 1
