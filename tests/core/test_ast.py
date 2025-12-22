"""
Unit tests for AST nodes and visitor pattern.

This test suite provides comprehensive coverage for:
1. AST Node Types (literals, operators, expressions)
2. Node immutability and validation
3. Visitor pattern (NodeVisitor)
4. Transformer pattern (NodeTransformer)
5. AST traversal and modification
"""

import datetime as dt
from uuid import UUID

import pytest

from fc_selector.core.parsers.filter.ast import nodes
from fc_selector.core.parsers.filter.ast.visitor import (
    NodeTransformer,
    NodeVisitor,
    iter_dataclass_fields,
)

# ==============================================================================
# Tests for Basic Node Types
# ==============================================================================


class TestIdentifierNode:
    """Tests for Identifier node."""

    def test_simple_identifier(self):
        """Test creating a simple identifier without namespace."""
        node = nodes.Identifier(name="field_name")

        assert node.name == "field_name"
        assert node.namespace == ()
        assert node.full_name() == "field_name"

    def test_namespaced_identifier(self):
        """Test creating an identifier with namespace."""
        node = nodes.Identifier(name="distance", namespace=("geo",))

        assert node.name == "distance"
        assert node.namespace == ("geo",)
        assert node.full_name() == "geo.distance"

    def test_multi_level_namespace(self):
        """Test identifier with multi-level namespace."""
        node = nodes.Identifier(name="func", namespace=("ns", "sub"))

        assert node.name == "func"
        assert node.namespace == ("ns", "sub")
        assert node.full_name() == "ns.sub.func"

    def test_identifier_immutability(self):
        """Test that identifiers are immutable (frozen dataclass)."""
        node = nodes.Identifier(name="test")

        with pytest.raises(Exception):  # FrozenInstanceError
            node.name = "modified"


class TestAttributeNode:
    """Tests for Attribute node (navigation properties)."""

    def test_simple_attribute_access(self):
        """Test simple attribute access: object.attribute"""
        owner = nodes.Identifier(name="author")
        node = nodes.Attribute(owner=owner, attr="name")

        assert isinstance(node.owner, nodes.Identifier)
        assert node.owner.name == "author"
        assert node.attr == "name"

    def test_nested_attribute_access(self):
        """Test nested attribute access: author.user.first_name"""
        author = nodes.Identifier(name="author")
        user = nodes.Attribute(owner=author, attr="user")
        first_name = nodes.Attribute(owner=user, attr="first_name")

        assert isinstance(first_name.owner, nodes.Attribute)
        assert first_name.attr == "first_name"
        assert first_name.owner.attr == "user"
        assert isinstance(first_name.owner.owner, nodes.Identifier)
        assert first_name.owner.owner.name == "author"


# ==============================================================================
# Tests for Literal Nodes
# ==============================================================================


