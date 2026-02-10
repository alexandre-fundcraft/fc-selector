"""
Tests for Django executor module.

Covers fc_selector/django/executor.py
"""
# pylint: disable=redefined-outer-name  # pytest fixtures

import pytest
from django.db.models import QuerySet
from django.utils import timezone

from fc_selector.core.intent import (
    ExpandIntent,
    FilterIntent,
    OrderField,
    OrderIntent,
    PaginationIntent,
    QueryIntent,
    SelectIntent,
)
from fc_selector.django.executor import DjangoExecutor
from fc_selector.protocols.odata.parsers.filter import parse_filter as parse
from tests.integration.support.models import ODataRelatedModel, ODataTestModel


@pytest.fixture
def executor():
    """Fixture for executor instance."""
    return DjangoExecutor()


@pytest.fixture
def test_model():
    """Fixture for test model."""
    return ODataTestModel


@pytest.fixture
def related_model():
    """Fixture for related model."""
    return ODataRelatedModel


@pytest.mark.django_db
class TestExecutorBasic:
    """Tests for basic executor operations."""

    def test_execute_empty_intent(self, executor, test_model):
        """Execute with empty intent returns unchanged queryset."""
        qs = test_model.objects.all()
        result = executor.execute(qs, QueryIntent())
        assert isinstance(result, QuerySet)

    def test_execute_none_intent(self, executor, test_model):
        """Execute with None intent returns unchanged queryset."""
        qs = test_model.objects.all()
        result = executor.execute(qs, None)
        assert result is qs


@pytest.mark.django_db
class TestApplyFilter:
    """Tests for filter application."""

    def test_apply_filter_simple(self, executor, test_model):
        """Apply simple filter."""
        filter_ast = parse("name eq 'test'")
        intent = QueryIntent(filter=FilterIntent(expression="name eq 'test'", ast=filter_ast))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_filter_no_ast(self, executor, test_model):
        """Filter without AST does nothing."""
        intent = QueryIntent(filter=FilterIntent(expression="name eq 'test'"))  # No AST

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        # Same queryset, no filtering applied
        assert isinstance(result, QuerySet)

    def test_apply_filter_none_filter(self, executor, test_model):
        """None filter does nothing."""
        intent = QueryIntent(filter=None)

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)


@pytest.mark.django_db
class TestApplyOrdering:
    """Tests for ordering application."""

    def test_apply_ordering_single_asc(self, executor, test_model):
        """Apply single ascending orderby."""
        intent = QueryIntent(orderby=OrderIntent(fields=[OrderField(field="name", direction="asc")]))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert "name" in str(result.query)

    def test_apply_ordering_single_desc(self, executor, test_model):
        """Apply single descending orderby."""
        intent = QueryIntent(orderby=OrderIntent(fields=[OrderField(field="name", direction="desc")]))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        # DESC shows as -name in Django
        assert "-name" in str(result.query) or "DESC" in str(result.query).upper()

    def test_apply_ordering_multiple(self, executor, test_model):
        """Apply multiple orderby fields."""
        intent = QueryIntent(
            orderby=OrderIntent(
                fields=[OrderField(field="status", direction="asc"), OrderField(field="created_at", direction="desc")]
            )
        )

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_ordering_with_dot_notation(self, executor, test_model):
        """Apply orderby with dot notation (relation.field)."""
        intent = QueryIntent(orderby=OrderIntent(fields=[OrderField(field="related_items.title", direction="asc")]))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        # Dot becomes __ in Django
        assert isinstance(result, QuerySet)

    def test_apply_ordering_empty(self, executor, test_model):
        """Empty orderby does nothing."""
        intent = QueryIntent(orderby=OrderIntent(fields=[]))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_ordering_none(self, executor, test_model):
        """None orderby does nothing."""
        intent = QueryIntent(orderby=None)

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_ordering_rejects_non_sortable_field(self, test_model):
        """Ordering by a non-sortable field raises InvalidFieldError."""
        from fc_selector.core.exceptions import InvalidFieldError

        executor = DjangoExecutor(non_sortable_fields=["status", "count"])
        intent = QueryIntent(orderby=OrderIntent(fields=[OrderField(field="status", direction="asc")]))

        qs = test_model.objects.all()
        with pytest.raises(InvalidFieldError, match="not sortable"):
            executor.execute(qs, intent)

    def test_apply_ordering_allows_sortable_field(self, test_model):
        """Ordering by a field not in non_sortable_fields succeeds."""
        executor = DjangoExecutor(non_sortable_fields=["status", "count"])
        intent = QueryIntent(orderby=OrderIntent(fields=[OrderField(field="name", direction="asc")]))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_ordering_no_restrictions(self, executor, test_model):
        """When non_sortable_fields is None, all fields are sortable."""
        intent = QueryIntent(orderby=OrderIntent(fields=[OrderField(field="status", direction="asc")]))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_ordering_rejects_nested_non_sortable_field(self, test_model):
        """Ordering by a nested path with non-sortable base field is rejected."""
        from fc_selector.core.exceptions import InvalidFieldError

        executor = DjangoExecutor(non_sortable_fields=["related_items"])
        intent = QueryIntent(
            orderby=OrderIntent(fields=[OrderField(field="related_items.title", direction="asc")])
        )

        qs = test_model.objects.all()
        with pytest.raises(InvalidFieldError, match="not sortable"):
            executor.execute(qs, intent)


