"""
Tests for Django filter visitor (AST to Q conversion).

Covers fc_selector/django/visitors/filter_visitor.py
"""

import pytest
from django.db.models import F, Q, Value
from django.db.models.expressions import Exists
from django.db.models.lookups import (
    Exact,
    GreaterThan,
    GreaterThanOrEqual,
    In,
    LessThan,
    LessThanOrEqual,
)

from fc_selector.core import exceptions as core_ex
from fc_selector.core.ast import nodes as ast
from fc_selector.django.visitors.filter_visitor import AstToDjangoQVisitor
from fc_selector.protocols.odata.parsers.filter import parse_filter as parse
from tests.integration.support.models import ODataTestModel


@pytest.fixture
def test_model():
    """Fixture for test model."""
    return ODataTestModel


@pytest.fixture
def visitor(test_model):
    """Fixture for visitor instance."""
    return AstToDjangoQVisitor(test_model)


@pytest.mark.django_db
class TestBasicVisitorOperations:
    """Tests for basic visitor operations."""

    def test_visit_identifier(self, visitor):
        """Identifier becomes F() reference."""
        node = ast.Identifier("name")
        result = visitor.visit(node)
        # At depth 0, result is wrapped in Q
        assert isinstance(result, Q)

    def test_visit_attribute(self, visitor):
        """Attribute becomes F() with __ notation."""
        # author.name -> F('author__name')
        node = ast.Attribute(owner=ast.Identifier("related_items"), attr="title")
        # This goes through visit, which wraps in Q at depth 0
        result = visitor.visit(node)
        assert isinstance(result, Q)

    def test_visit_integer(self, visitor):
        """Integer becomes Value."""
        node = ast.Integer(42)
        visitor._depth = 1  # Avoid Q wrapping
        result = visitor.visit(node)
        assert isinstance(result, Value)
        assert result.value == 42

    def test_visit_float(self, visitor):
        """Float becomes Value."""
        node = ast.Float(3.14)
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, Value)
        assert result.value == 3.14

    def test_visit_boolean_true(self, visitor):
        """Boolean true becomes Value."""
        # Boolean AST node takes string 'true'
        node = ast.Boolean("true")
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, Value)
        assert result.value is True

    def test_visit_boolean_false(self, visitor):
        """Boolean false becomes Value."""
        node = ast.Boolean("false")
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, Value)
        assert result.value is False

    def test_visit_string(self, visitor):
        """String becomes Value."""
        node = ast.String("hello")
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, Value)
        assert result.value == "hello"

    def test_visit_date(self, visitor):
        """Date becomes Value with date object."""
        node = ast.Date("2024-01-15")
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, Value)

    def test_visit_datetime(self, visitor):
        """DateTime becomes Value."""
        node = ast.DateTime("2024-01-15T10:30:00Z")
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, Value)

    def test_visit_time(self, visitor):
        """Time becomes Value."""
        node = ast.Time("10:30:00")
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, Value)

    def test_visit_duration(self, visitor):
        """Duration becomes Value."""
        node = ast.Duration("PT1H30M")
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, Value)

    def test_visit_guid(self, visitor):
        """GUID becomes Value."""
        node = ast.GUID("550e8400-e29b-41d4-a716-446655440000")
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, Value)

    def test_visit_list(self, visitor):
        """List becomes list of visited values."""
        node = ast.List([ast.Integer(1), ast.Integer(2), ast.Integer(3)])
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, list)
        assert len(result) == 3


