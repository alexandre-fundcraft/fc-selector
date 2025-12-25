"""
Tests for ODataSelector.

Covers fc_selector/django/selector/odata_selector.py
"""

import pytest
from django.db.models import QuerySet

from fc_selector.core.query_builder import QueryBuilder
from fc_selector.django.selector import ODataSelector


@pytest.fixture
def test_model():
    """Fixture for test model."""
    from tests.integration.support.models import ODataTestModel

    return ODataTestModel


@pytest.fixture
def related_model():
    """Fixture for related model."""
    from tests.integration.support.models import ODataRelatedModel

    return ODataRelatedModel


def create_selector(model):
    """Create a selector with Meta class for the given model."""

    class TestSelector(ODataSelector):
        class Meta:
            pass

    TestSelector.Meta.model = model
    return TestSelector()


@pytest.mark.django_db
class TestODataSelectorInit:
    """Tests for ODataSelector initialization."""

    def test_init_without_meta_raises_error(self):
        """Initialization without Meta class raises ValueError."""
        with pytest.raises(ValueError, match="must define a Meta class"):
            ODataSelector()

    def test_init_with_meta_class(self, test_model):
        """Initialize with Meta class configuration."""

        class TestSelector(ODataSelector):
            class Meta:
                model = test_model
                dto_class = None
                expandable_fields = {"related_items": True}
                field_aliases = {"title": "name"}
                allowed_fields = ["id", "name"]
                filterable_fields = ["name"]
                sortable_fields = ["name"]
                default_ordering = ["-name"]
                default_limit = 50
                max_limit = 200

        selector = TestSelector()
        assert selector.model is test_model
        assert selector.expandable_fields == {"related_items": True}
        assert selector.field_aliases == {"title": "name"}
        assert selector.allowed_fields == ["id", "name"]
        assert selector.filterable_fields == ["name"]
        assert selector.sortable_fields == ["name"]
        assert selector.default_ordering == ["-name"]
        assert selector.default_limit == 50
        assert selector.max_limit == 200

    def test_init_with_meta_defaults(self, test_model):
        """Initialize with Meta class using defaults."""

        class TestSelector(ODataSelector):
            class Meta:
                model = test_model

        selector = TestSelector()
        assert selector.model is test_model
        assert selector.dto_class is None
        assert selector.expandable_fields == {}
        assert selector.field_aliases == {}
        assert selector.allowed_fields is None  # None means all fields allowed
        assert selector.filterable_fields == []
        assert selector.sortable_fields == []
        assert selector.default_ordering == []
        assert selector.default_limit == 100
        assert selector.max_limit == 500

    def test_init_without_model_raises_on_get_queryset(self, test_model):
        """Initialization with empty Meta doesn't raise until get_queryset."""

        class TestSelector(ODataSelector):
            class Meta:
                pass

        selector = TestSelector()
        assert selector.model is None

        with pytest.raises(ValueError, match="model not configured"):
            selector.get_queryset()


@pytest.mark.django_db
class TestGetQueryset:
    """Tests for get_queryset method."""

    def test_get_queryset_basic(self, test_model):
        """get_queryset returns all objects."""
        selector = create_selector(test_model)
        qs = selector.get_queryset()
        assert isinstance(qs, QuerySet)
        assert qs.model is test_model


@pytest.mark.django_db
class TestQuery:
    """Tests for query method."""

    def test_query_empty_string(self, test_model):
        """Empty query string returns base queryset."""
        selector = create_selector(test_model)
        qs = selector.query("")
        assert isinstance(qs, QuerySet)

    def test_query_none(self, test_model):
        """None query string returns base queryset."""
        selector = create_selector(test_model)
        qs = selector.query(None)
        assert isinstance(qs, QuerySet)

    def test_query_with_filter(self, test_model):
        """Query with filter."""
        selector = create_selector(test_model)
        qs = selector.query("$filter=count gt 0")
        assert isinstance(qs, QuerySet)

    def test_query_with_select(self, test_model):
        """Query with select."""
        selector = create_selector(test_model)
        qs = selector.query("$select=id,name,count")
        assert isinstance(qs, QuerySet)

    def test_query_with_orderby(self, test_model):
        """Query with orderby."""
        selector = create_selector(test_model)
        qs = selector.query("$orderby=name desc")
        assert isinstance(qs, QuerySet)

    def test_query_with_top_skip(self, test_model):
        """Query with top and skip."""
        selector = create_selector(test_model)
        qs = selector.query("$top=10&$skip=5")
        assert isinstance(qs, QuerySet)

    def test_query_with_model_class_override(self, test_model, related_model):
        """Query with model_class parameter used for validation fallback."""

        class TestSelector(ODataSelector):
            class Meta:
                pass

        selector = TestSelector()
        base_qs = related_model.objects.all()
        qs = selector.query("$top=5", model_class=related_model, base_queryset=base_qs)
        assert qs.model is related_model

    def test_query_with_base_queryset(self, test_model):
        """Query with custom base queryset."""
        selector = create_selector(test_model)
        base_qs = test_model.objects.filter(is_active=True)
        qs = selector.query("$top=5", base_queryset=base_qs)
        assert isinstance(qs, QuerySet)

    def test_query_without_model_raises(self):
        """Query without model raises ValueError."""

        class TestSelector(ODataSelector):
            class Meta:
                pass

        selector = TestSelector()
        with pytest.raises(ValueError, match="model_class required"):
            selector.query("$top=10")


