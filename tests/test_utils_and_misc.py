"""
Tests for miscellaneous utility modules with low coverage.

Covers:
- fc_selector/utils.py (re-exports)
- fc_selector/core/__init__.py (lazy imports)
- fc_selector/protocols/odata/parsers/filter/typing.py
- fc_selector/protocols/odata/parsers/filter/utils.py
- fc_selector/django/visitors/django_q_ext.py
- fc_selector/core/dtos/converter.py
- fc_selector/django/drf/spectacular.py
- fc_selector/django/drf/mixins/serializer_mixin.py
"""

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from rest_framework import serializers

from fc_selector import core
from fc_selector.core import QueryBuilder, ast
from fc_selector.core.dtos.base import BaseODataDTO
from fc_selector.core.dtos.converter import DTOConverter
from fc_selector.django.drf.mixins.serializer_mixin import ODataSerializerMixin
from fc_selector.django.drf.spectacular import (
    get_odata_parameters,
    get_odata_retrieve_parameters,
)
from fc_selector.django.visitors.django_q_ext import NotEqual
from fc_selector.protocols.odata.parsers.filter.exceptions import (
    ArgumentTypeException,
)
from fc_selector.protocols.odata.parsers.filter.typing import typecheck
from fc_selector.protocols.odata.parsers.filter.utils import (
    expression_relative_to_identifier,
)
from fc_selector.utils import (
    QueryBuilder as UtilsQueryBuilder,
)
from fc_selector.utils import (
    apply_odata_query_params,
    parse_expand_fields_v2,
    parse_odata_query,
)


class TestUtilsReexports:
    """Tests for fc_selector/utils.py re-exports."""

    def test_odata_query_builder_import(self):
        """QueryBuilder is importable from utils."""
        assert UtilsQueryBuilder is not None

    def test_apply_odata_query_params_import(self):
        """apply_odata_query_params is importable from utils."""
        assert callable(apply_odata_query_params)

    def test_parse_expand_fields_v2_import(self):
        """parse_expand_fields_v2 is importable from utils."""
        assert callable(parse_expand_fields_v2)

    def test_parse_odata_query_import(self):
        """parse_odata_query is importable from utils."""
        assert callable(parse_odata_query)


class TestCoreInit:
    """Tests for fc_selector/core/__init__.py lazy imports."""

    def test_query_builder_import(self):
        """QueryBuilder is directly importable."""
        assert QueryBuilder is not None

    def test_odata_query_builder_alias_import(self):
        """QueryBuilder alias is importable."""
        assert QueryBuilder is not None

    def test_lazy_parse_odata_query(self):
        """parse_odata_query is lazily importable."""
        # Use __getattr__ via attribute access
        parser = core.__getattr__("parse_odata_query")
        assert callable(parser)

    def test_lazy_odata_query_parser(self):
        """ODataQueryParser is lazily importable."""
        parser_class = core.__getattr__("ODataQueryParser")
        assert parser_class is not None

    def test_invalid_lazy_import_raises(self):
        """Invalid lazy import raises AttributeError."""
        with pytest.raises(AttributeError, match="has no attribute"):
            core.__getattr__("nonexistent_module")


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


class TestDTOConverter:
    """Tests for fc_selector/core/dtos/converter.py."""

    def test_converter_requires_from_model(self):
        """DTOConverter requires DTO class with from_model method."""

        class InvalidDTO:
            pass

        with pytest.raises(ValueError, match="must inherit from BaseODataDTO"):
            DTOConverter.to_dto(InvalidDTO, object())

    def test_converter_to_dtos_list(self):
        """DTOConverter.to_dtos converts list of instances."""

        @dataclass
        class SimpleDTO(BaseODataDTO):
            id: int
            name: str

        class MockModel:
            def __init__(self, id, name):
                self.id = id
                self.name = name

        instances = [MockModel(1, "first"), MockModel(2, "second")]
        dtos = DTOConverter.to_dtos(SimpleDTO, instances)

        assert len(dtos) == 2
        assert dtos[0].id == 1
        assert dtos[1].id == 2