@pytest.mark.django_db
class TestInvalidDateTimeValueError:
    """Tests for ValueError handling in date/time visitors."""

    def test_invalid_date_raises_invalid_value_error(self, visitor):
        """Invalid date string raises InvalidValueError."""
        # Create a Date node with invalid format
        node = ast.Date("not-a-valid-date")
        visitor._depth = 1
        with pytest.raises(core_ex.InvalidValueError) as exc_info:
            visitor.visit(node)
        assert exc_info.value.expected_type == "Date"
        assert "not-a-valid-date" in str(exc_info.value.value)

    def test_invalid_datetime_raises_invalid_value_error(self, visitor):
        """Invalid datetime string raises InvalidValueError."""
        # Create a DateTime node with invalid format
        node = ast.DateTime("not-a-valid-datetime")
        visitor._depth = 1
        with pytest.raises(core_ex.InvalidValueError) as exc_info:
            visitor.visit(node)
        assert exc_info.value.expected_type == "DateTime"
        assert "not-a-valid-datetime" in str(exc_info.value.value)

    def test_invalid_time_raises_invalid_value_error(self, visitor):
        """Invalid time string raises InvalidValueError."""
        # Create a Time node with invalid format
        node = ast.Time("not-a-valid-time")
        visitor._depth = 1
        with pytest.raises(core_ex.InvalidValueError) as exc_info:
            visitor.visit(node)
        assert exc_info.value.expected_type == "Time"
        assert "not-a-valid-time" in str(exc_info.value.value)

    def test_partial_date_raises_error(self, visitor):
        """Partial date raises InvalidValueError."""
        node = ast.Date("2024-13-45")  # Invalid month/day
        visitor._depth = 1
        with pytest.raises(core_ex.InvalidValueError):
            visitor.visit(node)

    def test_invalid_time_format_raises_error(self, visitor):
        """Invalid time format raises InvalidValueError."""
        node = ast.Time("25:99:99")  # Invalid hour/minute/second
        visitor._depth = 1
        with pytest.raises(core_ex.InvalidValueError):
            visitor.visit(node)


@pytest.mark.django_db
class TestComparisonOperators:
    """Tests for comparison operators."""

    def test_visit_eq(self, visitor):
        """Eq operator becomes Exact lookup."""
        node = ast.Eq()
        visitor._depth = 1
        result = visitor.visit(node)
        assert result is Exact

    def test_visit_lt(self, visitor):
        """Lt operator becomes LessThan lookup."""
        node = ast.Lt()
        visitor._depth = 1
        result = visitor.visit(node)
        assert result is LessThan

    def test_visit_lte(self, visitor):
        """LtE operator becomes LessThanOrEqual lookup."""
        node = ast.LtE()
        visitor._depth = 1
        result = visitor.visit(node)
        assert result is LessThanOrEqual

    def test_visit_gt(self, visitor):
        """Gt operator becomes GreaterThan lookup."""
        node = ast.Gt()
        visitor._depth = 1
        result = visitor.visit(node)
        assert result is GreaterThan

    def test_visit_gte(self, visitor):
        """GtE operator becomes GreaterThanOrEqual lookup."""
        node = ast.GtE()
        visitor._depth = 1
        result = visitor.visit(node)
        assert result is GreaterThanOrEqual

    def test_visit_in(self, visitor):
        """In operator becomes In lookup."""
        node = ast.In()
        visitor._depth = 1
        result = visitor.visit(node)
        assert result is In


@pytest.mark.django_db
class TestArithmeticOperators:
    """Tests for arithmetic operators."""

    def test_visit_add(self, visitor):
        """Add becomes addition operator."""
        node = ast.Add()
        visitor._depth = 1
        result = visitor.visit(node)
        assert result(2, 3) == 5

    def test_visit_sub(self, visitor):
        """Sub becomes subtraction operator."""
        node = ast.Sub()
        visitor._depth = 1
        result = visitor.visit(node)
        assert result(5, 3) == 2

    def test_visit_mult(self, visitor):
        """Mult becomes multiplication operator."""
        node = ast.Mult()
        visitor._depth = 1
        result = visitor.visit(node)
        assert result(4, 3) == 12

    def test_visit_div(self, visitor):
        """Div becomes division operator."""
        node = ast.Div()
        visitor._depth = 1
        result = visitor.visit(node)
        assert result(10, 2) == 5.0

    def test_visit_mod(self, visitor):
        """Mod becomes modulo operator."""
        node = ast.Mod()
        visitor._depth = 1
        result = visitor.visit(node)
        assert result(10, 3) == 1