@pytest.mark.django_db
class TestExecute:
    """Tests for execute method."""

    def test_execute_with_intent(self, test_model):
        """Execute with QueryIntent."""
        from fc_selector.core.intent import PaginationIntent, QueryIntent

        selector = create_selector(test_model)
        intent = QueryIntent(pagination=PaginationIntent(limit=5))
        qs = selector.execute(intent)
        assert isinstance(qs, QuerySet)

    def test_execute_with_base_queryset(self, test_model):
        """Execute with custom base queryset."""
        from fc_selector.core.intent import QueryIntent

        selector = create_selector(test_model)
        base_qs = test_model.objects.filter(is_active=True)
        intent = QueryIntent()
        qs = selector.execute(intent, base_queryset=base_qs)
        assert isinstance(qs, QuerySet)


@pytest.mark.django_db
class TestAliasResolution:
    """Tests for field alias resolution."""

    def test_resolve_aliases_in_filter(self, test_model):
        """Aliases are resolved in $filter."""

        class AliasedSelector(ODataSelector):
            class Meta:
                model = test_model
                field_aliases = {"title": "name"}

        selector = AliasedSelector()
        resolved = selector._resolve_aliases_in_query_string("$filter=title eq 'test'")
        assert "name eq 'test'" in resolved

    def test_resolve_aliases_in_select(self, test_model):
        """Aliases are resolved in $select."""

        class AliasedSelector(ODataSelector):
            class Meta:
                model = test_model
                field_aliases = {"title": "name", "qty": "count"}

        selector = AliasedSelector()
        resolved = selector._resolve_aliases_in_query_string("$select=id,title,qty")
        assert "name" in resolved
        assert "count" in resolved

    def test_resolve_aliases_in_orderby(self, test_model):
        """Aliases are resolved in $orderby."""

        class AliasedSelector(ODataSelector):
            class Meta:
                model = test_model
                field_aliases = {"title": "name"}

        selector = AliasedSelector()
        resolved = selector._resolve_aliases_in_query_string("$orderby=title desc")
        assert "name desc" in resolved

    def test_resolve_aliases_empty_query(self, test_model):
        """Empty query returns empty."""

        class AliasedSelector(ODataSelector):
            class Meta:
                model = test_model
                field_aliases = {"title": "name"}

        selector = AliasedSelector()
        resolved = selector._resolve_aliases_in_query_string("")
        assert resolved == ""

    def test_resolve_aliases_no_aliases(self, test_model):
        """No aliases returns unchanged query."""
        selector = create_selector(test_model)
        query = "$filter=name eq 'test'"
        resolved = selector._resolve_aliases_in_query_string(query)
        assert resolved == query

    def test_resolve_aliases_in_filter_preserves_string_literals(self, test_model):
        """Aliases in string literals are not replaced."""

        class AliasedSelector(ODataSelector):
            class Meta:
                model = test_model
                field_aliases = {"eq": "internal_eq"}

        selector = AliasedSelector()
        resolved = selector._resolve_aliases_in_filter("name eq 'test'")
        assert "eq" in resolved


@pytest.mark.django_db
class TestQueryBuilderMethods:
    """Tests for QueryBuilder integration methods."""

    def test_count_by(self, test_model):
        """count_by returns integer count."""
        selector = create_selector(test_model)
        count = selector.count_by()
        assert isinstance(count, int)

    def test_count_by_with_query(self, test_model):
        """count_by with query builder."""
        selector = create_selector(test_model)
        qb = QueryBuilder().filter("count gt 0")
        count = selector.count_by(qb)
        assert isinstance(count, int)

    def test_exists_by(self, test_model):
        """exists_by returns boolean."""
        selector = create_selector(test_model)
        exists = selector.exists_by()
        assert isinstance(exists, bool)

    def test_exists_by_with_query(self, test_model):
        """exists_by with query builder."""
        selector = create_selector(test_model)
        qb = QueryBuilder().filter("count gt 0")
        exists = selector.exists_by(qb)
        assert isinstance(exists, bool)
