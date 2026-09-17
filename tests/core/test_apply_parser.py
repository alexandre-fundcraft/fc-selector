"""Tests for the OData $apply parser: groupby/aggregate/filter transformations."""

import pytest

from fc_selector.core.ast.nodes import Apply, ApplyAggregateSpec, ApplyFilter, ApplyGroupBy
from fc_selector.core.exceptions import QueryError
from fc_selector.protocols.odata.parsers.apply import parse_apply


def test_parse_bare_count():
    result = parse_apply("aggregate($count as total)")
    assert result == Apply(
        transformations=[
            ApplyGroupBy(fields=[], aggregate=[ApplyAggregateSpec(source_field=None, method="count", alias="total")])
        ]
    )


def test_parse_groupby_single_field_single_aggregate():
    result = parse_apply("groupby((status), aggregate(id with countdistinct as n))")
    assert result == Apply(
        transformations=[
            ApplyGroupBy(
                fields=["status"],
                aggregate=[ApplyAggregateSpec(source_field="id", method="countdistinct", alias="n")],
            )
        ]
    )


def test_parse_groupby_multi_field_multi_aggregate():
    result = parse_apply(
        "groupby((status, domain), aggregate(id with countdistinct as n, rating with average as avg_rating))"
    )
    group = result.transformations[0]
    assert isinstance(group, ApplyGroupBy)
    assert group.fields == ["status", "domain"]
    assert group.aggregate == [
        ApplyAggregateSpec(source_field="id", method="countdistinct", alias="n"),
        ApplyAggregateSpec(source_field="rating", method="average", alias="avg_rating"),
    ]


def test_parse_groupby_no_aggregate_is_distinct():
    """groupby with no aggregate() clause means 'distinct rows of these fields'."""
    result = parse_apply("groupby((status, domain))")
    group = result.transformations[0]
    assert group.fields == ["status", "domain"]
    assert group.aggregate is None


def test_parse_filter_then_groupby():
    result = parse_apply("filter(status eq 'published')/groupby((domain), aggregate($count as n))")
    assert len(result.transformations) == 2
    assert isinstance(result.transformations[0], ApplyFilter)
    assert isinstance(result.transformations[1], ApplyGroupBy)


def test_parse_all_standard_methods():
    result = parse_apply(
        "groupby((status), aggregate(a with sum as s, b with average as avg, c with min as mn, d with max as mx, e with countdistinct as cd))"
    )
    methods = [spec.method for spec in result.transformations[0].aggregate]
    assert methods == ["sum", "average", "min", "max", "countdistinct"]


def test_parse_unknown_syntax_raises_query_error():
    with pytest.raises(QueryError):
        parse_apply("groupby(not valid odata")


def test_parse_empty_string_raises_query_error():
    with pytest.raises(QueryError):
        parse_apply("")


def test_parse_groupby_whitespace_variations():
    res1 = parse_apply("groupby((status),aggregate($count as n))")
    res2 = parse_apply("groupby((status),  aggregate($count as n))")
    assert res1 == res2
    assert res1.transformations[0].fields == ["status"]
    assert res1.transformations[0].aggregate[0].alias == "n"


def test_parse_empty_groupby_fields_raises_query_error():
    with pytest.raises(QueryError, match="groupby fields list cannot be empty"):
        parse_apply("groupby(())")


def test_parse_empty_aggregate_clause_raises_query_error():
    with pytest.raises(QueryError, match="aggregate clause cannot be empty"):
        parse_apply("groupby((status), aggregate())")
    with pytest.raises(QueryError, match="aggregate clause cannot be empty"):
        parse_apply("aggregate()")
