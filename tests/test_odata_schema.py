"""
Tests for OData schema generation and API documentation.

Ensures that OData query parameters are properly documented in the API schema.
"""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from fc_selector.django.drf import ODataAutoSchema
from fc_selector.django.drf.schema import get_odata_parameters_description


class TestODataAutoSchema(TestCase):
    """Test OData schema generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = APIRequestFactory()
        self.schema = ODataAutoSchema()

    def test_schema_adds_odata_parameters(self):
        """Test that schema adds all OData query parameters."""
        operation = {"parameters": []}

        result = self.schema._add_odata_parameters(operation)

        # Check that all OData parameters are present
        param_names = [p["name"] for p in result["parameters"]]

        assert "$filter" in param_names
        assert "$select" in param_names
        assert "$expand" in param_names
        assert "$orderby" in param_names
        assert "$top" in param_names
        assert "$skip" in param_names
        assert "$count" in param_names

    def test_filter_parameter_documentation(self):
        """Test that $filter parameter has comprehensive documentation."""
        operation = {"parameters": []}
        result = self.schema._add_odata_parameters(operation)

        filter_param = next((p for p in result["parameters"] if p["name"] == "$filter"), None)
        assert filter_param is not None, "$filter parameter not found"

        assert filter_param["in"] == "query"
        assert filter_param["required"] is False
        assert "eq" in filter_param["description"]
        assert "contains" in filter_param["description"]
        assert "examples" in filter_param
        assert "simple" in filter_param["examples"]

    def test_select_parameter_documentation(self):
        """Test that $select parameter has proper documentation."""
        operation = {"parameters": []}
        result = self.schema._add_odata_parameters(operation)

        select_param = next((p for p in result["parameters"] if p["name"] == "$select"), None)
        assert select_param is not None, "$select parameter not found"

        assert select_param["required"] is False
        assert "comma-separated" in select_param["description"].lower()
        assert "examples" in select_param

    def test_pagination_parameters_documentation(self):
        """Test that $top and $skip have proper documentation."""
        operation = {"parameters": []}
        result = self.schema._add_odata_parameters(operation)

        top_param = next((p for p in result["parameters"] if p["name"] == "$top"), None)
        assert top_param is not None, "$top parameter not found"
        skip_param = next((p for p in result["parameters"] if p["name"] == "$skip"), None)
        assert skip_param is not None, "$skip parameter not found"

        # Check $top
        assert top_param["schema"]["type"] == "integer"
        assert top_param["schema"]["minimum"] == 0
        assert "pagination" in top_param["description"].lower()

        # Check $skip
        assert skip_param["schema"]["type"] == "integer"
        assert skip_param["schema"]["minimum"] == 0
        assert "pagination" in skip_param["description"].lower()

    def test_expand_parameter_documentation(self):
        """Test that $expand parameter has proper documentation."""
        operation = {"parameters": []}
        result = self.schema._add_odata_parameters(operation)

        expand_param = next((p for p in result["parameters"] if p["name"] == "$expand"), None)
        assert expand_param is not None, "$expand parameter not found"

        assert "eager loading" in expand_param["description"].lower()
        assert "examples" in expand_param
        assert "nested" in expand_param["examples"]

    def test_orderby_parameter_documentation(self):
        """Test that $orderby parameter has proper documentation."""
        operation = {"parameters": []}
        result = self.schema._add_odata_parameters(operation)

        orderby_param = next((p for p in result["parameters"] if p["name"] == "$orderby"), None)
        assert orderby_param is not None, "$orderby parameter not found"

        assert "sort" in orderby_param["description"].lower()
        assert "asc" in orderby_param["description"]
        assert "desc" in orderby_param["description"]

    def test_count_parameter_documentation(self):
        """Test that $count parameter has proper documentation."""
        operation = {"parameters": []}
        result = self.schema._add_odata_parameters(operation)

        count_param = next((p for p in result["parameters"] if p["name"] == "$count"), None)
        assert count_param is not None, "$count parameter not found"

        assert count_param["schema"]["type"] == "boolean"
        assert "@odata.count" in count_param["description"]

    def test_all_parameters_have_examples(self):
        """Test that all parameters include usage examples."""
        operation = {"parameters": []}
        result = self.schema._add_odata_parameters(operation)

        params_with_examples = ["$filter", "$select", "$expand", "$orderby"]

        for param_name in params_with_examples:
            param = next((p for p in result["parameters"] if p["name"] == param_name), None)
            assert param is not None, f"{param_name} parameter not found"
            assert "examples" in param or "example" in param, f"{param_name} should have examples"

    def test_parameters_include_helpful_descriptions(self):
        """Test that all parameters have helpful, detailed descriptions."""
        operation = {"parameters": []}
        result = self.schema._add_odata_parameters(operation)

        for param in result["parameters"]:
            # All parameters should have descriptions
            assert "description" in param
            assert len(param["description"]) > 50, f"{param['name']} should have a detailed description"

            # Descriptions should include examples
            assert "example" in param["description"].lower() or "examples" in param, (
                f"{param['name']} should show examples"
            )

    def test_add_odata_parameters_creates_list_when_missing(self):
        """Test _add_odata_parameters creates parameters list when not present."""
        operation = {}  # No parameters key

        result = self.schema._add_odata_parameters(operation)

        assert "parameters" in result
        assert len(result["parameters"]) > 0

    def test_get_operation_adds_params_for_get_list(self):
        """Test get_operation adds OData params for GET list endpoints."""
        # Mock the parent get_operation
        with patch.object(ODataAutoSchema.__bases__[0], "get_operation", return_value={"parameters": []}):
            result = self.schema.get_operation("/api/posts/", "GET")

        param_names = [p["name"] for p in result.get("parameters", [])]
        assert "$filter" in param_names

    def test_get_operation_skips_params_for_get_detail(self):
        """Test get_operation skips OData params for GET detail endpoints."""
        # Mock the parent get_operation
        with patch.object(ODataAutoSchema.__bases__[0], "get_operation", return_value={"parameters": []}):
            result = self.schema.get_operation("/api/posts/{id}", "GET")

        # Should not add OData params for detail endpoints
        param_names = [p["name"] for p in result.get("parameters", [])]
        assert "$filter" not in param_names

    def test_get_operation_skips_params_for_post(self):
        """Test get_operation skips OData params for POST requests."""
        with patch.object(ODataAutoSchema.__bases__[0], "get_operation", return_value={"parameters": []}):
            result = self.schema.get_operation("/api/posts/", "POST")

        param_names = [p["name"] for p in result.get("parameters", [])]
        assert "$filter" not in param_names


class TestGetODataParametersDescription(TestCase):
    """Test get_odata_parameters_description function."""

    def test_returns_string(self):
        """Test function returns string."""
        result = get_odata_parameters_description()
        assert isinstance(result, str)

    def test_includes_all_parameters(self):
        """Test description includes all OData parameters."""
        result = get_odata_parameters_description()

        assert "$filter" in result
        assert "$select" in result
        assert "$expand" in result
        assert "$orderby" in result
        assert "$top" in result
        assert "$skip" in result
        assert "$count" in result

    def test_includes_markdown_formatting(self):
        """Test description uses markdown."""
        result = get_odata_parameters_description()

        # Should have markdown headers
        assert "##" in result or "**" in result

    def test_includes_examples(self):
        """Test description includes examples."""
        result = get_odata_parameters_description()

        assert "Example" in result
        assert "eq" in result  # Filter example
        assert "desc" in result  # Orderby example