class TestLiteralNodes:
    """Tests for literal value nodes."""

    def test_null_literal(self):
        """Test Null literal."""
        node = nodes.Null()
        assert node.py_val is None

    def test_integer_literal(self):
        """Test Integer literal."""
        node = nodes.Integer(val="42")
        assert node.val == "42"
        assert node.py_val == 42
        assert isinstance(node.py_val, int)

    def test_integer_negative(self):
        """Test negative integer."""
        node = nodes.Integer(val="-10")
        assert node.py_val == -10

    def test_float_literal(self):
        """Test Float literal."""
        node = nodes.Float(val="3.14")
        assert node.val == "3.14"
        assert node.py_val == 3.14
        assert isinstance(node.py_val, float)

    def test_float_negative(self):
        """Test negative float."""
        node = nodes.Float(val="-2.5")
        assert node.py_val == -2.5

    def test_boolean_true(self):
        """Test Boolean true literal."""
        node = nodes.Boolean(val="true")
        assert node.val == "true"
        assert node.py_val is True

    def test_boolean_false(self):
        """Test Boolean false literal."""
        node = nodes.Boolean(val="false")
        assert node.val == "false"
        assert node.py_val is False

    def test_boolean_case_insensitive(self):
        """Test Boolean is case insensitive."""
        assert nodes.Boolean(val="TRUE").py_val is True
        assert nodes.Boolean(val="False").py_val is False
        assert nodes.Boolean(val="TrUe").py_val is True

    def test_string_literal(self):
        """Test String literal."""
        node = nodes.String(val="hello")
        assert node.val == "hello"
        assert node.py_val == "hello"

    def test_string_with_quotes(self):
        """Test String preserves quotes."""
        node = nodes.String(val="'John Doe'")
        assert node.val == "'John Doe'"
        assert node.py_val == "'John Doe'"

    def test_date_literal(self):
        """Test Date literal."""
        node = nodes.Date(val="2023-01-15")
        assert node.val == "2023-01-15"
        assert node.py_val == dt.date(2023, 1, 15)
        assert isinstance(node.py_val, dt.date)

    def test_time_literal(self):
        """Test Time literal."""
        node = nodes.Time(val="14:30:00")
        assert node.val == "14:30:00"
        assert node.py_val == dt.time(14, 30, 0)
        assert isinstance(node.py_val, dt.time)

    def test_datetime_literal(self):
        """Test DateTime literal."""
        node = nodes.DateTime(val="2023-01-15T14:30:00Z")
        assert node.val == "2023-01-15T14:30:00Z"
        result = node.py_val
        assert isinstance(result, dt.datetime)
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 15

    def test_guid_literal(self):
        """Test GUID literal."""
        guid_str = "12345678-1234-1234-1234-123456789abc"
        node = nodes.GUID(val=guid_str)
        assert node.val == guid_str
        assert node.py_val == UUID(guid_str)
        assert isinstance(node.py_val, UUID)

    def test_list_literal_integers(self):
        """Test List literal with integers."""
        items = [nodes.Integer(val="1"), nodes.Integer(val="2"), nodes.Integer(val="3")]
        node = nodes.List(val=items)
        assert len(node.val) == 3
        assert node.py_val == [1, 2, 3]

    def test_list_literal_strings(self):
        """Test List literal with strings."""
        items = [nodes.String(val="'a'"), nodes.String(val="'b'")]
        node = nodes.List(val=items)
        assert node.py_val == ["'a'", "'b'"]

    def test_list_literal_mixed(self):
        """Test List literal with mixed types."""
        items = [nodes.Integer(val="42"), nodes.String(val="'text'"), nodes.Boolean(val="true")]
        node = nodes.List(val=items)
        assert node.py_val == [42, "'text'", True]


class TestDurationLiteral:
    """Tests for Duration literal parsing."""

    def test_duration_days_only(self):
        """Test duration with only days: P1D"""
        node = nodes.Duration(val="P1D")
        assert node.py_val == dt.timedelta(days=1)

    def test_duration_time_only(self):
        """Test duration with only time: PT2H30M"""
        node = nodes.Duration(val="PT2H30M")
        assert node.py_val == dt.timedelta(hours=2, minutes=30)

    def test_duration_combined(self):
        """Test duration with date and time: P1DT2H30M"""
        node = nodes.Duration(val="P1DT2H30M")
        expected = dt.timedelta(days=1, hours=2, minutes=30)
        assert node.py_val == expected

    def test_duration_with_seconds(self):
        """Test duration with seconds: PT1H30M45S"""
        node = nodes.Duration(val="PT1H30M45S")
        expected = dt.timedelta(hours=1, minutes=30, seconds=45)
        assert node.py_val == expected

    def test_duration_negative(self):
        """Test negative duration: -P1D"""
        node = nodes.Duration(val="-P1D")
        assert node.py_val == dt.timedelta(days=-1)

    def test_duration_unpack(self):
        """Test duration unpacking."""
        node = nodes.Duration(val="P1Y2M3DT4H5M6S")
        sign, years, months, days, hours, minutes, seconds = node.unpack()

        assert sign is None
        assert years == "1"
        assert months == "2"
        assert days == "3"
        assert hours == "4"
        assert minutes == "5"
        assert seconds == "6"

    def test_duration_invalid_format(self):
        """Test invalid duration format raises ValueError."""
        node = nodes.Duration(val="INVALID")
        with pytest.raises(ValueError, match="Could not unpack Duration"):
            node.unpack()


# ==============================================================================
# Tests for Operator Nodes
# ==============================================================================