@pytest.mark.django_db
class TestBooleanOperators:
    """Tests for boolean operators."""

    def test_visit_and(self, visitor):
        """And becomes & operator."""
        node = ast.And()
        visitor._depth = 1
        result = visitor.visit(node)
        # Test with Q objects
        q1 = Q(a=1)
        q2 = Q(b=2)
        combined = result(q1, q2)
        assert isinstance(combined, Q)

    def test_visit_or(self, visitor):
        """Or becomes | operator."""
        node = ast.Or()
        visitor._depth = 1
        result = visitor.visit(node)
        q1 = Q(a=1)
        q2 = Q(b=2)
        combined = result(q1, q2)
        assert isinstance(combined, Q)

    def test_visit_not(self, visitor):
        """Not becomes ~ operator."""
        node = ast.Not()
        visitor._depth = 1
        result = visitor.visit(node)
        q = Q(a=1)
        negated = result(q)
        assert isinstance(negated, Q)


@pytest.mark.django_db
class TestCompareNode:
    """Tests for Compare node processing."""

    def test_compare_null_eq(self, visitor):
        """Compare with null eq becomes isnull=True."""
        node = ast.Compare(left=ast.Identifier("name"), comparator=ast.Eq(), right=ast.Null())
        result = visitor.visit(node)
        assert isinstance(result, Q)

    def test_compare_null_ne(self, visitor):
        """Compare with null ne becomes isnull=False."""
        node = ast.Compare(left=ast.Identifier("name"), comparator=ast.NotEq(), right=ast.Null())
        result = visitor.visit(node)
        assert isinstance(result, Q)

    def test_compare_null_invalid_operator(self, visitor):
        """Compare with null and gt raises error."""
        node = ast.Compare(left=ast.Identifier("count"), comparator=ast.Gt(), right=ast.Null())
        with pytest.raises(core_ex.TypeMismatchError):
            visitor.visit(node)

    def test_compare_string(self, visitor):
        """Compare string field."""
        node = ast.Compare(left=ast.Identifier("name"), comparator=ast.Eq(), right=ast.String("test"))
        result = visitor.visit(node)
        assert isinstance(result, Q)


@pytest.mark.django_db
class TestBoolOpNode:
    """Tests for BoolOp node processing."""

    def test_bool_op_and(self, visitor):
        """BoolOp with And combines Q objects."""
        left = ast.Compare(left=ast.Identifier("name"), comparator=ast.Eq(), right=ast.String("test"))
        right = ast.Compare(left=ast.Identifier("count"), comparator=ast.Gt(), right=ast.Integer(5))
        node = ast.BoolOp(left=left, op=ast.And(), right=right)
        result = visitor.visit(node)
        assert isinstance(result, Q)

    def test_bool_op_from_filter(self, visitor):
        """BoolOp from parsed filter."""
        filter_ast = parse("name eq 'test' and count gt 5")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)


@pytest.mark.django_db
class TestUnaryOpNode:
    """Tests for UnaryOp node processing."""

    def test_unary_not_from_filter(self, visitor):
        """UnaryOp with Not negates Q object (from parser)."""
        filter_ast = parse("not (is_active eq true)")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)


