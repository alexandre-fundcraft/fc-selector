"""
Tests for miscellaneous utility modules with low coverage.

Covers:
- fc_selector/protocols/odata/parsers/filter/typing.py
- fc_selector/protocols/odata/parsers/filter/utils.py
- fc_selector/django/visitors/django_q_ext.py
- fc_selector/django/drf/spectacular.py
"""

from unittest.mock import MagicMock

import pytest

from fc_selector.core import ast
from fc_selector.django.visitors.django_q_ext import NotEqual
from fc_selector.protocols.odata.parsers.filter.exceptions import (
    ArgumentTypeException,
)
from fc_selector.protocols.odata.parsers.filter.typing import typecheck
from fc_selector.protocols.odata.parsers.filter.utils import (
    expression_relative_to_identifier,
)


class TestFilterTyping:
    """Tests for fc_selector/protocols/odata/parsers/filter/typing.py."""

    def test_typecheck_single_type_pass(self):
        """Typecheck passes for matching single type."""
        node = ast.String("test")
        # Should not raise
        typecheck(node, ast.String, "test_field")

    def test_typecheck_single_type_fail(self):
        """Typecheck fails for non-matching single type."""
        node = ast.String("test")
        with pytest.raises(ArgumentTypeException):
            typecheck(node, ast.Integer, "test_field")

    def test_typecheck_tuple_type_pass(self):
        """Typecheck passes for matching tuple type."""
        node = ast.String("test")
        # Should not raise - matches one of the types
        typecheck(node, (ast.String, ast.Integer), "test_field")

    def test_typecheck_tuple_type_fail(self):
        """Typecheck fails for non-matching tuple type."""
        node = ast.Boolean("true")
        with pytest.raises(ArgumentTypeException):
            typecheck(node, (ast.String, ast.Integer), "test_field")


class TestFilterUtils:
    """Tests for fc_selector/protocols/odata/parsers/filter/utils.py."""

    def test_expression_relative_to_identifier(self):
        """expression_relative_to_identifier strips identifier from expression."""
        identifier = ast.Identifier("x")
        # x/name becomes just name
        attr_node = ast.Attribute(owner=ast.Identifier("x"), attr="name")
        result = expression_relative_to_identifier(identifier, attr_node)

        assert isinstance(result, ast.Identifier)
        assert result.name == "name"

    def test_expression_relative_non_matching(self):
        """Non-matching identifier is unchanged."""
        identifier = ast.Identifier("x")
        # y/name stays y/name
        attr_node = ast.Attribute(owner=ast.Identifier("y"), attr="name")
        result = expression_relative_to_identifier(identifier, attr_node)

        assert isinstance(result, ast.Attribute)
        assert result.attr == "name"


@pytest.mark.django_db
class TestNotEqualLookup:
    """Tests for fc_selector/django/visitors/django_q_ext.py NotEqual lookup."""

    def test_not_equal_lookup_class(self):
        """NotEqual lookup class exists and has correct lookup_name."""
        assert NotEqual.lookup_name == "ne"

    def test_not_equal_as_sql(self):
        """NotEqual lookup generates correct SQL."""
        # Create mock lookup
        lookup = NotEqual.__new__(NotEqual)
        lookup.lhs = MagicMock()
        lookup.rhs = MagicMock()

        # Mock process_lhs and process_rhs
        lookup.process_lhs = MagicMock(return_value=("col1", []))
        lookup.process_rhs = MagicMock(return_value=("'test'", ["test"]))

        # Test SQL generation using Django's parameterized query interface
        # This is safe because params are properly separated from SQL string
        sql, params = lookup.as_sql(MagicMock(), MagicMock())  # nosec B608 - Testing SQL generation
        assert "<>" in sql
        assert sql == "col1 <> 'test'"
        assert params == ["test"]


class TestSpectacularIntegration:
    """Tests for fc_selector/django/drf/spectacular.py."""

    def test_odata_parameters_list(self):
        """ODATA_PARAMETERS contains expected parameters."""
        from fc_selector.django.drf.spectacular import ODATA_PARAMETERS  # noqa: PLC0415

        param_names = [p.name for p in ODATA_PARAMETERS]
        assert param_names == ["$filter", "$select", "$expand", "$orderby", "$top", "$skip", "$count"]

    def test_odata_retrieve_parameters(self):
        """ODATA_RETRIEVE_PARAMETERS has subset for retrieve."""
        from fc_selector.django.drf.spectacular import ODATA_RETRIEVE_PARAMETERS  # noqa: PLC0415

        param_names = [p.name for p in ODATA_RETRIEVE_PARAMETERS]
        assert param_names == ["$select", "$expand"]