class TestArithmeticOperators:
    """Tests for arithmetic operator nodes."""

    def test_add_operator(self):
        """Test Add operator."""
        left = nodes.Identifier(name="price")
        right = nodes.Integer(val="10")
        node = nodes.BinOp(op=nodes.Add(), left=left, right=right)

        assert isinstance(node.op, nodes.Add)
        assert node.left.name == "price"
        assert node.right.py_val == 10

    def test_sub_operator(self):
        """Test Sub operator."""
        left = nodes.Identifier(name="total")
        right = nodes.Integer(val="5")
        node = nodes.BinOp(op=nodes.Sub(), left=left, right=right)

        assert isinstance(node.op, nodes.Sub)

    def test_mult_operator(self):
        """Test Mult operator."""
        left = nodes.Identifier(name="quantity")
        right = nodes.Integer(val="2")
        node = nodes.BinOp(op=nodes.Mult(), left=left, right=right)

        assert isinstance(node.op, nodes.Mult)

    def test_div_operator(self):
        """Test Div operator."""
        left = nodes.Identifier(name="total")
        right = nodes.Integer(val="2")
        node = nodes.BinOp(op=nodes.Div(), left=left, right=right)

        assert isinstance(node.op, nodes.Div)

    def test_mod_operator(self):
        """Test Mod operator."""
        left = nodes.Identifier(name="value")
        right = nodes.Integer(val="10")
        node = nodes.BinOp(op=nodes.Mod(), left=left, right=right)

        assert isinstance(node.op, nodes.Mod)

    def test_nested_arithmetic(self):
        """Test nested arithmetic operations."""
        # (a + b) * c
        a = nodes.Identifier(name="a")
        b = nodes.Identifier(name="b")
        c = nodes.Identifier(name="c")

        add_op = nodes.BinOp(op=nodes.Add(), left=a, right=b)
        mult_op = nodes.BinOp(op=nodes.Mult(), left=add_op, right=c)

        assert isinstance(mult_op.left, nodes.BinOp)
        assert isinstance(mult_op.left.op, nodes.Add)


class TestComparisonOperators:
    """Tests for comparison operator nodes."""

    def test_eq_operator(self):
        """Test Eq (equal) operator."""
        left = nodes.Identifier(name="status")
        right = nodes.String(val="'active'")
        node = nodes.Compare(comparator=nodes.Eq(), left=left, right=right)

        assert isinstance(node.comparator, nodes.Eq)
        assert node.left.name == "status"
        assert node.right.val == "'active'"

    def test_ne_operator(self):
        """Test NotEq (not equal) operator."""
        left = nodes.Identifier(name="status")
        right = nodes.String(val="'deleted'")
        node = nodes.Compare(comparator=nodes.NotEq(), left=left, right=right)

        assert isinstance(node.comparator, nodes.NotEq)

    def test_lt_operator(self):
        """Test Lt (less than) operator."""
        left = nodes.Identifier(name="age")
        right = nodes.Integer(val="18")
        node = nodes.Compare(comparator=nodes.Lt(), left=left, right=right)

        assert isinstance(node.comparator, nodes.Lt)

    def test_lte_operator(self):
        """Test LtE (less than or equal) operator."""
        left = nodes.Identifier(name="price")
        right = nodes.Float(val="99.99")
        node = nodes.Compare(comparator=nodes.LtE(), left=left, right=right)

        assert isinstance(node.comparator, nodes.LtE)

    def test_gt_operator(self):
        """Test Gt (greater than) operator."""
        left = nodes.Identifier(name="rating")
        right = nodes.Float(val="4.5")
        node = nodes.Compare(comparator=nodes.Gt(), left=left, right=right)

        assert isinstance(node.comparator, nodes.Gt)

    def test_gte_operator(self):
        """Test GtE (greater than or equal) operator."""
        left = nodes.Identifier(name="score")
        right = nodes.Integer(val="100")
        node = nodes.Compare(comparator=nodes.GtE(), left=left, right=right)

        assert isinstance(node.comparator, nodes.GtE)

    def test_in_operator(self):
        """Test In operator with list."""
        left = nodes.Identifier(name="status")
        right = nodes.List(val=[
            nodes.String(val="'active'"),
            nodes.String(val="'pending'")
        ])
        node = nodes.Compare(comparator=nodes.In(), left=left, right=right)

        assert isinstance(node.comparator, nodes.In)
        assert isinstance(node.right, nodes.List)
        assert len(node.right.val) == 2