@pytest.mark.django_db
class TestStringFunctions:
    """Tests for OData string functions."""

    def test_contains_function(self, visitor):
        """contains(field, 'substr') function."""
        filter_ast = parse("contains(name, 'test')")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_startswith_function(self, visitor):
        """startswith(field, 'prefix') function."""
        filter_ast = parse("startswith(name, 'test')")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_endswith_function(self, visitor):
        """endswith(field, 'suffix') function."""
        filter_ast = parse("endswith(name, 'test')")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_length_function(self, visitor):
        """length(field) function."""
        filter_ast = parse("length(name) gt 5")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_tolower_function(self, visitor):
        """tolower(field) function."""
        filter_ast = parse("tolower(name) eq 'test'")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_toupper_function(self, visitor):
        """toupper(field) function."""
        filter_ast = parse("toupper(name) eq 'TEST'")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_trim_function(self, visitor):
        """trim(field) function."""
        filter_ast = parse("trim(name) eq 'test'")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_concat_function(self, visitor):
        """concat(field1, field2) function."""
        filter_ast = parse("concat(name, description) eq 'test'")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_indexof_function(self, visitor):
        """indexof(field, 'substr') function."""
        filter_ast = parse("indexof(name, 'test') eq 0")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_substring_function(self, visitor):
        """substring(field, start) function."""
        filter_ast = parse("substring(name, 0) eq 'test'")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_substring_function_with_length(self, visitor):
        """substring(field, start, length) function."""
        filter_ast = parse("substring(name, 0, 4) eq 'test'")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_matchespattern_function(self, visitor):
        """matchesPattern(field, 'pattern') function."""
        filter_ast = parse("matchesPattern(name, '^test.*')")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)


@pytest.mark.django_db
class TestDateTimeFunctions:
    """Tests for OData date/time functions."""

    def test_date_function(self, visitor):
        """date(field) function."""
        filter_ast = parse("date(created_at) eq 2024-01-15")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_day_function(self, visitor):
        """day(field) function."""
        filter_ast = parse("day(created_at) eq 15")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_month_function(self, visitor):
        """month(field) function."""
        filter_ast = parse("month(created_at) eq 1")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_year_function(self, visitor):
        """year(field) function."""
        filter_ast = parse("year(created_at) eq 2024")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_hour_function(self, visitor):
        """hour(field) function."""
        filter_ast = parse("hour(created_at) eq 10")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_minute_function(self, visitor):
        """minute(field) function."""
        filter_ast = parse("minute(created_at) eq 30")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_second_function(self, visitor):
        """second(field) function."""
        filter_ast = parse("second(created_at) eq 45")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_time_function(self, visitor):
        """time(field) function."""
        filter_ast = parse("time(created_at) eq 10:30:00")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_now_function(self, visitor):
        """now() function."""
        filter_ast = parse("created_at lt now()")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)


@pytest.mark.django_db
class TestMathFunctions:
    """Tests for OData math functions."""

    def test_ceiling_function(self, visitor):
        """ceiling(field) function."""
        filter_ast = parse("ceiling(rating) eq 5")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_floor_function(self, visitor):
        """floor(field) function."""
        filter_ast = parse("floor(rating) eq 4")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_round_function(self, visitor):
        """round(field) function."""
        filter_ast = parse("round(rating) eq 5")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)


@pytest.mark.django_db
class TestUnknownFunction:
    """Tests for unknown function handling."""

    def test_unknown_function_raises_error(self, visitor):
        """Unknown function raises UnsupportedFunctionError."""
        # Create a Call node directly to test unknown function
        node = ast.Call(func=ast.Identifier("unknownfunc"), args=[ast.Identifier("name")])
        with pytest.raises(core_ex.UnsupportedFunctionError) as exc_info:
            visitor.visit(node)
        assert "unknownfunc" in str(exc_info.value)


@pytest.mark.django_db
class TestNotEqComparison:
    """Tests for NotEq comparison operator."""

    def test_not_eq_operator(self, visitor):
        """NotEq operator returns NotEqual lookup."""
        filter_ast = parse("name ne 'test'")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_not_eq_integer(self, visitor):
        """NotEq with integer."""
        filter_ast = parse("count ne 5")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)


