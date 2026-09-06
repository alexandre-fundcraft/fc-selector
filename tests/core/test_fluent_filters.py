"""
Tests for the fluent type-safe filter API (Field, Expression).
"""

from fc_selector.core.ast import nodes as ast
from fc_selector.core.filters import Expression, Field


class TestField:
    """Tests for Field class."""

    def test_field_simple(self):
        """Field with simple name."""
        f = Field("name")
        assert repr(f) == "Field('name')"

    def test_field_nested(self):
        """Field with nested name using dots."""
        f = Field("author.name")
        assert repr(f) == "Field('author.name')"

    def test_field_nested_via_getattr(self):
        """Field with nested name using attribute access."""
        f = Field("author").name
        assert repr(f) == "Field('author.name')"

    def test_field_deeply_nested(self):
        """Field with deeply nested name."""
        f = Field("author").profile.address.city
        assert repr(f) == "Field('author.profile.address.city')"


class TestFieldComparisons:
    """Tests for Field comparison operators."""

    def test_eq(self):
        """Field.eq creates equality expression."""
        expr = Field("name").eq("John")
        assert isinstance(expr, Expression)
        node = expr.to_ast()
        assert isinstance(node, ast.Compare)
        assert isinstance(node.comparator, ast.Eq)
        assert isinstance(node.left, ast.Identifier)
        assert node.left.name == "name"
        assert isinstance(node.right, ast.String)

    def test_ne(self):
        """Field.ne creates not-equal expression."""
        expr = Field("status").ne("deleted")
        node = expr.to_ast()
        assert isinstance(node.comparator, ast.NotEq)

    def test_gt(self):
        """Field.gt creates greater-than expression."""
        expr = Field("age").gt(18)
        node = expr.to_ast()
        assert isinstance(node.comparator, ast.Gt)
        assert isinstance(node.right, ast.Integer)

    def test_ge(self):
        """Field.ge creates greater-or-equal expression."""
        expr = Field("price").ge(100.5)
        node = expr.to_ast()
        assert isinstance(node.comparator, ast.GtE)
        assert isinstance(node.right, ast.Float)

    def test_lt(self):
        """Field.lt creates less-than expression."""
        expr = Field("count").lt(10)
        node = expr.to_ast()
        assert isinstance(node.comparator, ast.Lt)

    def test_le(self):
        """Field.le creates less-or-equal expression."""
        expr = Field("rating").le(5)
        node = expr.to_ast()
        assert isinstance(node.comparator, ast.LtE)

    def test_eq_with_boolean(self):
        """Field.eq with boolean value."""
        expr = Field("active").eq(True)
        node = expr.to_ast()
        assert isinstance(node.right, ast.Boolean)
        assert node.right.val == "true"

    def test_eq_with_none(self):
        """Field.eq with None becomes null check."""
        expr = Field("deleted_at").eq(None)
        node = expr.to_ast()
        assert isinstance(node.right, ast.Null)


class TestFieldNullChecks:
    """Tests for Field null check methods."""

    def test_is_null(self):
        """Field.is_null creates null equality."""
        expr = Field("deleted_at").is_null()
        node = expr.to_ast()
        assert isinstance(node.comparator, ast.Eq)
        assert isinstance(node.right, ast.Null)

    def test_is_not_null(self):
        """Field.is_not_null creates null inequality."""
        expr = Field("name").is_not_null()
        node = expr.to_ast()
        assert isinstance(node.comparator, ast.NotEq)
        assert isinstance(node.right, ast.Null)


class TestFieldInOperator:
    """Tests for Field in operator methods."""

    def test_is_in(self):
        """Field.is_in creates in expression."""
        expr = Field("status").is_in(["active", "pending"])
        node = expr.to_ast()
        assert isinstance(node.comparator, ast.In)
        assert isinstance(node.right, ast.List)
        assert len(node.right.val) == 2

    def test_not_in(self):
        """Field.not_in creates negated in expression."""
        expr = Field("status").not_in(["deleted", "archived"])
        node = expr.to_ast()
        # Should be: NOT (field IN [...])
        assert isinstance(node, ast.UnaryOp)
        assert isinstance(node.op, ast.Not)
        assert isinstance(node.operand, ast.Compare)
        assert isinstance(node.operand.comparator, ast.In)


class TestFieldStringFunctions:
    """Tests for Field string function methods."""

    def test_contains(self):
        """Field.contains creates contains function call."""
        expr = Field("name").contains("john")
        node = expr.to_ast()
        assert isinstance(node, ast.Call)
        assert node.func.name == "contains"
        assert len(node.args) == 2

    def test_startswith(self):
        """Field.startswith creates startswith function call."""
        expr = Field("email").startswith("admin")
        node = expr.to_ast()
        assert isinstance(node, ast.Call)
        assert node.func.name == "startswith"

    def test_endswith(self):
        """Field.endswith creates endswith function call."""
        expr = Field("email").endswith("@example.com")
        node = expr.to_ast()
        assert isinstance(node, ast.Call)
        assert node.func.name == "endswith"

    def test_matches(self):
        """Field.matches creates matchesPattern function call."""
        expr = Field("code").matches("^[A-Z]{3}$")
        node = expr.to_ast()
        assert isinstance(node, ast.Call)
        assert node.func.name == "matchesPattern"