class TestBooleanOperators:
    """Tests for boolean operator nodes."""

    def test_and_operator(self):
        """Test And operator."""
        left = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="status"),
            right=nodes.String(val="'active'")
        )
        right = nodes.Compare(
            comparator=nodes.Gt(),
            left=nodes.Identifier(name="age"),
            right=nodes.Integer(val="18")
        )
        node = nodes.BoolOp(op=nodes.And(), left=left, right=right)

        assert isinstance(node.op, nodes.And)
        assert isinstance(node.left, nodes.Compare)
        assert isinstance(node.right, nodes.Compare)

    def test_or_operator(self):
        """Test Or operator."""
        left = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="status"),
            right=nodes.String(val="'active'")
        )
        right = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="status"),
            right=nodes.String(val="'pending'")
        )
        node = nodes.BoolOp(op=nodes.Or(), left=left, right=right)

        assert isinstance(node.op, nodes.Or)

    def test_nested_boolean_ops(self):
        """Test nested boolean operations: (a and b) or c"""
        a = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="a"),
            right=nodes.Boolean(val="true")
        )
        b = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="b"),
            right=nodes.Boolean(val="true")
        )
        c = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="c"),
            right=nodes.Boolean(val="true")
        )

        and_op = nodes.BoolOp(op=nodes.And(), left=a, right=b)
        or_op = nodes.BoolOp(op=nodes.Or(), left=and_op, right=c)

        assert isinstance(or_op.left, nodes.BoolOp)
        assert isinstance(or_op.left.op, nodes.And)


class TestUnaryOperators:
    """Tests for unary operator nodes."""

    def test_not_operator(self):
        """Test Not operator."""
        operand = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="active"),
            right=nodes.Boolean(val="false")
        )
        node = nodes.UnaryOp(op=nodes.Not(), operand=operand)

        assert isinstance(node.op, nodes.Not)
        assert isinstance(node.operand, nodes.Compare)

    def test_usub_operator(self):
        """Test unary negation (USub) operator."""
        operand = nodes.Identifier(name="value")
        node = nodes.UnaryOp(op=nodes.USub(), operand=operand)

        assert isinstance(node.op, nodes.USub)
        assert node.operand.name == "value"

    def test_nested_not(self):
        """Test nested not: not (not expression)"""
        inner = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="flag"),
            right=nodes.Boolean(val="true")
        )
        inner_not = nodes.UnaryOp(op=nodes.Not(), operand=inner)
        outer_not = nodes.UnaryOp(op=nodes.Not(), operand=inner_not)

        assert isinstance(outer_not.operand, nodes.UnaryOp)
        assert isinstance(outer_not.operand.op, nodes.Not)


# ==============================================================================
# Tests for Function Calls
# ==============================================================================


class TestFunctionCalls:
    """Tests for function call nodes."""

    def test_simple_function_call(self):
        """Test simple function call: contains(name, 'John')"""
        func = nodes.Identifier(name="contains")
        args = [
            nodes.Identifier(name="name"),
            nodes.String(val="'John'")
        ]
        node = nodes.Call(func=func, args=args)

        assert node.func.name == "contains"
        assert len(node.args) == 2
        assert node.args[0].name == "name"
        assert node.args[1].val == "'John'"

    def test_function_with_no_args(self):
        """Test function call with no arguments: now()"""
        func = nodes.Identifier(name="now")
        node = nodes.Call(func=func, args=[])

        assert node.func.name == "now"
        assert len(node.args) == 0

    def test_namespaced_function(self):
        """Test namespaced function: geo.distance()"""
        func = nodes.Identifier(name="distance", namespace=("geo",))
        args = [
            nodes.Identifier(name="location"),
            nodes.Identifier(name="point")
        ]
        node = nodes.Call(func=func, args=args)

        assert node.func.full_name() == "geo.distance"
        assert len(node.args) == 2

    def test_named_parameter(self):
        """Test named parameter in function call."""
        param = nodes.NamedParam(
            name=nodes.Identifier(name="param"),
            param=nodes.String(val="'value'")
        )

        assert param.name.name == "param"
        assert param.param.val == "'value'"

    def test_function_with_named_params(self):
        """Test function call with named parameters."""
        func = nodes.Identifier(name="func")
        args = [
            nodes.NamedParam(
                name=nodes.Identifier(name="x"),
                param=nodes.Integer(val="1")
            ),
            nodes.NamedParam(
                name=nodes.Identifier(name="y"),
                param=nodes.Integer(val="2")
            )
        ]
        node = nodes.Call(func=func, args=args)

        assert len(node.args) == 2
        assert isinstance(node.args[0], nodes.NamedParam)
        assert node.args[0].name.name == "x"


# ==============================================================================
# Tests for Collection Lambda Expressions
# ==============================================================================