class TestSpectacularIntegration:
    """Tests for fc_selector/django/drf/spectacular.py."""

    def test_odata_parameters_list(self):
        """ODATA_PARAMETERS contains expected parameters."""
        try:
            from fc_selector.django.drf.spectacular import ODATA_PARAMETERS  # noqa: PLC0415

            param_names = [p.name for p in ODATA_PARAMETERS]
            assert "$filter" in param_names
            assert "$select" in param_names
            assert "$expand" in param_names
            assert "$orderby" in param_names
            assert "$top" in param_names
            assert "$skip" in param_names
            assert "$count" in param_names
        except ImportError:
            pytest.skip("drf-spectacular not installed")

    def test_odata_retrieve_parameters(self):
        """ODATA_RETRIEVE_PARAMETERS has subset for retrieve."""
        try:
            from fc_selector.django.drf.spectacular import ODATA_RETRIEVE_PARAMETERS  # noqa: PLC0415

            param_names = [p.name for p in ODATA_RETRIEVE_PARAMETERS]
            assert "$select" in param_names
            assert "$expand" in param_names
            assert "$top" not in param_names
            assert "$skip" not in param_names
        except ImportError:
            pytest.skip("drf-spectacular not installed")

    def test_get_odata_parameters(self):
        """get_odata_parameters returns parameters list."""
        params = get_odata_parameters()
        # Returns list (empty if spectacular not installed)
        assert isinstance(params, list)

    def test_get_odata_retrieve_parameters(self):
        """get_odata_retrieve_parameters returns retrieve parameters."""
        params = get_odata_retrieve_parameters()
        assert isinstance(params, list)


class TestODataSerializerMixin:
    """Tests for fc_selector/django/drf/mixins/serializer_mixin.py."""

    def test_serializer_mixin_to_representation(self):
        """ODataSerializerMixin.to_representation works."""

        class TestSerializer(ODataSerializerMixin, serializers.Serializer):
            id = serializers.IntegerField()
            name = serializers.CharField()

        class MockInstance:
            id = 1
            name = "test"

        serializer = TestSerializer(MockInstance(), context={})
        data = serializer.to_representation(MockInstance())

        assert data["id"] == 1
        assert data["name"] == "test"

    def test_serializer_mixin_with_select(self):
        """ODataSerializerMixin respects $select."""

        class TestSerializer(ODataSerializerMixin, serializers.Serializer):
            id = serializers.IntegerField()
            name = serializers.CharField()
            email = serializers.CharField()

        class MockInstance:
            id = 1
            name = "test"
            email = "test@test.com"

        serializer = TestSerializer(MockInstance(), context={"odata_params": {"$select": "id,name"}})
        data = serializer.to_representation(MockInstance())

        assert "id" in data
        assert "name" in data
        assert "email" not in data

    def test_serializer_mixin_with_odata_context(self):
        """ODataSerializerMixin adds @odata.context with proper request."""

        class TestModel:
            __name__ = "TestModel"

        class TestSerializer(ODataSerializerMixin, serializers.Serializer):
            id = serializers.IntegerField()
            name = serializers.CharField()

            class Meta:
                model = TestModel

        class MockInstance:
            id = 1
            name = "test"
            pk = 1

        class MockRequest:
            query_params = {"$format": "json"}
            headers = {}

            def build_absolute_uri(self, path):
                return f"http://localhost{path}"

        serializer = TestSerializer(MockInstance(), context={"request": MockRequest()})
        data = serializer.to_representation(MockInstance())

        assert "@odata.context" in data
        assert "$metadata" in data["@odata.context"]

    def test_serializer_mixin_with_accept_header(self):
        """ODataSerializerMixin adds @odata.context with Accept header."""

        class TestModel:
            __name__ = "TestModel"

        class TestSerializer(ODataSerializerMixin, serializers.Serializer):
            id = serializers.IntegerField()

            class Meta:
                model = TestModel

        class MockInstance:
            id = 1
            pk = 1

        class MockRequest:
            query_params = {}
            headers = {"Accept": "application/json"}

            def build_absolute_uri(self, path):
                return f"http://localhost{path}"

        serializer = TestSerializer(MockInstance(), context={"request": MockRequest()})
        data = serializer.to_representation(MockInstance())

        assert "@odata.context" in data

    def test_serializer_mixin_get_odata_context(self):
        """ODataSerializerMixin.get_odata_context returns context."""

        class TestSerializer(ODataSerializerMixin, serializers.Serializer):
            id = serializers.IntegerField()

            class Meta:
                model = type("TestModel", (), {"__name__": "TestModel"})

        serializer = TestSerializer(context={})
        context = serializer.get_odata_context()

        assert context["odata_version"] == "4.0"
        assert "service_root" in context
        assert context["entity_set"] == "testmodels"
        assert context["entity_type"] == "TestModel"

    def test_serializer_mixin_with_request_context(self):
        """ODataSerializerMixin.get_odata_context with request."""

        class TestModel:
            __name__ = "TestModel"

        class TestSerializer(ODataSerializerMixin, serializers.Serializer):
            id = serializers.IntegerField()

            class Meta:
                model = TestModel

        class MockRequest:
            def build_absolute_uri(self, path):
                return f"http://api.example.com{path}"

        serializer = TestSerializer(context={"request": MockRequest()})
        context = serializer.get_odata_context()

        assert "http://api.example.com" in context["service_root"]