class TestFieldRangeOperations:
    """Tests for Field range operations."""

    def test_between(self):
        """Field.between creates combined ge and le expression."""
        expr = Field("price").between(10, 100)
        node = expr.to_ast()
        # Should be: (field >= 10) AND (field <= 100)
        assert isinstance(node, ast.BoolOp)
        assert isinstance(node.op, ast.And)
        assert isinstance(node.left, ast.Compare)
        assert isinstance(node.left.comparator, ast.GtE)
        assert isinstance(node.right, ast.Compare)
        assert isinstance(node.right.comparator, ast.LtE)


class TestExpressionComposition:
    """Tests for Expression composition with operators."""

    def test_and(self):
        """Expression & Expression creates AND."""
        expr1 = Field("name").eq("John")
        expr2 = Field("age").gt(18)
        combined = expr1 & expr2

        node = combined.to_ast()
        assert isinstance(node, ast.BoolOp)
        assert isinstance(node.op, ast.And)

    def test_or(self):
        """Expression | Expression creates OR."""
        expr1 = Field("role").eq("admin")
        expr2 = Field("role").eq("superuser")
        combined = expr1 | expr2

        node = combined.to_ast()
        assert isinstance(node, ast.BoolOp)
        assert isinstance(node.op, ast.Or)

    def test_not(self):
        """~Expression creates NOT."""
        expr = Field("deleted").eq(True)
        negated = ~expr

        node = negated.to_ast()
        assert isinstance(node, ast.UnaryOp)
        assert isinstance(node.op, ast.Not)

    def test_complex_composition(self):
        """Complex expression composition."""
        # (name eq 'John' AND age gt 18) OR vip eq true
        expr = (Field("name").eq("John") & Field("age").gt(18)) | Field("vip").eq(True)

        node = expr.to_ast()
        assert isinstance(node, ast.BoolOp)
        assert isinstance(node.op, ast.Or)
        assert isinstance(node.left, ast.BoolOp)
        assert isinstance(node.left.op, ast.And)

    def test_multiple_and(self):
        """Multiple AND expressions."""
        expr = Field("a").eq(1) & Field("b").eq(2) & Field("c").eq(3)

        # Should form a left-associative tree
        node = expr.to_ast()
        assert isinstance(node, ast.BoolOp)


class TestFieldNestedAccess:
    """Tests for Field nested field access."""

    def test_nested_identifier(self):
        """Nested field builds Attribute chain."""
        f = Field("author.name")
        expr = f.eq("John")
        node = expr.to_ast()

        assert isinstance(node.left, ast.Attribute)
        assert node.left.attr == "name"
        assert isinstance(node.left.owner, ast.Identifier)
        assert node.left.owner.name == "author"

    def test_deeply_nested_identifier(self):
        """Deeply nested field builds deep Attribute chain."""
        f = Field("author.profile.avatar.url")
        expr = f.contains("gravatar")
        node = expr.to_ast()

        # The first arg should be the nested attribute
        field_node = node.args[0]
        assert isinstance(field_node, ast.Attribute)
        assert field_node.attr == "url"


class TestFieldAliases:
    """Tests for SQL-style method aliases."""


class TestExpressionEquality:
    """Tests for Expression __eq__ and __hash__ methods."""

    def test_equal_expressions(self):
        """Two expressions with same AST are equal."""
        expr1 = Field("name").eq("John")
        expr2 = Field("name").eq("John")
        assert expr1 == expr2

    def test_unequal_expressions_different_field(self):
        """Expressions with different fields are not equal."""
        expr1 = Field("name").eq("John")
        expr2 = Field("email").eq("John")
        assert expr1 != expr2

    def test_unequal_expressions_different_value(self):
        """Expressions with different values are not equal."""
        expr1 = Field("name").eq("John")
        expr2 = Field("name").eq("Jane")
        assert expr1 != expr2

    def test_expression_not_equal_to_non_expression(self):
        """Expression is not equal to non-Expression objects."""
        expr = Field("name").eq("John")
        assert expr != "not an expression"
        assert expr != 42
        assert expr is not None
        assert expr != {"node": "dict"}

    def test_expression_hash_consistent(self):
        """Same expression produces same hash."""
        expr1 = Field("name").eq("John")
        expr2 = Field("name").eq("John")
        assert hash(expr1) == hash(expr2)

    def test_expression_usable_in_set(self):
        """Expressions can be used in sets."""
        expr1 = Field("name").eq("John")
        expr2 = Field("name").eq("John")
        expr3 = Field("age").gt(18)

        s = {expr1, expr2, expr3}
        # expr1 and expr2 are equal, so set should have 2 elements
        assert len(s) == 2

    def test_expression_usable_as_dict_key(self):
        """Expressions can be used as dictionary keys."""
        expr1 = Field("name").eq("John")
        expr2 = Field("name").eq("John")

        d = {expr1: "first"}
        d[expr2] = "second"  # Should overwrite since equal

        assert len(d) == 1
        assert d[expr1] == "second"