class TestCollectionLambda:
    """Tests for collection lambda expressions (any/all)."""

    def test_any_operator_with_lambda(self):
        """Test any operator with lambda expression."""
        # comments/any(c: c/rating gt 4)
        owner = nodes.Identifier(name="comments")
        lambda_var = nodes.Identifier(name="c")
        lambda_expr = nodes.Compare(
            comparator=nodes.Gt(),
            left=nodes.Attribute(owner=lambda_var, attr="rating"),
            right=nodes.Float(val="4.0")
        )
        lambda_node = nodes.Lambda(identifier=lambda_var, expression=lambda_expr)
        node = nodes.CollectionLambda(
            owner=owner,
            operator=nodes.Any(),
            lambda_=lambda_node
        )

        assert isinstance(node.operator, nodes.Any)
        assert node.owner.name == "comments"
        assert node.lambda_.identifier.name == "c"
        assert isinstance(node.lambda_.expression, nodes.Compare)

    def test_any_without_lambda(self):
        """Test any operator without lambda (just check non-empty)."""
        # tags/any()
        owner = nodes.Identifier(name="tags")
        node = nodes.CollectionLambda(
            owner=owner,
            operator=nodes.Any(),
            lambda_=None
        )

        assert isinstance(node.operator, nodes.Any)
        assert node.owner.name == "tags"
        assert node.lambda_ is None

    def test_all_operator(self):
        """Test all operator with lambda expression."""
        # comments/all(c: c/status eq 'approved')
        owner = nodes.Identifier(name="comments")
        lambda_var = nodes.Identifier(name="c")
        lambda_expr = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Attribute(owner=lambda_var, attr="status"),
            right=nodes.String(val="'approved'")
        )
        lambda_node = nodes.Lambda(identifier=lambda_var, expression=lambda_expr)
        node = nodes.CollectionLambda(
            owner=owner,
            operator=nodes.All(),
            lambda_=lambda_node
        )

        assert isinstance(node.operator, nodes.All)
        assert node.lambda_.expression.left.attr == "status"

    def test_nested_lambda(self):
        """Test nested collection lambda expressions."""
        # posts/any(p: p/comments/any(c: c/rating gt 4))
        posts = nodes.Identifier(name="posts")
        p_var = nodes.Identifier(name="p")
        c_var = nodes.Identifier(name="c")

        inner_lambda = nodes.Lambda(
            identifier=c_var,
            expression=nodes.Compare(
                comparator=nodes.Gt(),
                left=nodes.Attribute(owner=c_var, attr="rating"),
                right=nodes.Float(val="4.0")
            )
        )
        inner_collection = nodes.CollectionLambda(
            owner=nodes.Attribute(owner=p_var, attr="comments"),
            operator=nodes.Any(),
            lambda_=inner_lambda
        )
        outer_lambda = nodes.Lambda(identifier=p_var, expression=inner_collection)
        outer_collection = nodes.CollectionLambda(
            owner=posts,
            operator=nodes.Any(),
            lambda_=outer_lambda
        )

        assert isinstance(outer_collection.lambda_.expression, nodes.CollectionLambda)
        assert outer_collection.lambda_.identifier.name == "p"


# ==============================================================================
# Tests for Visitor Pattern
# ==============================================================================


