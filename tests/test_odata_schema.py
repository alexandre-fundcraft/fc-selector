"""
Tests for OData schema generation and API documentation.

Ensures that OData query parameters are properly documented in the API schema.
"""

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from fc_selector.django.drf import ODataAutoSchema, ODataModelViewSet


class TestODataAutoSchema(TestCase):
    """Test OData schema generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = APIRequestFactory()
        self.schema = ODataAutoSchema()

    def test_schema_adds_odata_parameters(self):
        """Test that schema adds all OData query parameters."""
        operation = {
            'parameters': []
        }

        result = self.schema._add_odata_parameters(operation)

        # Check that all OData parameters are present
        param_names = [p['name'] for p in result['parameters']]

        assert '$filter' in param_names
        assert '$select' in param_names
        assert '$expand' in param_names
        assert '$orderby' in param_names
        assert '$top' in param_names
        assert '$skip' in param_names
        assert '$count' in param_names

    def test_filter_parameter_documentation(self):
        """Test that $filter parameter has comprehensive documentation."""
        operation = {'parameters': []}
        result = self.schema._add_odata_parameters(operation)

        filter_param = next(p for p in result['parameters'] if p['name'] == '$filter')

        assert filter_param['in'] == 'query'
        assert filter_param['required'] is False
        assert 'eq' in filter_param['description']
        assert 'contains' in filter_param['description']
        assert 'examples' in filter_param
        assert 'simple' in filter_param['examples']

    def test_select_parameter_documentation(self):
        """Test that $select parameter has proper documentation."""
        operation = {'parameters': []}
        result = self.schema._add_odata_parameters(operation)

        select_param = next(p for p in result['parameters'] if p['name'] == '$select')

        assert select_param['required'] is False
        assert 'comma-separated' in select_param['description'].lower()
        assert 'examples' in select_param

    def test_pagination_parameters_documentation(self):
        """Test that $top and $skip have proper documentation."""
        operation = {'parameters': []}
        result = self.schema._add_odata_parameters(operation)

        top_param = next(p for p in result['parameters'] if p['name'] == '$top')
        skip_param = next(p for p in result['parameters'] if p['name'] == '$skip')

        # Check $top
        assert top_param['schema']['type'] == 'integer'
        assert top_param['schema']['minimum'] == 0
        assert 'pagination' in top_param['description'].lower()

        # Check $skip
        assert skip_param['schema']['type'] == 'integer'
        assert skip_param['schema']['minimum'] == 0
        assert 'pagination' in skip_param['description'].lower()

    def test_expand_parameter_documentation(self):
        """Test that $expand parameter has proper documentation."""
        operation = {'parameters': []}
        result = self.schema._add_odata_parameters(operation)

        expand_param = next(p for p in result['parameters'] if p['name'] == '$expand')

        assert 'eager loading' in expand_param['description'].lower()
        assert 'examples' in expand_param
        assert 'nested' in expand_param['examples']

    def test_orderby_parameter_documentation(self):
        """Test that $orderby parameter has proper documentation."""
        operation = {'parameters': []}
        result = self.schema._add_odata_parameters(operation)

        orderby_param = next(p for p in result['parameters'] if p['name'] == '$orderby')

        assert 'sort' in orderby_param['description'].lower()
        assert 'asc' in orderby_param['description']
        assert 'desc' in orderby_param['description']

    def test_count_parameter_documentation(self):
        """Test that $count parameter has proper documentation."""
        operation = {'parameters': []}
        result = self.schema._add_odata_parameters(operation)

        count_param = next(p for p in result['parameters'] if p['name'] == '$count')

        assert count_param['schema']['type'] == 'boolean'
        assert '@odata.count' in count_param['description']

    def test_odata_model_viewset_has_schema(self):
        """Test that ODataModelViewSet has schema configured."""
        assert hasattr(ODataModelViewSet, 'schema')
        assert isinstance(ODataModelViewSet.schema, ODataAutoSchema)

    def test_all_parameters_have_examples(self):
        """Test that all parameters include usage examples."""
        operation = {'parameters': []}
        result = self.schema._add_odata_parameters(operation)

        params_with_examples = ['$filter', '$select', '$expand', '$orderby']

        for param_name in params_with_examples:
            param = next(p for p in result['parameters'] if p['name'] == param_name)
            assert 'examples' in param or 'example' in param, \
                f"{param_name} should have examples"

    def test_parameters_include_helpful_descriptions(self):
        """Test that all parameters have helpful, detailed descriptions."""
        operation = {'parameters': []}
        result = self.schema._add_odata_parameters(operation)

        for param in result['parameters']:
            # All parameters should have descriptions
            assert 'description' in param
            assert len(param['description']) > 50, \
                f"{param['name']} should have a detailed description"

            # Descriptions should include examples
            assert 'example' in param['description'].lower() or 'examples' in param, \
                f"{param['name']} should show examples"
