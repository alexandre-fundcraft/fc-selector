"""
Additional tests for fc_selector/django/visitors/filter_visitor.py to improve coverage.
"""
import re
import pytest
from uuid import UUID
from django.db.models import Value, F, Func, Expression
from fc_selector.core import ast
from fc_selector.core import exceptions as core_ex
from fc_selector.django.visitors.filter_visitor import AstToDjangoQVisitor, MAX_REGEX_PATTERN_LENGTH
from tests.integration.support.models import ODataTestModel


@pytest.fixture
def visitor():
    return AstToDjangoQVisitor(ODataTestModel)


@pytest.mark.django_db
class TestFilterVisitorCoverage:
    """Additional coverage tests for filter visitor."""

    def test_visit_null_raises_not_implemented(self, visitor):
        """visit_Null should raise NotImplementedError."""
        node = ast.Null()
        with pytest.raises(NotImplementedError):
            visitor.visit(node)

    def test_matchespattern_redos_prevention(self, visitor):
        """matchesPattern should raise InvalidValueError for too long patterns."""
        long_pattern = "a" * (MAX_REGEX_PATTERN_LENGTH + 1)
        node = ast.Call(
            func=ast.Identifier("matchesPattern"),
            args=[ast.Identifier("name"), ast.String(long_pattern)]
        )
        with pytest.raises(core_ex.InvalidValueError) as exc:
            visitor.visit(node)
        assert "pattern too long" in str(exc.value)

    def test_matchespattern_invalid_regex(self, visitor):
        """matchesPattern should raise InvalidValueError for invalid regex."""
        invalid_pattern = "["  # Unclosed bracket
        node = ast.Call(
            func=ast.Identifier("matchesPattern"),
            args=[ast.Identifier("name"), ast.String(invalid_pattern)]
        )
        with pytest.raises(core_ex.InvalidValueError) as exc:
            visitor.visit(node)
        assert "valid regex pattern" in str(exc.value)

    def test_collection_lambda_unknown_operator(self, visitor):
        """visit_CollectionLambda should raise NotImplementedError for unknown operators."""
        # Manually construct a lambda node with a dummy operator
        class DummyOp(ast.Node):
            pass

        node = ast.CollectionLambda(
            owner=ast.Identifier("related_items"),
            operator=DummyOp(),
            lambda_=None
        )
        with pytest.raises(NotImplementedError):
            visitor.visit(node)

    def test_gen_annotation_name_fallback(self, visitor):
        """_gen_annotation_name should handle expressions without name/value."""
        class DummyExpr(Expression):
            def __init__(self):
                pass
            
            def get_source_expressions(self):
                return [Value("inner")]

        expr = DummyExpr()
        name = visitor._gen_annotation_name(expr)
        assert "dummyexpr" in name
        assert "inner" in name

    def test_gen_annotation_name_sanitization(self, visitor):
        """_gen_annotation_name should sanitize names."""
        expr = Value("Invalid-Name!@#")
        name = visitor._gen_annotation_name(expr)
        assert "invalid_name" in name
        assert "!" not in name

    def test_fix_uuid_value(self, visitor):
        """_fix_uuid should handle UUID values."""
        uuid_val = UUID("550e8400-e29b-41d4-a716-446655440000")
        node = Value(uuid_val)
        result = visitor._fix_uuid(node)
        assert result == uuid_val

    def test_fix_uuid_list(self, visitor):
        """_fix_uuid should handle lists of UUID values."""
        uuid_val = UUID("550e8400-e29b-41d4-a716-446655440000")
        node = [Value(uuid_val), "string"]
        result = visitor._fix_uuid(node)
        assert result[0] == uuid_val
        assert result[1] == "string"

    def test_attempt_keywordify_literal(self, visitor):
        """_attempt_keywordify returns None for literals."""
        assert visitor._attempt_keywordify(ast.String("test")) is None
        assert visitor._attempt_keywordify(Value("test")) is None

    def test_attempt_keywordify_lookup(self, visitor):
        """_attempt_keywordify handles lookups with rhs."""
        from django.db.models.lookups import Exact
        lookup = Exact(F("name"), Value("test"))
        result = visitor._attempt_keywordify(lookup)
        assert result is not None