class TestNodeVisitor:
    """Tests for NodeVisitor pattern."""

    def test_visit_identifier(self):
        """Test visiting an Identifier node."""

        class TestVisitor(NodeVisitor):
            def __init__(self):
                self.visited = []

            def visit_Identifier(self, node):
                self.visited.append(node.name)
                return node.name

        visitor = TestVisitor()
        node = nodes.Identifier(name="test_field")
        result = visitor.visit(node)

        assert result == "test_field"
        assert "test_field" in visitor.visited

    def test_visit_compare_node(self):
        """Test visiting a Compare node."""

        class TestVisitor(NodeVisitor):
            def __init__(self):
                self.comparisons = []

            def visit_Compare(self, node):
                self.comparisons.append(type(node.comparator).__name__)
                self.generic_visit(node)

        visitor = TestVisitor()
        node = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="status"),
            right=nodes.String(val="'active'")
        )
        visitor.visit(node)

        assert "Eq" in visitor.comparisons

    def test_generic_visit_traverses_tree(self):
        """Test that generic_visit traverses the entire tree."""

        class CountingVisitor(NodeVisitor):
            def __init__(self):
                self.count = 0

            def generic_visit(self, node):
                self.count += 1
                super().generic_visit(node)

        visitor = CountingVisitor()
        # Create a tree: (a eq 1) and (b gt 2)
        tree = nodes.BoolOp(
            op=nodes.And(),
            left=nodes.Compare(
                comparator=nodes.Eq(),
                left=nodes.Identifier(name="a"),
                right=nodes.Integer(val="1")
            ),
            right=nodes.Compare(
                comparator=nodes.Gt(),
                left=nodes.Identifier(name="b"),
                right=nodes.Integer(val="2")
            )
        )

        visitor.visit(tree)
        # Should visit: BoolOp, And, Compare, Eq, Identifier, Integer, Compare, Gt, Identifier, Integer
        assert visitor.count > 5  # At least visited all major nodes

    def test_visit_list_of_nodes(self):
        """Test visitor handles lists of nodes (like function args)."""

        class ArgCountVisitor(NodeVisitor):
            def __init__(self):
                self.arg_count = 0

            def visit_Call(self, node):
                self.arg_count = len(node.args)
                self.generic_visit(node)

        visitor = ArgCountVisitor()
        node = nodes.Call(
            func=nodes.Identifier(name="func"),
            args=[
                nodes.Integer(val="1"),
                nodes.Integer(val="2"),
                nodes.Integer(val="3")
            ]
        )
        visitor.visit(node)

        assert visitor.arg_count == 3

    def test_visitor_with_no_matching_method(self):
        """Test visitor falls back to generic_visit when no method matches."""

        class PartialVisitor(NodeVisitor):
            def __init__(self):
                self.visited_types = []

            def generic_visit(self, node):
                self.visited_types.append(type(node).__name__)
                super().generic_visit(node)

        visitor = PartialVisitor()
        node = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="x"),
            right=nodes.Integer(val="1")
        )
        visitor.visit(node)

        # Should have visited Compare node via generic_visit
        assert "Compare" in visitor.visited_types


# ==============================================================================
# Tests for Transformer Pattern
# ==============================================================================


class TestNodeTransformer:
    """Tests for NodeTransformer pattern."""

    def test_transform_string_to_uppercase(self):
        """Test transformer that converts strings to uppercase."""

        class UppercaseTransformer(NodeTransformer):
            def visit_String(self, node):
                return nodes.String(val=node.val.upper())

        transformer = UppercaseTransformer()
        node = nodes.String(val="'hello'")
        result = transformer.visit(node)

        assert result.val == "'HELLO'"

    def test_transform_modifies_tree(self):
        """Test transformer modifies the tree structure."""

        class IncrementIntegerTransformer(NodeTransformer):
            def visit_Integer(self, node):
                new_val = str(int(node.val) + 1)
                return nodes.Integer(val=new_val)

        transformer = IncrementIntegerTransformer()
        node = nodes.Integer(val="5")
        result = transformer.visit(node)

        assert result.val == "6"
        assert result.py_val == 6

    def test_transform_complex_tree(self):
        """Test transformer on complex AST tree."""

        class DoubleIntegerTransformer(NodeTransformer):
            def visit_Integer(self, node):
                new_val = str(int(node.val) * 2)
                return nodes.Integer(val=new_val)

        transformer = DoubleIntegerTransformer()
        # Create: (age gt 10) and (score eq 100)
        tree = nodes.BoolOp(
            op=nodes.And(),
            left=nodes.Compare(
                comparator=nodes.Gt(),
                left=nodes.Identifier(name="age"),
                right=nodes.Integer(val="10")
            ),
            right=nodes.Compare(
                comparator=nodes.Eq(),
                left=nodes.Identifier(name="score"),
                right=nodes.Integer(val="100")
            )
        )

        result = transformer.visit(tree)

        # Check that integers were doubled
        assert result.left.right.py_val == 20  # 10 * 2
        assert result.right.right.py_val == 200  # 100 * 2

    def test_transformer_preserves_immutability(self):
        """Test that transformer creates new nodes (immutability)."""

        class IdentityTransformer(NodeTransformer):
            pass

        transformer = IdentityTransformer()
        original = nodes.Integer(val="42")
        result = transformer.visit(original)

        # Should be a new object (even though values are the same)
        assert result.val == original.val
        # Frozen dataclasses with same values will be equal
        assert result == original

    def test_transformer_can_replace_node_type(self):
        """Test transformer can replace one node type with another."""

        class ReplaceEqWithGtTransformer(NodeTransformer):
            def visit_Eq(self, node):
                return nodes.Gt()

        transformer = ReplaceEqWithGtTransformer()
        tree = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="x"),
            right=nodes.Integer(val="1")
        )

        result = transformer.visit(tree)
        assert isinstance(result.comparator, nodes.Gt)

    def test_optimizer_transformer(self):
        """Test optimizer that removes double negation: not (not x) -> x"""

        class OptimizeNotTransformer(NodeTransformer):
            def visit_UnaryOp(self, node):
                # First transform children
                node = self.generic_visit(node)

                # Optimize: not (not x) -> x
                if isinstance(node.op, nodes.Not):
                    if isinstance(node.operand, nodes.UnaryOp):
                        if isinstance(node.operand.op, nodes.Not):
                            # Return the inner operand, removing both nots
                            return node.operand.operand

                return node

        transformer = OptimizeNotTransformer()
        # Create: not (not (x eq 1))
        inner = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="x"),
            right=nodes.Integer(val="1")
        )
        inner_not = nodes.UnaryOp(op=nodes.Not(), operand=inner)
        outer_not = nodes.UnaryOp(op=nodes.Not(), operand=inner_not)

        result = transformer.visit(outer_not)

        # Should have removed both nots, leaving just the comparison
        assert isinstance(result, nodes.Compare)
        assert result.left.name == "x"


