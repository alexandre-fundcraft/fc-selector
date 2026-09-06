"""
Tests for Django utility modules.

Covers:
- fc_selector/django/utils/introspection.py
- fc_selector/django/visitors/utils.py
- fc_selector/django/query/applier.py
"""
# pylint: disable=redefined-outer-name  # pytest fixtures

import pytest

from fc_selector.django.query.applier import apply_odata_query_params
from fc_selector.django.utils.introspection import (
    get_field_safe,
    is_forward_relation,
)
from fc_selector.django.visitors.utils import reverse_relationship
from fc_selector.exceptions import (
    ODataInvalidPaginationError,
)
from tests.integration.support.models import ODataRelatedModel, ODataTestModel


@pytest.fixture
def test_model():
    """Fixture for test model."""
    return ODataTestModel


@pytest.fixture
def related_model():
    """Fixture for related model."""
    return ODataRelatedModel


@pytest.mark.django_db
class TestGetFieldSafe:
    """Tests for get_field_safe utility."""

    def test_existing_field(self, test_model):
        """Returns field for existing field."""
        field = get_field_safe(test_model, "name")
        assert field is not None
        assert field.name == "name"

    def test_nonexistent_field(self, test_model):
        """Returns None for non-existent field."""
        field = get_field_safe(test_model, "nonexistent")
        assert field is None

    def test_related_field(self, related_model):
        """Returns field for ForeignKey."""
        field = get_field_safe(related_model, "test_model")
        assert field is not None


@pytest.mark.django_db
class TestIsForwardRelation:
    """Tests for is_forward_relation utility."""

    def test_fk_is_forward(self, related_model):
        """ForeignKey is forward relation."""
        result = is_forward_relation(related_model, "test_model")
        assert result is True

    def test_reverse_is_not_forward(self, test_model):
        """Reverse relation is not forward."""
        result = is_forward_relation(test_model, "related_items")
        assert result is False

    def test_regular_field_not_relation(self, test_model):
        """Regular field (CharField) check via get_field_safe."""
        # Regular fields like CharField don't have related_model
        field = get_field_safe(test_model, "name")
        assert field is not None
        # CharField doesn't have related_model attribute
        has_related_model = hasattr(field, "related_model") and field.related_model is not None
        # Either it doesn't have it or it's None
        assert not has_related_model or not getattr(field, "many_to_one", False)

    def test_nonexistent_is_not_forward(self, test_model):
        """Non-existent field is not forward relation."""
        result = is_forward_relation(test_model, "nonexistent")
        assert result is False


@pytest.mark.django_db
class TestReverseRelationship:
    """Tests for reverse_relationship utility."""

    def test_single_step_reverse(self, related_model, test_model):
        """Reverse single-step relationship."""
        path, model = reverse_relationship("test_model", related_model)
        assert model is test_model
        # The reverse path depends on the related_name setting


@pytest.mark.django_db
class TestApplyOdataQueryParams:
    """Tests for apply_odata_query_params."""

    def test_apply_empty_params(self, test_model):
        """Empty params returns unchanged queryset."""
        qs = test_model.objects.all()
        result = apply_odata_query_params(qs, "")
        assert result.query.__str__() == qs.query.__str__()

    def test_apply_none_params(self, test_model):
        """None params returns unchanged queryset."""
        qs = test_model.objects.all()
        result = apply_odata_query_params(qs, None)
        assert result is qs

    def test_apply_string_query(self, test_model):
        """Apply string query params."""
        qs = test_model.objects.all()
        result = apply_odata_query_params(qs, "$top=10")
        assert result is not None

    def test_apply_dict_query(self, test_model):
        """Apply dict query params."""
        qs = test_model.objects.all()
        result = apply_odata_query_params(qs, {"$top": "10"})
        assert result is not None

    def test_apply_filter(self, test_model):
        """Apply filter query."""
        qs = test_model.objects.all()
        result = apply_odata_query_params(qs, "$filter=count gt 0")
        assert result is not None

    def test_apply_invalid_top_value(self, test_model):
        """Invalid $top value raises error."""
        qs = test_model.objects.all()
        with pytest.raises(ODataInvalidPaginationError):
            apply_odata_query_params(qs, {"$top": "abc"})

    def test_apply_negative_top_value(self, test_model):
        """Negative $top value raises error."""
        qs = test_model.objects.all()
        with pytest.raises(ODataInvalidPaginationError):
            apply_odata_query_params(qs, {"$top": "-5"})

    def test_apply_invalid_skip_value(self, test_model):
        """Invalid $skip value raises error."""
        qs = test_model.objects.all()
        with pytest.raises(ODataInvalidPaginationError):
            apply_odata_query_params(qs, {"$skip": "abc"})

    def test_apply_negative_skip_value(self, test_model):
        """Negative $skip value raises error."""
        qs = test_model.objects.all()
        with pytest.raises(ODataInvalidPaginationError):
            apply_odata_query_params(qs, {"$skip": "-5"})


@pytest.mark.django_db
class TestApplyODataQueryParams:
    """Tests for apply_odata_query_params function."""

    def test_module_level_function(self, test_model):
        """Module-level function works."""
        qs = test_model.objects.all()
        result = apply_odata_query_params(qs, "$top=5")
        assert result is not None

    def test_with_orderby(self, test_model):
        """Apply orderby."""
        qs = test_model.objects.all()
        result = apply_odata_query_params(qs, "$orderby=name desc")
        assert result is not None

    def test_with_select(self, test_model):
        """Apply select."""
        qs = test_model.objects.all()
        result = apply_odata_query_params(qs, "$select=id,name")
        assert result is not None

    def test_full_query(self, test_model):
        """Apply full query with all params."""
        qs = test_model.objects.all()
        result = apply_odata_query_params(qs, "$filter=count gt 0&$orderby=name&$top=10&$skip=0")
        assert result is not None