@pytest.mark.django_db
class TestApplyPagination:
    """Tests for pagination application."""

    def test_apply_pagination_limit_only(self, executor, test_model):
        """Apply limit (top) only."""
        intent = QueryIntent(pagination=PaginationIntent(limit=10))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        # Sliced queryset
        assert isinstance(result, QuerySet)

    def test_apply_pagination_offset_only(self, executor, test_model):
        """Apply offset (skip) only."""
        intent = QueryIntent(pagination=PaginationIntent(offset=5))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_pagination_limit_and_offset(self, executor, test_model):
        """Apply both limit and offset."""
        intent = QueryIntent(pagination=PaginationIntent(limit=10, offset=20))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_pagination_zero_offset(self, executor, test_model):
        """Offset of 0 is ignored."""
        intent = QueryIntent(pagination=PaginationIntent(limit=10, offset=0))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_pagination_none(self, executor, test_model):
        """None pagination does nothing."""
        intent = QueryIntent(pagination=None)

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_pagination_empty(self, executor, test_model):
        """Empty pagination (no limit/offset) does nothing."""
        intent = QueryIntent(pagination=PaginationIntent())

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)


@pytest.mark.django_db
class TestApplyExpands:
    """Tests for expand (eager loading) application."""

    def test_apply_expand_forward_relation(self, executor, related_model):
        """Expand forward relation (ForeignKey)."""
        intent = QueryIntent(expand=ExpandIntent(relations={"test_model": QueryIntent()}))

        qs = related_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_expand_reverse_relation(self, executor, test_model):
        """Expand reverse relation (related_name)."""
        intent = QueryIntent(expand=ExpandIntent(relations={"related_items": QueryIntent()}))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_expand_with_nested_filter(self, executor, test_model):
        """Expand with nested filter."""
        filter_ast = parse("value gt 5")
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={"related_items": QueryIntent(filter=FilterIntent(expression="value gt 5", ast=filter_ast))}
            )
        )

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_expand_with_nested_ordering(self, executor, test_model):
        """Expand with nested ordering."""
        intent = QueryIntent(
            expand=ExpandIntent(
                relations={
                    "related_items": QueryIntent(
                        orderby=OrderIntent(fields=[OrderField(field="title", direction="asc")])
                    )
                }
            )
        )

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_expand_with_nested_pagination(self, executor, test_model):
        """Expand with nested pagination."""
        intent = QueryIntent(
            expand=ExpandIntent(relations={"related_items": QueryIntent(pagination=PaginationIntent(limit=5))})
        )

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_expand_none(self, executor, test_model):
        """None expand does nothing."""
        intent = QueryIntent(expand=None)

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_expand_empty(self, executor, test_model):
        """Empty expand does nothing."""
        intent = QueryIntent(expand=ExpandIntent(relations={}))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)


@pytest.mark.django_db
class TestApplySelects:
    """Tests for select (field limiting) application."""

    def test_apply_select_simple(self, executor, test_model):
        """Apply simple select."""
        intent = QueryIntent(select=SelectIntent(fields=["id", "name", "count"]))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_select_with_expand(self, executor, test_model):
        """Apply select with expand (FK fields included)."""
        intent = QueryIntent(
            select=SelectIntent(fields=["id", "name"]),
            expand=ExpandIntent(relations={"related_items": QueryIntent()}),
        )

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_select_none(self, executor, test_model):
        """None select does nothing."""
        intent = QueryIntent(select=None)

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)

    def test_apply_select_empty(self, executor, test_model):
        """Empty select does nothing."""
        intent = QueryIntent(select=SelectIntent(fields=[]))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)