@pytest.mark.django_db
class TestBoolOpErrors:
    """Tests for BoolOp error conditions."""

    def test_boolop_with_f_left_raises_error(self, visitor):
        """BoolOp with F on left side raises TypeMismatchError."""
        # Create a BoolOp where left is just an identifier (F reference)
        # This happens when the expression doesn't resolve to Q
        node = ast.BoolOp(
            left=ast.Identifier("name"),  # Will become F, not Q
            op=ast.And(),
            right=ast.Compare(left=ast.Identifier("count"), comparator=ast.Gt(), right=ast.Integer(5)),
        )
        with pytest.raises(core_ex.TypeMismatchError):
            visitor.visit(node)


@pytest.mark.django_db
class TestInOperator:
    """Tests for In operator."""

    def test_in_list(self, visitor):
        """In operator with list of values."""
        filter_ast = parse("status in ('draft', 'published')")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)


@pytest.mark.django_db
class TestLambdaExpressions:
    """Tests for any/all lambda expressions."""

    def test_any_without_lambda(self, visitor):
        """any() expression without lambda returns Exists subquery."""
        # Test collection any() - checks if relation has any items
        filter_ast = parse("related_items/any()")
        result = visitor.visit(filter_ast)
        # Lambda expressions return Exists subqueries
        assert isinstance(result, Exists)

    def test_any_with_lambda(self, visitor):
        """any() expression with lambda filter returns Exists subquery."""
        # Test any(x: x/value gt 10)
        filter_ast = parse("related_items/any(r: r/value gt 10)")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Exists)

    def test_all_with_lambda(self, visitor):
        """all() expression with lambda filter returns negated Exists subquery."""
        # Test all(x: x/value gt 10)
        filter_ast = parse("related_items/all(r: r/value gt 10)")
        result = visitor.visit(filter_ast)
        # all() returns Exists (the negated flag is internal to the subquery)
        assert isinstance(result, Exists)


@pytest.mark.django_db
class TestDateTimeValidation:
    """Tests for date/time validation errors."""

    def test_date_value_parsing(self, visitor):
        """Date value is correctly parsed."""
        # Test with a valid date literal
        node = ast.Date("2024-01-15")
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, Value)

    def test_datetime_value_parsing(self, visitor):
        """DateTime value is correctly parsed."""
        node = ast.DateTime("2024-01-15T10:30:00Z")
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, Value)

    def test_time_value_parsing(self, visitor):
        """Time value is correctly parsed."""
        node = ast.Time("10:30:00")
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, Value)

    def test_duration_value_parsing(self, visitor):
        """Duration value is correctly parsed."""
        node = ast.Duration("P1D")
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, Value)

    def test_guid_value_parsing(self, visitor):
        """GUID value is correctly parsed."""
        node = ast.GUID("550e8400-e29b-41d4-a716-446655440000")
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, Value)


@pytest.mark.django_db
class TestListNode:
    """Tests for List node processing."""

    def test_visit_list(self, visitor):
        """List node is converted to Python list."""
        node = ast.List(val=[ast.Integer(1), ast.Integer(2), ast.Integer(3)])
        visitor._depth = 1
        result = visitor.visit(node)
        assert isinstance(result, list)
        assert len(result) == 3


@pytest.mark.django_db
class TestArithmeticOperators:
    """Tests for arithmetic operators."""

    def test_add_operator(self, visitor):
        """Add operator."""
        filter_ast = parse("count add 5 eq 15")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_sub_operator(self, visitor):
        """Sub operator."""
        filter_ast = parse("count sub 5 eq 5")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_mul_operator(self, visitor):
        """Mul operator."""
        filter_ast = parse("count mul 2 eq 20")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_div_operator(self, visitor):
        """Div operator."""
        filter_ast = parse("count div 2 eq 5")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_mod_operator(self, visitor):
        """Mod operator."""
        filter_ast = parse("count mod 3 eq 1")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)


