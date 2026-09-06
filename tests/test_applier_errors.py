"""
Tests for applier.py error handling paths.

Covers fc_selector/django/query/applier.py error handling branches.
"""
# pylint: disable=redefined-outer-name  # pytest fixtures

from unittest.mock import patch

import pytest
from django.db.models import QuerySet

from fc_selector.core import exceptions as core_ex
from fc_selector.django.executor import DjangoExecutor
from fc_selector.django.query.applier import apply_odata_query_params
from fc_selector.exceptions import (
    ODataFieldNotFoundError,
    ODataFilterError,
    ODataInvalidValueError,
)
from tests.integration.support.models import ODataTestModel


@pytest.fixture
def test_model():
    """Fixture for test model."""
    return ODataTestModel


@pytest.fixture
def queryset(test_model):
    """Fixture for queryset."""
    return test_model.objects.all()


@pytest.mark.django_db
class TestApplierErrorHandling:
    """Tests for apply_odata_query_params error handling paths."""

    def test_field_not_found_error_conversion(self, queryset):
        """FieldNotFoundError is converted to ODataFieldNotFoundError."""
        with patch.object(
            DjangoExecutor,
            "execute",
            side_effect=core_ex.FieldNotFoundError("nonexistent_field", "TestModel"),
        ):
            with pytest.raises(ODataFieldNotFoundError) as exc_info:
                apply_odata_query_params(queryset, "$top=5")

            # Check the details dict contains field info
            assert exc_info.value.details["field"] == "nonexistent_field"
            assert "TestModel" in exc_info.value.details["entity"]

    def test_field_not_found_error_without_model_name(self, queryset):
        """FieldNotFoundError without model_name uses queryset model."""
        with patch.object(
            DjangoExecutor,
            "execute",
            side_effect=core_ex.FieldNotFoundError("unknown_field"),
        ):
            with pytest.raises(ODataFieldNotFoundError) as exc_info:
                apply_odata_query_params(queryset, "$top=5")

            assert exc_info.value.details["field"] == "unknown_field"
            # Should use queryset model name when e.model_name is None
            assert "ODataTestModel" in exc_info.value.details["entity"]

    def test_invalid_value_error_conversion(self, queryset):
        """InvalidValueError is converted to ODataInvalidValueError."""
        with patch.object(
            DjangoExecutor,
            "execute",
            side_effect=core_ex.InvalidValueError("bad_value", expected_type="Integer"),
        ):
            with pytest.raises(ODataInvalidValueError) as exc_info:
                apply_odata_query_params(queryset, "$top=5")

            assert exc_info.value.details["value"] == "bad_value"
            assert exc_info.value.details["expected_type"] == "Integer"

    def test_invalid_value_error_without_expected_type(self, queryset):
        """InvalidValueError without expected_type defaults to 'unknown'."""
        with patch.object(
            DjangoExecutor,
            "execute",
            side_effect=core_ex.InvalidValueError("bad"),
        ):
            with pytest.raises(ODataInvalidValueError) as exc_info:
                apply_odata_query_params(queryset, "$top=5")

            assert exc_info.value.details["expected_type"] == "unknown"

    def test_query_error_conversion(self, queryset):
        """QueryError is converted to ODataFilterError."""
        with patch.object(
            DjangoExecutor,
            "execute",
            side_effect=core_ex.QueryError("Query processing failed"),
        ):
            with pytest.raises(ODataFilterError) as exc_info:
                apply_odata_query_params(queryset, "$top=5")

            assert exc_info.value.error_code == "QueryError"
            assert exc_info.value.target == "$filter"
            assert "Query processing failed" in exc_info.value.message

    def test_selector_error_conversion(self, queryset):
        """SelectorError is converted to ODataFilterError."""
        with patch.object(
            DjangoExecutor,
            "execute",
            side_effect=core_ex.SelectorError("Selector error"),
        ):
            with pytest.raises(ODataFilterError) as exc_info:
                apply_odata_query_params(queryset, "$top=5")

            assert exc_info.value.error_code == "QueryError"

    def test_generic_value_error_conversion(self, queryset):
        """ValueError is converted to ODataFilterError."""
        with patch.object(
            DjangoExecutor,
            "execute",
            side_effect=ValueError("Invalid value"),
        ):
            with pytest.raises(ODataFilterError) as exc_info:
                apply_odata_query_params(queryset, "$top=5")

            assert exc_info.value.error_code == "InvalidQuery"
            assert "Invalid value" in exc_info.value.message

    def test_generic_type_error_conversion(self, queryset):
        """TypeError is converted to ODataFilterError."""
        with patch.object(
            DjangoExecutor,
            "execute",
            side_effect=TypeError("Type mismatch"),
        ):
            with pytest.raises(ODataFilterError) as exc_info:
                apply_odata_query_params(queryset, "$top=5")

            assert exc_info.value.error_code == "InvalidQuery"
            assert "Type mismatch" in exc_info.value.message

    def test_attribute_error_conversion(self, queryset):
        """AttributeError is converted to ODataFilterError."""
        with patch.object(
            DjangoExecutor,
            "execute",
            side_effect=AttributeError("Missing attribute"),
        ):
            with pytest.raises(ODataFilterError) as exc_info:
                apply_odata_query_params(queryset, "$top=5")

            assert exc_info.value.error_code == "InvalidQuery"

    def test_key_error_conversion(self, queryset):
        """KeyError is converted to ODataFilterError."""
        with patch.object(
            DjangoExecutor,
            "execute",
            side_effect=KeyError("missing_key"),
        ):
            with pytest.raises(ODataFilterError) as exc_info:
                apply_odata_query_params(queryset, "$top=5")

            assert exc_info.value.error_code == "InvalidQuery"


@pytest.mark.django_db
class TestApplyOdataQueryParamsFunction:
    """Tests for the module-level apply_odata_query_params function."""

    def test_apply_odata_query_params_empty(self, queryset):
        """Empty query string returns the queryset untouched."""
        result = apply_odata_query_params(queryset, "")
        assert isinstance(result, QuerySet)

    def test_apply_odata_query_params_with_filter(self, queryset):
        """apply_odata_query_params handles filter."""
        result = apply_odata_query_params(queryset, "$filter=count ge 0")
        assert isinstance(result, QuerySet)