@pytest.mark.django_db
class TestFullExecution:
    """Integration tests for full intent execution."""

    def test_full_intent(self, executor, test_model):
        """Execute full intent with all components."""
        filter_ast = parse("count gt 0")
        intent = QueryIntent(
            filter=FilterIntent(expression="count gt 0", ast=filter_ast),
            select=SelectIntent(fields=["id", "name", "count"]),
            expand=ExpandIntent(relations={"related_items": QueryIntent()}),
            orderby=OrderIntent(fields=[OrderField(field="name", direction="asc")]),
            pagination=PaginationIntent(limit=10, offset=0),
        )

        qs = test_model.objects.all()
        result = executor.execute(qs, intent)
        assert isinstance(result, QuerySet)


@pytest.mark.django_db
class TestValuesMode:
    """Tests for use_values mode that returns dicts instead of model instances."""

    @pytest.fixture
    def now(self):
        """Return current datetime for test data."""
        return timezone.now()

    def test_values_mode_returns_dicts(self, executor, test_model, now):
        """use_values=True returns ValuesQuerySet that yields dicts."""
        ODataTestModel.objects.create(name="test1", status="draft", count=1, created_at=now)

        intent = QueryIntent(select=SelectIntent(fields=["id", "name"]))

        qs = test_model.objects.all()
        result = executor.execute(qs, intent, use_values=True)

        # Should return ValuesQuerySet
        items = list(result)
        assert len(items) >= 1
        assert isinstance(items[0], dict)
        assert "name" in items[0]

    def test_values_mode_ignored_with_expand(self, executor, test_model):
        """use_values is ignored when expand is present (returns model instances)."""
        intent = QueryIntent(
            select=SelectIntent(fields=["id", "name"]),
            expand=ExpandIntent(relations={"related_items": QueryIntent()}),
        )

        qs = test_model.objects.all()
        result = executor.execute(qs, intent, use_values=True)

        # Should NOT be ValuesQuerySet because expand is present
        # The queryset should still work with model instances
        assert isinstance(result, QuerySet)

    def test_values_mode_with_filter(self, executor, test_model, now):
        """Values mode works with filters."""
        ODataTestModel.objects.create(name="findme", status="draft", count=10, created_at=now)
        ODataTestModel.objects.create(name="other", status="draft", count=5, created_at=now)

        filter_ast = parse("name eq 'findme'")
        intent = QueryIntent(
            filter=FilterIntent(expression="name eq 'findme'", ast=filter_ast),
            select=SelectIntent(fields=["id", "name", "count"]),
        )

        qs = test_model.objects.all()
        result = executor.execute(qs, intent, use_values=True)

        items = list(result)
        assert len(items) == 1
        assert isinstance(items[0], dict)
        assert items[0]["name"] == "findme"

    def test_values_mode_with_ordering(self, executor, test_model, now):
        """Values mode works with ordering."""
        ODataTestModel.objects.create(name="aaa", status="draft", count=1, created_at=now)
        ODataTestModel.objects.create(name="zzz", status="draft", count=2, created_at=now)

        intent = QueryIntent(
            select=SelectIntent(fields=["name"]),
            orderby=OrderIntent(fields=[OrderField(field="name", direction="asc")]),
        )

        qs = test_model.objects.all()
        result = executor.execute(qs, intent, use_values=True)

        items = list(result)
        assert len(items) >= 2
        # First should be 'aaa' (alphabetically first)
        assert items[0]["name"] == "aaa"

    def test_values_mode_with_pagination(self, executor, test_model, now):
        """Values mode works with pagination."""
        for i in range(5):
            ODataTestModel.objects.create(name=f"item{i}", status="draft", count=i, created_at=now)

        intent = QueryIntent(
            select=SelectIntent(fields=["name"]),
            pagination=PaginationIntent(limit=2, offset=1),
        )

        qs = test_model.objects.all()
        result = executor.execute(qs, intent, use_values=True)

        items = list(result)
        assert len(items) == 2
        assert all(isinstance(item, dict) for item in items)

    def test_values_mode_all_fields(self, executor, test_model, now):
        """Values mode without select returns all fields."""
        ODataTestModel.objects.create(name="fulltest", status="draft", count=99, created_at=now)

        intent = QueryIntent()  # No select specified

        qs = test_model.objects.all()
        result = executor.execute(qs, intent, use_values=True)

        items = list(result)
        assert len(items) >= 1
        assert isinstance(items[0], dict)
        # Should have all model fields
        assert "name" in items[0]
        assert "status" in items[0]
        assert "count" in items[0]