@pytest.mark.django_db
class TestFieldValidation:
    """Tests for field validation."""

    def test_private_field_blocked(self, visitor):
        """Private fields (starting with _) are blocked."""
        node = ast.Identifier("_private_field")
        with pytest.raises(core_ex.InvalidFieldError) as exc_info:
            visitor.visit(node)
        assert "private" in str(exc_info.value).lower()

    def test_allowed_fields_filter(self):
        """Fields not in allowed_fields are blocked."""
        visitor = AstToDjangoQVisitor(ODataTestModel, allowed_fields={"name", "count"})
        # Allowed field works
        filter_ast = parse("name eq 'test'")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

        # Disallowed field raises error
        filter_ast2 = parse("description eq 'test'")
        with pytest.raises(core_ex.InvalidFieldError) as exc_info:
            visitor.visit(filter_ast2)
        assert "not in allowed" in str(exc_info.value).lower()

    def test_nonexistent_field(self, visitor):
        """Non-existent field raises InvalidFieldError."""
        node = ast.Identifier("nonexistent_field")
        with pytest.raises(core_ex.InvalidFieldError) as exc_info:
            visitor.visit(node)
        assert "does not exist" in str(exc_info.value).lower()


@pytest.mark.django_db
class TestBinOpNode:
    """Tests for BinOp (arithmetic) node processing."""

    def test_binop_addition(self, visitor):
        """BinOp addition works."""
        filter_ast = parse("count add 5 eq 10")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_binop_subtraction(self, visitor):
        """BinOp subtraction works."""
        filter_ast = parse("count sub 5 eq 0")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_binop_multiplication(self, visitor):
        """BinOp multiplication works."""
        filter_ast = parse("count mul 2 eq 10")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_binop_division(self, visitor):
        """BinOp division works."""
        filter_ast = parse("count div 2 eq 5")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_binop_modulo(self, visitor):
        """BinOp modulo works."""
        filter_ast = parse("count mod 3 eq 1")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)


@pytest.mark.django_db
class TestComplexFilters:
    """Tests for complex filter expressions."""

    def test_nested_and_or(self, visitor):
        """Nested AND/OR expressions."""
        filter_ast = parse("(name eq 'test' or name eq 'test2') and count gt 5")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_not_with_comparison(self, visitor):
        """NOT with comparison."""
        filter_ast = parse("not (name eq 'test')")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)

    def test_multiple_function_calls(self, visitor):
        """Multiple function calls in expression."""
        filter_ast = parse("contains(name, 'test') and length(name) gt 5")
        result = visitor.visit(filter_ast)
        assert isinstance(result, Q)


@pytest.mark.django_db
class TestSubstringTypeChecks:
    """Tests for substring function type checking."""

    def test_contains_type_check_invalid_field(self, visitor):
        """contains() with invalid field type raises error."""
        # Create AST with integer as field (should fail type check)
        node = ast.Call(func=ast.Identifier("contains"), args=[ast.Integer(123), ast.String("test")])
        with pytest.raises(core_ex.TypeMismatchError):
            visitor.visit(node)

    def test_contains_type_check_invalid_substr(self, visitor):
        """contains() with invalid substring type raises error."""
        node = ast.Call(func=ast.Identifier("contains"), args=[ast.Identifier("name"), ast.Integer(123)])
        with pytest.raises(core_ex.TypeMismatchError):
            visitor.visit(node)


@pytest.mark.django_db
class TestAnnotationGeneration:
    """Tests for annotation name generation."""

    def test_gen_annotation_name_with_name(self, visitor):
        """Annotation name from expr with name attribute."""
        expr = F("test_field")
        name = visitor._gen_annotation_name(expr)
        assert "test_field" in name

    def test_gen_annotation_name_with_value(self, visitor):
        """Annotation name from expr with value attribute."""
        expr = Value("test_value")
        name = visitor._gen_annotation_name(expr)
        assert "test_value" in name
