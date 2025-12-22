"""
Tests for OData pagination parameter validation.

Tests ensure that $top and $skip parameters are properly validated
and provide helpful error messages when invalid values are provided.
"""

import pytest
from django.contrib.auth.models import User
from django.test import TestCase

from fc_selector.django.query.applier import apply_odata_query_params
from fc_selector.exceptions import ODataInvalidPaginationError


class TestPaginationValidation(TestCase):
    """Test validation of $top and $skip parameters."""

    @classmethod
    def setUpTestData(cls):
        """Create test data once for all tests."""
        # Create 20 test users
        for i in range(20):
            User.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@example.com",
            )

    def test_valid_top(self):
        """Test that valid $top values work correctly."""
        queryset = User.objects.all()
        result = apply_odata_query_params(queryset, {"$top": "10"})

        assert result.count() == 10

    def test_valid_skip(self):
        """Test that valid $skip values work correctly."""
        queryset = User.objects.all()
        result = apply_odata_query_params(queryset, {"$skip": "5"})

        assert result.count() == 15  # 20 - 5

    def test_valid_top_and_skip(self):
        """Test that valid $top and $skip combination works."""
        queryset = User.objects.all()
        result = apply_odata_query_params(queryset, {"$top": "10", "$skip": "5"})

        assert result.count() == 10

    def test_invalid_top_string(self):
        """Test that invalid $top string raises error with helpful message."""
        queryset = User.objects.all()

        with pytest.raises(ODataInvalidPaginationError) as exc_info:
            apply_odata_query_params(queryset, {"$top": "abc"})

        error = exc_info.value
        assert error.target == "$top"
        assert "abc" in str(error)
        assert "positive integer" in str(error)

    def test_invalid_skip_string(self):
        """Test that invalid $skip string raises error."""
        queryset = User.objects.all()

        with pytest.raises(ODataInvalidPaginationError) as exc_info:
            apply_odata_query_params(queryset, {"$skip": "xyz"})

        error = exc_info.value
        assert error.target == "$skip"
        assert "xyz" in str(error)

    def test_negative_top(self):
        """Test that negative $top value raises error."""
        queryset = User.objects.all()

        with pytest.raises(ODataInvalidPaginationError) as exc_info:
            apply_odata_query_params(queryset, {"$top": "-5"})

        error = exc_info.value
        assert error.target == "$top"

    def test_negative_skip(self):
        """Test that negative $skip value raises error."""
        queryset = User.objects.all()

        with pytest.raises(ODataInvalidPaginationError) as exc_info:
            apply_odata_query_params(queryset, {"$skip": "-10"})

        error = exc_info.value
        assert error.target == "$skip"

    def test_top_with_missing_ampersand(self):
        """
        Test the common mistake: ?$top=5$skip=5 instead of ?$top=5&$skip=5

        This simulates what happens when Django receives a malformed URL where
        the user forgot to use '&' between parameters.
        """
        queryset = User.objects.all()

        # When user types ?$top=5$skip=5, Django sees $top="5$skip=5"
        with pytest.raises(ODataInvalidPaginationError) as exc_info:
            apply_odata_query_params(queryset, {"$top": "5$skip=5"})

        error = exc_info.value
        assert error.target == "$top"
        assert "5$skip=5" in str(error)
        # Check that the helpful suggestion is included
        assert "&" in str(error)
        assert "?" in str(error)
        assert "Example:" in str(error) or "Did you forget" in str(error)

    def test_skip_with_missing_ampersand(self):
        """Test error message when $skip contains another parameter."""
        queryset = User.objects.all()

        # Simulate: ?$skip=10$count=true (missing &)
        with pytest.raises(ODataInvalidPaginationError) as exc_info:
            apply_odata_query_params(queryset, {"$skip": "10$count=true"})

        error = exc_info.value
        assert error.target == "$skip"
        assert "$" in str(error.details["invalid_value"])

    def test_float_top(self):
        """Test that float values are rejected."""
        queryset = User.objects.all()

        with pytest.raises(ODataInvalidPaginationError) as exc_info:
            apply_odata_query_params(queryset, {"$top": "10.5"})

        error = exc_info.value
        assert error.target == "$top"

    def test_zero_top(self):
        """Test that $top=0 is valid and returns empty result."""
        queryset = User.objects.all()
        result = apply_odata_query_params(queryset, {"$top": "0"})

        # $top=0 should work but return no results
        assert result.count() == 0

    def test_zero_skip(self):
        """Test that $skip=0 is valid and returns all results."""
        queryset = User.objects.all()
        result = apply_odata_query_params(queryset, {"$skip": "0"})

        # $skip=0 should return all results
        assert result.count() == 20

    def test_large_pagination_values(self):
        """Test that large valid values work correctly."""
        queryset = User.objects.all()

        # Large skip that exceeds dataset
        result = apply_odata_query_params(queryset, {"$skip": "100"})
        assert result.count() == 0

        # Large top
        result = apply_odata_query_params(queryset, {"$top": "1000"})
        assert result.count() == 20  # Can't exceed available records