# ==============================================================================
# Tests for Utility Functions
# ==============================================================================


class TestUtilityFunctions:
    """Tests for visitor utility functions."""

    def test_iter_dataclass_fields(self):
        """Test iter_dataclass_fields utility function."""
        node = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="x"),
            right=nodes.Integer(val="1")
        )

        fields = list(iter_dataclass_fields(node))

        assert len(fields) == 3
        field_names = [name for name, _ in fields]
        assert "comparator" in field_names
        assert "left" in field_names
        assert "right" in field_names

    def test_iter_dataclass_fields_with_list(self):
        """Test iter_dataclass_fields with list field."""
        node = nodes.Call(
            func=nodes.Identifier(name="func"),
            args=[nodes.Integer(val="1"), nodes.Integer(val="2")]
        )

        fields = dict(iter_dataclass_fields(node))

        assert "func" in fields
        assert "args" in fields
        assert isinstance(fields["args"], list)
        assert len(fields["args"]) == 2


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestASTIntegration:
    """Integration tests for complex AST scenarios."""

    def test_complex_filter_expression(self):
        """Test complex filter expression AST."""
        # (status eq 'active' and age gt 18) or (role eq 'admin')
        status_check = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="status"),
            right=nodes.String(val="'active'")
        )
        age_check = nodes.Compare(
            comparator=nodes.Gt(),
            left=nodes.Identifier(name="age"),
            right=nodes.Integer(val="18")
        )
        role_check = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="role"),
            right=nodes.String(val="'admin'")
        )

        and_expr = nodes.BoolOp(op=nodes.And(), left=status_check, right=age_check)
        or_expr = nodes.BoolOp(op=nodes.Or(), left=and_expr, right=role_check)

        # Verify structure
        assert isinstance(or_expr.left, nodes.BoolOp)
        assert isinstance(or_expr.left.op, nodes.And)
        assert isinstance(or_expr.right, nodes.Compare)

    def test_visitor_and_transformer_combination(self):
        """Test using visitor for analysis and transformer for modification."""

        # First, use visitor to count nodes
        class NodeCounter(NodeVisitor):
            def __init__(self):
                self.count = 0

            def generic_visit(self, node):
                self.count += 1
                super().generic_visit(node)

        # Then, use transformer to modify
        class IncrementIntegers(NodeTransformer):
            def visit_Integer(self, node):
                return nodes.Integer(val=str(int(node.val) + 1))

        tree = nodes.Compare(
            comparator=nodes.Eq(),
            left=nodes.Identifier(name="x"),
            right=nodes.Integer(val="10")
        )

        # Count nodes
        counter = NodeCounter()
        counter.visit(tree)
        original_count = counter.count

        # Transform tree
        transformer = IncrementIntegers()
        new_tree = transformer.visit(tree)

        # Count nodes in new tree (should be same)
        counter2 = NodeCounter()
        counter2.visit(new_tree)

        assert counter2.count == original_count
        assert new_tree.right.py_val == 11  # 10 + 1
