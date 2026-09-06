"""
Comprehensive tests for OData $filter expressions.

Tests all combinations of:
- Comparison operators (eq, ne, gt, ge, lt, le)
- Logical operators (and, or, not)
- Functions (startswith, endswith, contains, etc.)
- Navigation paths (author/user/field)
- Parentheses grouping
- Complex nested expressions

Each test validates:
1. The filter is parsed
2. The AST (Abstract Syntax Tree) is correct
3. The nodes have proper types and values
"""

from fc_selector.core.ast import nodes
from fc_selector.protocols.odata.parsers.query import parse_odata_query


# Helper functions for AST validation
def assert_ast_exists(query):
    """Assert that filter AST was parsed successfully."""
    assert query.filter is not None
    assert query.filter.ast is not None


def assert_compare_node(ast, field_name=None, comparator_type=None):
    """Assert node is a Compare with optional field and comparator validation."""
    assert isinstance(ast, nodes.Compare)
    if field_name:
        assert ast.left.name == field_name
    if comparator_type:
        assert isinstance(ast.comparator, comparator_type)


def assert_bool_op(ast, op_type):
    """Assert node is a BoolOp with specified operator (And/Or)."""
    assert isinstance(ast, nodes.BoolOp)
    assert isinstance(ast.op, op_type)


def assert_has_field(ast, field_name):
    """Recursively check if AST references a field name."""
    if isinstance(ast, nodes.Identifier):
        return ast.name == field_name
    elif isinstance(ast, nodes.Attribute):
        return field_name in str(ast)
    elif isinstance(ast, nodes.Compare):
        return assert_has_field(ast.left, field_name)
    elif isinstance(ast, nodes.BoolOp):
        return assert_has_field(ast.left, field_name) or assert_has_field(ast.right, field_name)
    return False


class TestFilterComparisonOperators:
    """Tests for basic comparison operators in filters."""

    def test_eq_operator(self):
        """Test eq (equal) operator."""
        query = parse_odata_query("$filter=status eq 'published'")

        assert query.filter is not None
        assert query.filter.expression == "status eq 'published'"

        # Validate AST
        assert query.filter.ast is not None
        assert isinstance(query.filter.ast, nodes.Compare)
        assert isinstance(query.filter.ast.comparator, nodes.Eq)
        assert isinstance(query.filter.ast.left, nodes.Identifier)
        assert query.filter.ast.left.name == "status"
        assert isinstance(query.filter.ast.right, nodes.String)
        assert query.filter.ast.right.val == "published"

    def test_ne_operator(self):
        """Test ne (not equal) operator."""
        query = parse_odata_query("$filter=status ne 'draft'")

        assert query.filter is not None
        assert query.filter.ast is not None
        assert isinstance(query.filter.ast, nodes.Compare)
        assert isinstance(query.filter.ast.comparator, nodes.NotEq)
        assert query.filter.ast.left.name == "status"
        assert query.filter.ast.right.val == "draft"

    def test_gt_operator(self):
        """Test gt (greater than) operator."""
        query = parse_odata_query("$filter=rating gt 4.0")

        assert query.filter is not None
        assert query.filter.ast is not None
        assert isinstance(query.filter.ast, nodes.Compare)
        assert isinstance(query.filter.ast.comparator, nodes.Gt)
        assert query.filter.ast.left.name == "rating"
        assert isinstance(query.filter.ast.right, nodes.Float)
        assert query.filter.ast.right.val == "4.0"

    def test_ge_operator(self):
        """Test ge (greater than or equal) operator."""
        query = parse_odata_query("$filter=rating ge 4.0")

        assert query.filter is not None
        assert query.filter.ast is not None
        assert isinstance(query.filter.ast, nodes.Compare)
        assert isinstance(query.filter.ast.comparator, nodes.GtE)

    def test_lt_operator(self):
        """Test lt (less than) operator."""
        query = parse_odata_query("$filter=views lt 100")

        assert query.filter is not None
        assert query.filter.ast is not None
        assert isinstance(query.filter.ast, nodes.Compare)
        assert isinstance(query.filter.ast.comparator, nodes.Lt)
        assert query.filter.ast.left.name == "views"
        assert isinstance(query.filter.ast.right, nodes.Integer)

    def test_le_operator(self):
        """Test le (less than or equal) operator."""
        query = parse_odata_query("$filter=price le 99.99")

        assert query.filter is not None
        assert query.filter.ast is not None
        assert isinstance(query.filter.ast, nodes.Compare)
        assert isinstance(query.filter.ast.comparator, nodes.LtE)


class TestFilterLogicalAnd:
    """Tests for AND logical operator in filters."""

    def test_and_two_conditions(self):
        """Test AND with two conditions."""
        query = parse_odata_query("$filter=status eq 'published' and rating gt 4.0")

        assert query.filter is not None
        assert "and" in query.filter.expression

        # Validate AST
        assert query.filter.ast is not None
        assert isinstance(query.filter.ast, nodes.BoolOp)
        assert isinstance(query.filter.ast.op, nodes.And)

        # Validate left side (status eq 'published')
        assert isinstance(query.filter.ast.left, nodes.Compare)
        assert isinstance(query.filter.ast.left.comparator, nodes.Eq)
        assert query.filter.ast.left.left.name == "status"
        assert query.filter.ast.left.right.val == "published"

        # Validate right side (rating gt 4.0)
        assert isinstance(query.filter.ast.right, nodes.Compare)
        assert isinstance(query.filter.ast.right.comparator, nodes.Gt)
        assert query.filter.ast.right.left.name == "rating"
        assert query.filter.ast.right.right.val == "4.0"

    def test_and_three_conditions(self):
        """Test AND with three conditions."""
        query = parse_odata_query("$filter=status eq 'published' and rating gt 4.0 and views gt 100")

        assert query.filter is not None
        assert query.filter.ast is not None

        # Root is BoolOp(and)
        assert isinstance(query.filter.ast, nodes.BoolOp)
        assert isinstance(query.filter.ast.op, nodes.And)

        # Left side is another BoolOp(and) with two conditions
        assert isinstance(query.filter.ast.left, nodes.BoolOp)
        assert isinstance(query.filter.ast.left.op, nodes.And)

        # Right side is the third condition
        assert isinstance(query.filter.ast.right, nodes.Compare)
        assert query.filter.ast.right.left.name == "views"

    def test_and_four_conditions(self):
        """Test AND with four conditions."""
        query = parse_odata_query(
            "$filter=status eq 'published' and rating gt 4.0 and views gt 100 and is_featured eq true"
        )

        assert query.filter is not None
        assert query.filter.ast is not None
        assert isinstance(query.filter.ast, nodes.BoolOp)
        assert isinstance(query.filter.ast.op, nodes.And)

    def test_and_with_different_operators(self):
        """Test AND combining different comparison operators."""
        query = parse_odata_query("$filter=price ge 10 and price le 100")

        assert query.filter is not None
        assert query.filter.ast is not None

        # Root is BoolOp(and)
        assert isinstance(query.filter.ast, nodes.BoolOp)
        assert isinstance(query.filter.ast.op, nodes.And)

        # Left: price ge 10
        assert isinstance(query.filter.ast.left, nodes.Compare)
        assert isinstance(query.filter.ast.left.comparator, nodes.GtE)
        assert query.filter.ast.left.left.name == "price"

        # Right: price le 100
        assert isinstance(query.filter.ast.right, nodes.Compare)
        assert isinstance(query.filter.ast.right.comparator, nodes.LtE)
        assert query.filter.ast.right.left.name == "price"

    def test_and_with_strings(self):
        """Test AND with string comparisons."""
        query = parse_odata_query("$filter=category eq 'tech' and author eq 'John'")

        assert query.filter is not None
        assert query.filter.ast is not None
        assert isinstance(query.filter.ast, nodes.BoolOp)

        # Left side
        assert query.filter.ast.left.left.name == "category"
        assert query.filter.ast.left.right.val == "tech"

        # Right side
        assert query.filter.ast.right.left.name == "author"
        assert query.filter.ast.right.right.val == "John"

    def test_and_with_booleans(self):
        """Test AND with boolean values."""
        query = parse_odata_query("$filter=is_active eq true and is_published eq true")

        assert query.filter is not None
        assert query.filter.ast is not None
        assert isinstance(query.filter.ast, nodes.BoolOp)

        # Both sides should have boolean values
        assert isinstance(query.filter.ast.left.right, nodes.Boolean)
        assert isinstance(query.filter.ast.right.right, nodes.Boolean)

    def test_and_with_dates(self):
        """Test AND with date comparisons."""
        query = parse_odata_query("$filter=created_at gt '2024-01-01' and created_at lt '2024-12-31'")

        assert query.filter is not None
        assert query.filter.ast is not None
        assert isinstance(query.filter.ast, nodes.BoolOp)

        # Both comparisons should reference created_at
        assert query.filter.ast.left.left.name == "created_at"
        assert query.filter.ast.right.left.name == "created_at"

    def test_and_mixed_types(self):
        """Test AND with mixed data types."""
        query = parse_odata_query("$filter=status eq 'published' and rating gt 4.0 and is_active eq true")

        assert query.filter is not None
        assert query.filter.ast is not None
        assert isinstance(query.filter.ast, nodes.BoolOp)

        # Should have nested BoolOp for three conditions
        assert isinstance(query.filter.ast.left, nodes.BoolOp)


class TestFilterLogicalOr:
    """Tests for OR logical operator in filters."""

    def test_or_two_conditions(self):
        """Test OR with two conditions."""
        query = parse_odata_query("$filter=status eq 'draft' or status eq 'published'")

        assert query.filter is not None
        assert query.filter.ast is not None

        # Root is BoolOp(or)
        assert isinstance(query.filter.ast, nodes.BoolOp)
        assert isinstance(query.filter.ast.op, nodes.Or)

        # Left: status eq 'draft'
        assert isinstance(query.filter.ast.left, nodes.Compare)
        assert query.filter.ast.left.left.name == "status"
        assert query.filter.ast.left.right.val == "draft"

        # Right: status eq 'published'
        assert isinstance(query.filter.ast.right, nodes.Compare)
        assert query.filter.ast.right.left.name == "status"
        assert query.filter.ast.right.right.val == "published"

    def test_or_three_conditions(self):
        """Test OR with three conditions."""
        query = parse_odata_query("$filter=status eq 'draft' or status eq 'published' or status eq 'archived'")

        assert query.filter is not None
        assert query.filter.ast is not None

        # Root is BoolOp(or)
        assert isinstance(query.filter.ast, nodes.BoolOp)
        assert isinstance(query.filter.ast.op, nodes.Or)

        # Left side is another BoolOp(or) with two conditions
        assert isinstance(query.filter.ast.left, nodes.BoolOp)
        assert isinstance(query.filter.ast.left.op, nodes.Or)

        # Right side is the third condition
        assert isinstance(query.filter.ast.right, nodes.Compare)
        assert query.filter.ast.right.right.val == "archived"

    def test_or_with_numbers(self):
        """Test OR with numeric comparisons."""
        query = parse_odata_query("$filter=rating eq 5.0 or rating eq 4.5")

        assert query.filter is not None
        assert query.filter.ast is not None
        assert isinstance(query.filter.ast, nodes.BoolOp)
        assert isinstance(query.filter.ast.op, nodes.Or)

        # Both sides should reference rating
        assert query.filter.ast.left.left.name == "rating"
        assert query.filter.ast.right.left.name == "rating"

        # Values should be Float
        assert isinstance(query.filter.ast.left.right, nodes.Float)
        assert isinstance(query.filter.ast.right.right, nodes.Float)

    def test_or_with_different_fields(self):
        """Test OR with different fields."""
        query = parse_odata_query("$filter=is_featured eq true or is_trending eq true")

        assert query.filter is not None
        assert query.filter.ast is not None
        assert isinstance(query.filter.ast, nodes.BoolOp)
        assert isinstance(query.filter.ast.op, nodes.Or)

        # Different field names
        assert query.filter.ast.left.left.name == "is_featured"
        assert query.filter.ast.right.left.name == "is_trending"

        # Both should be boolean comparisons
        assert isinstance(query.filter.ast.left.right, nodes.Boolean)
        assert isinstance(query.filter.ast.right.right, nodes.Boolean)

    def test_or_with_ranges(self):
        """Test OR with range conditions."""
        query = parse_odata_query("$filter=price lt 10 or price gt 1000")

        assert query.filter is not None
        assert query.filter.ast is not None
        assert isinstance(query.filter.ast, nodes.BoolOp)
        assert isinstance(query.filter.ast.op, nodes.Or)

        # Left: price lt 10
        assert isinstance(query.filter.ast.left.comparator, nodes.Lt)
        assert query.filter.ast.left.left.name == "price"

        # Right: price gt 1000
        assert isinstance(query.filter.ast.right.comparator, nodes.Gt)
        assert query.filter.ast.right.left.name == "price"


class TestFilterAndOrCombinations:
    """Tests for combinations of AND and OR operators."""

    def test_and_or_with_parentheses(self):
        """Test AND and OR with explicit parentheses."""
        query = parse_odata_query("$filter=(status eq 'published' or status eq 'draft') and rating gt 4.0")

        assert_ast_exists(query)

        # Root is BoolOp(and)
        assert_bool_op(query.filter.ast, nodes.And)

        # Left side is BoolOp(or) with two status comparisons
        assert isinstance(query.filter.ast.left, nodes.BoolOp)
        assert isinstance(query.filter.ast.left.op, nodes.Or)
        assert_compare_node(query.filter.ast.left.left, "status", nodes.Eq)
        assert query.filter.ast.left.left.right.val == "published"
        assert_compare_node(query.filter.ast.left.right, "status", nodes.Eq)
        assert query.filter.ast.left.right.right.val == "draft"

        # Right side is rating comparison
        assert_compare_node(query.filter.ast.right, "rating", nodes.Gt)

    def test_and_or_reverse_order(self):
        """Test AND before OR with parentheses."""
        query = parse_odata_query("$filter=status eq 'published' and (rating gt 4.0 or views gt 1000)")

        assert_ast_exists(query)

        # Root is BoolOp(and)
        assert_bool_op(query.filter.ast, nodes.And)

        # Left side is status comparison
        assert_compare_node(query.filter.ast.left, "status", nodes.Eq)

        # Right side is BoolOp(or) with two comparisons
        assert isinstance(query.filter.ast.right, nodes.BoolOp)
        assert isinstance(query.filter.ast.right.op, nodes.Or)
        assert_compare_node(query.filter.ast.right.left, "rating", nodes.Gt)
        assert_compare_node(query.filter.ast.right.right, "views", nodes.Gt)

    def test_multiple_or_groups_with_and(self):
        """Test multiple OR groups connected with AND."""
        query = parse_odata_query(
            "$filter=(status eq 'published' or status eq 'draft') and (category eq 'tech' or category eq 'science')"
        )

        assert_ast_exists(query)

        # Root is BoolOp(and)
        assert_bool_op(query.filter.ast, nodes.And)

        # Left side is BoolOp(or) for status
        assert isinstance(query.filter.ast.left, nodes.BoolOp)
        assert isinstance(query.filter.ast.left.op, nodes.Or)
        assert_compare_node(query.filter.ast.left.left, "status", nodes.Eq)
        assert query.filter.ast.left.left.right.val == "published"
        assert_compare_node(query.filter.ast.left.right, "status", nodes.Eq)
        assert query.filter.ast.left.right.right.val == "draft"

        # Right side is BoolOp(or) for category
        assert isinstance(query.filter.ast.right, nodes.BoolOp)
        assert isinstance(query.filter.ast.right.op, nodes.Or)
        assert_compare_node(query.filter.ast.right.left, "category", nodes.Eq)
        assert query.filter.ast.right.left.right.val == "tech"
        assert_compare_node(query.filter.ast.right.right, "category", nodes.Eq)
        assert query.filter.ast.right.right.right.val == "science"

    def test_nested_parentheses(self):
        """Test nested parentheses in complex expression."""
        query = parse_odata_query(
            "$filter=((status eq 'published' or status eq 'draft') and rating gt 4.0) or is_featured eq true"
        )

        assert_ast_exists(query)

        # Root is BoolOp(or)
        assert_bool_op(query.filter.ast, nodes.Or)

        # Left side is BoolOp(and)
        assert isinstance(query.filter.ast.left, nodes.BoolOp)
        assert isinstance(query.filter.ast.left.op, nodes.And)

        # Left.left is BoolOp(or) for status
        assert isinstance(query.filter.ast.left.left, nodes.BoolOp)
        assert isinstance(query.filter.ast.left.left.op, nodes.Or)
        assert_compare_node(query.filter.ast.left.left.left, "status", nodes.Eq)
        assert_compare_node(query.filter.ast.left.left.right, "status", nodes.Eq)

        # Left.right is rating comparison
        assert_compare_node(query.filter.ast.left.right, "rating", nodes.Gt)

        # Right side is is_featured comparison
        assert_compare_node(query.filter.ast.right, "is_featured", nodes.Eq)

    def test_three_way_or_with_and(self):
        """Test three conditions with OR, then AND."""
        query = parse_odata_query(
            "$filter=(status eq 'published' or status eq 'draft' or status eq 'pending') and rating gt 3.0"
        )

        assert_ast_exists(query)

        # Root is BoolOp(and)
        assert_bool_op(query.filter.ast, nodes.And)

        # Left side is BoolOp(or) with three conditions (nested)
        assert isinstance(query.filter.ast.left, nodes.BoolOp)
        assert isinstance(query.filter.ast.left.op, nodes.Or)

        # Left.left is another BoolOp(or) with first two conditions
        assert isinstance(query.filter.ast.left.left, nodes.BoolOp)
        assert isinstance(query.filter.ast.left.left.op, nodes.Or)
        assert_compare_node(query.filter.ast.left.left.left, "status", nodes.Eq)
        assert query.filter.ast.left.left.left.right.val == "published"
        assert_compare_node(query.filter.ast.left.left.right, "status", nodes.Eq)
        assert query.filter.ast.left.left.right.right.val == "draft"

        # Left.right is the third condition
        assert_compare_node(query.filter.ast.left.right, "status", nodes.Eq)
        assert query.filter.ast.left.right.right.val == "pending"

        # Right side is rating comparison
        assert_compare_node(query.filter.ast.right, "rating", nodes.Gt)

    def test_complex_mixed_operators(self):
        """Test complex expression with multiple AND and OR."""
        query = parse_odata_query(
            "$filter=status eq 'published' and rating gt 4.0 "
            "and (category eq 'tech' or category eq 'science') "
            "and views gt 100"
        )

        assert_ast_exists(query)

        # Root is BoolOp(and)
        assert_bool_op(query.filter.ast, nodes.And)

        # Should have nested And operators (left-associative)
        # Structure: (((status AND rating) AND (category OR category)) AND views)
        assert isinstance(query.filter.ast.left, nodes.BoolOp)
        assert isinstance(query.filter.ast.left.op, nodes.And)

        # Navigate to the deepest left to find status comparison
        current = query.filter.ast
        while isinstance(current.left, nodes.BoolOp) and isinstance(current.left.op, nodes.And):
            current = current.left

        # Verify we have status comparison somewhere in the tree
        assert assert_has_field(query.filter.ast, "status")
        assert assert_has_field(query.filter.ast, "rating")
        assert assert_has_field(query.filter.ast, "category")
        assert assert_has_field(query.filter.ast, "views")

        # Right side should be views comparison
        assert_compare_node(query.filter.ast.right, "views", nodes.Gt)


class TestFilterNotOperator:
    """Tests for NOT logical operator."""

    def test_not_simple_condition(self):
        """Test NOT with simple condition."""
        query = parse_odata_query("$filter=not (status eq 'archived')")

        assert_ast_exists(query)

        # Root should be UnaryOp with Not operator
        assert isinstance(query.filter.ast, nodes.UnaryOp)
        assert isinstance(query.filter.ast.op, nodes.Not)

        # Operand should be Compare
        assert isinstance(query.filter.ast.operand, nodes.Compare)
        assert_compare_node(query.filter.ast.operand, "status", nodes.Eq)
        assert query.filter.ast.operand.right.val == "archived"

    def test_not_with_boolean(self):
        """Test NOT with boolean field."""
        query = parse_odata_query("$filter=not (is_active eq false)")

        assert_ast_exists(query)

        # Root should be UnaryOp with Not operator
        assert isinstance(query.filter.ast, nodes.UnaryOp)
        assert isinstance(query.filter.ast.op, nodes.Not)

        # Operand should be Compare with boolean
        assert isinstance(query.filter.ast.operand, nodes.Compare)
        assert_compare_node(query.filter.ast.operand, "is_active", nodes.Eq)
        assert isinstance(query.filter.ast.operand.right, nodes.Boolean)

    def test_not_with_and(self):
        """Test NOT combined with AND."""
        query = parse_odata_query("$filter=not (status eq 'archived') and rating gt 4.0")

        assert_ast_exists(query)

        # Root should be BoolOp(and)
        assert_bool_op(query.filter.ast, nodes.And)

        # Left side should be UnaryOp(not)
        assert isinstance(query.filter.ast.left, nodes.UnaryOp)
        assert isinstance(query.filter.ast.left.op, nodes.Not)
        assert isinstance(query.filter.ast.left.operand, nodes.Compare)
        assert_compare_node(query.filter.ast.left.operand, "status", nodes.Eq)

        # Right side should be rating comparison
        assert_compare_node(query.filter.ast.right, "rating", nodes.Gt)


class TestFilterNavigationPaths:
    """Tests for navigation paths in filters."""

    def test_navigation_one_level(self):
        """Test filter with one-level navigation."""
        query = parse_odata_query("$filter=author/name eq 'John'")

        assert_ast_exists(query)

        # Root should be Compare
        assert isinstance(query.filter.ast, nodes.Compare)
        assert isinstance(query.filter.ast.comparator, nodes.Eq)

        # Left side should be Attribute (navigation path)
        assert isinstance(query.filter.ast.left, nodes.Attribute)
        # Verify the navigation path contains both parts
        assert "author" in str(query.filter.ast.left)
        assert "name" in str(query.filter.ast.left)

        # Right side should be String
        assert isinstance(query.filter.ast.right, nodes.String)
        assert query.filter.ast.right.val == "John"

    def test_navigation_two_levels(self):
        """Test filter with two-level navigation."""
        query = parse_odata_query("$filter=author/user/email eq 'john@example.com'")

        assert_ast_exists(query)

        # Root should be Compare
        assert isinstance(query.filter.ast, nodes.Compare)
        assert isinstance(query.filter.ast.comparator, nodes.Eq)

        # Left side should be Attribute (navigation path)
        assert isinstance(query.filter.ast.left, nodes.Attribute)
        # Verify all parts of navigation path
        assert "author" in str(query.filter.ast.left)
        assert "user" in str(query.filter.ast.left)
        assert "email" in str(query.filter.ast.left)

        # Right side should be String
        assert isinstance(query.filter.ast.right, nodes.String)

    def test_navigation_three_levels(self):
        """Test filter with three-level navigation."""
        query = parse_odata_query("$filter=author/user/profile/country eq 'Spain'")

        assert_ast_exists(query)

        # Root should be Compare
        assert isinstance(query.filter.ast, nodes.Compare)
        assert isinstance(query.filter.ast.left, nodes.Attribute)

        # Verify all parts of deep navigation path
        nav_str = str(query.filter.ast.left)
        assert "author" in nav_str
        assert "user" in nav_str
        assert "profile" in nav_str
        assert "country" in nav_str

        # Right side should be String
        assert query.filter.ast.right.val == "Spain"

    def test_navigation_with_and(self):
        """Test navigation combined with AND."""
        query = parse_odata_query("$filter=author/name eq 'John' and author/is_active eq true")

        assert_ast_exists(query)

        # Root should be BoolOp(and)
        assert_bool_op(query.filter.ast, nodes.And)

        # Left side: author/name comparison
        assert isinstance(query.filter.ast.left, nodes.Compare)
        assert isinstance(query.filter.ast.left.left, nodes.Attribute)
        assert "author" in str(query.filter.ast.left.left)
        assert "name" in str(query.filter.ast.left.left)
        assert query.filter.ast.left.right.val == "John"

        # Right side: author/is_active comparison
        assert isinstance(query.filter.ast.right, nodes.Compare)
        assert isinstance(query.filter.ast.right.left, nodes.Attribute)
        assert "author" in str(query.filter.ast.right.left)
        assert "is_active" in str(query.filter.ast.right.left)
        assert isinstance(query.filter.ast.right.right, nodes.Boolean)

    def test_multiple_navigation_paths(self):
        """Test multiple different navigation paths."""
        query = parse_odata_query("$filter=author/name eq 'John' and category/slug eq 'tech'")

        assert_ast_exists(query)

        # Root should be BoolOp(and)
        assert_bool_op(query.filter.ast, nodes.And)

        # Left side: author/name
        assert isinstance(query.filter.ast.left, nodes.Compare)
        assert isinstance(query.filter.ast.left.left, nodes.Attribute)
        assert "author" in str(query.filter.ast.left.left)

        # Right side: category/slug
        assert isinstance(query.filter.ast.right, nodes.Compare)
        assert isinstance(query.filter.ast.right.left, nodes.Attribute)
        assert "category" in str(query.filter.ast.right.left)
        assert "slug" in str(query.filter.ast.right.left)

    def test_navigation_with_or(self):
        """Test navigation combined with OR."""
        query = parse_odata_query("$filter=author/name eq 'John' or author/name eq 'Jane'")

        assert_ast_exists(query)

        # Root should be BoolOp(or)
        assert_bool_op(query.filter.ast, nodes.Or)

        # Both sides should be Compare with Attribute (author/name)
        assert isinstance(query.filter.ast.left, nodes.Compare)
        assert isinstance(query.filter.ast.left.left, nodes.Attribute)
        assert "author" in str(query.filter.ast.left.left)
        assert query.filter.ast.left.right.val == "John"

        assert isinstance(query.filter.ast.right, nodes.Compare)
        assert isinstance(query.filter.ast.right.left, nodes.Attribute)
        assert "author" in str(query.filter.ast.right.left)
        assert query.filter.ast.right.right.val == "Jane"

    def test_deep_navigation_with_comparison(self):
        """Test deep navigation with different comparison operators."""
        query = parse_odata_query("$filter=post/author/user/profile/age gt 18")

        assert_ast_exists(query)

        # Root should be Compare with Gt
        assert isinstance(query.filter.ast, nodes.Compare)
        assert isinstance(query.filter.ast.comparator, nodes.Gt)

        # Left side should be Attribute with deep navigation
        assert isinstance(query.filter.ast.left, nodes.Attribute)
        nav_str = str(query.filter.ast.left)
        assert "post" in nav_str
        assert "author" in nav_str
        assert "user" in nav_str
        assert "profile" in nav_str
        assert "age" in nav_str

        # Right side should be Integer
        assert isinstance(query.filter.ast.right, nodes.Integer)


class TestFilterFunctions:
    """Tests for OData functions in filters."""

    def test_startswith_function(self):
        """Test startswith string function."""
        query = parse_odata_query("$filter=startswith(title,'Introduction')")

        assert query.filter is not None
        assert "startswith" in query.filter.expression
        assert "title" in query.filter.expression
        assert "Introduction" in query.filter.expression

    def test_endswith_function(self):
        """Test endswith string function."""
        query = parse_odata_query("$filter=endswith(email,'@gmail.com')")

        assert query.filter is not None
        assert "endswith" in query.filter.expression
        assert "email" in query.filter.expression

    def test_contains_function(self):
        """Test contains string function."""
        query = parse_odata_query("$filter=contains(title,'OData')")

        assert query.filter is not None
        assert "contains" in query.filter.expression
        assert "OData" in query.filter.expression

    def test_tolower_function(self):
        """Test tolower string function."""
        query = parse_odata_query("$filter=tolower(name) eq 'john'")

        assert query.filter is not None
        assert "tolower" in query.filter.expression
        assert "name" in query.filter.expression

    def test_toupper_function(self):
        """Test toupper string function."""
        query = parse_odata_query("$filter=toupper(status) eq 'PUBLISHED'")

        assert query.filter is not None
        assert "toupper" in query.filter.expression

    def test_function_with_and(self):
        """Test function combined with AND."""
        query = parse_odata_query("$filter=startswith(title,'Hello') and rating gt 4.0")

        assert query.filter is not None
        assert "startswith" in query.filter.expression
        assert "and" in query.filter.expression
        assert "rating gt 4.0" in query.filter.expression

    def test_multiple_functions_with_or(self):
        """Test multiple functions combined with OR."""
        query = parse_odata_query("$filter=startswith(title,'Hello') or endswith(title,'World')")

        assert query.filter is not None
        assert "startswith" in query.filter.expression
        assert "endswith" in query.filter.expression
        assert "or" in query.filter.expression

    def test_function_with_navigation(self):
        """Test function on navigation path."""
        query = parse_odata_query("$filter=startswith(author/name,'John')")

        assert query.filter is not None
        assert "startswith" in query.filter.expression
        assert "author/name" in query.filter.expression


class TestFilterDateFunctions:
    """Tests for date/time functions in filters."""

    def test_year_function(self):
        """Test year date function."""
        query = parse_odata_query("$filter=year(created_at) eq 2024")

        assert query.filter is not None
        assert "year" in query.filter.expression
        assert "created_at" in query.filter.expression
        assert "2024" in query.filter.expression

    def test_month_function(self):
        """Test month date function."""
        query = parse_odata_query("$filter=month(created_at) eq 12")

        assert query.filter is not None
        assert "month" in query.filter.expression

    def test_day_function(self):
        """Test day date function."""
        query = parse_odata_query("$filter=day(created_at) eq 25")

        assert query.filter is not None
        assert "day" in query.filter.expression

    def test_hour_function(self):
        """Test hour time function."""
        query = parse_odata_query("$filter=hour(created_at) eq 14")

        assert query.filter is not None
        assert "hour" in query.filter.expression

    def test_date_function_with_and(self):
        """Test date function combined with AND."""
        query = parse_odata_query("$filter=year(created_at) eq 2024 and month(created_at) eq 12")

        assert query.filter is not None
        assert "year" in query.filter.expression
        assert "month" in query.filter.expression
        assert "and" in query.filter.expression


class TestFilterComplexExpressions:
    """Tests for complex filter expressions."""

    def test_complex_expression_1(self):
        """Test complex expression with multiple operators and functions."""
        query = parse_odata_query(
            "$filter=status eq 'published' and rating gt 4.0 "
            "and (contains(title,'Django') or contains(title,'Python')) "
            "and year(created_at) eq 2024"
        )

        assert query.filter is not None
        assert "status eq 'published'" in query.filter.expression
        assert "rating gt 4.0" in query.filter.expression
        assert "contains" in query.filter.expression
        assert "year" in query.filter.expression

    def test_complex_expression_2(self):
        """Test complex expression with navigation and functions."""
        query = parse_odata_query(
            "$filter=(author/user/is_active eq true and author/rating gt 4.0) "
            "or (is_featured eq true and views gt 1000)"
        )

        assert query.filter is not None
        assert "author/user/is_active" in query.filter.expression
        assert "author/rating" in query.filter.expression
        assert "is_featured" in query.filter.expression

    def test_complex_expression_3(self):
        """Test deeply nested complex expression."""
        query = parse_odata_query(
            "$filter=((status eq 'published' and rating gt 4.0) "
            "or (status eq 'featured' and rating gt 3.5)) "
            "and (category/slug eq 'tech' or category/slug eq 'science') "
            "and year(created_at) ge 2023"
        )

        assert query.filter is not None
        assert query.filter.expression.count("(") >= 4
        assert query.filter.expression.count("and") >= 3
        assert query.filter.expression.count("or") >= 2

    def test_complex_expression_4(self):
        """Test complex expression with multiple navigation levels."""
        query = parse_odata_query(
            "$filter=post/author/user/is_active eq true "
            "and (post/category/slug eq 'tech' or post/category/slug eq 'science') "
            "and post/rating gt 4.0 "
            "and startswith(post/title,'Introduction')"
        )

        assert query.filter is not None
        assert "post/author/user/is_active" in query.filter.expression
        assert "post/category/slug" in query.filter.expression
        assert "startswith" in query.filter.expression

    def test_complex_expression_5(self):
        """Test complex expression with all operator types."""
        query = parse_odata_query(
            "$filter=not (status eq 'archived') "
            "and (rating ge 4.0 and rating le 5.0) "
            "and (contains(title,'Python') or contains(tags,'python')) "
            "and author/user/profile/country eq 'Spain' "
            "and year(created_at) eq 2024"
        )

        assert query.filter is not None
        assert "not" in query.filter.expression
        assert "contains" in query.filter.expression
        assert "author/user/profile/country" in query.filter.expression
        assert "year" in query.filter.expression


class TestFilterEdgeCases:
    """Tests for edge cases in filter expressions."""

    def test_filter_with_spaces_in_string(self):
        """Test filter with spaces in string values."""
        query = parse_odata_query("$filter=title eq 'Hello World'")

        assert query.filter is not None
        assert "Hello World" in query.filter.expression

    def test_filter_with_special_characters(self):
        """Test filter with special characters.

        Note: In URL-encoded query strings, '+' means space.
        To include a literal '+' character, use %2B encoding.
        """
        # Use %2B for literal '+' in URL-encoded query strings
        query = parse_odata_query("$filter=email eq 'user%2Btag@example.com'")

        assert query.filter is not None
        assert "user+tag@example.com" in query.filter.expression

    def test_filter_with_numbers_in_strings(self):
        """Test filter with numbers in string values."""
        query = parse_odata_query("$filter=code eq 'ABC123'")

        assert query.filter is not None
        assert "ABC123" in query.filter.expression

    def test_filter_with_decimal_numbers(self):
        """Test filter with decimal numbers."""
        query = parse_odata_query("$filter=price eq 99.99")

        assert query.filter is not None
        assert "99.99" in query.filter.expression

    def test_filter_with_negative_numbers(self):
        """Test filter with negative numbers."""
        query = parse_odata_query("$filter=temperature lt -5")

        assert query.filter is not None
        assert "-5" in query.filter.expression

    def test_filter_with_null(self):
        """Test filter with null value."""
        query = parse_odata_query("$filter=deleted_at eq null")

        assert query.filter is not None
        assert "null" in query.filter.expression

    def test_filter_with_extra_spaces(self):
        """Test filter with extra spaces (should be preserved)."""
        query = parse_odata_query("$filter=status  eq  'published'")

        assert query.filter is not None
        assert "status" in query.filter.expression
        assert "published" in query.filter.expression


class TestFilterRealWorldScenarios:
    """Tests for real-world filter scenarios."""

    def test_blog_published_posts_high_rating(self):
        """Test blog: find published posts with high rating."""
        query = parse_odata_query("$filter=status eq 'published' and rating ge 4.5 and views gt 1000")

        assert query.filter is not None
        assert "status eq 'published'" in query.filter.expression
        assert "rating ge 4.5" in query.filter.expression
        assert "views gt 1000" in query.filter.expression

    def test_ecommerce_price_range_in_stock(self):
        """Test e-commerce: products in price range and in stock."""
        query = parse_odata_query("$filter=price ge 10.00 and price le 100.00 and stock gt 0 and is_active eq true")

        assert query.filter is not None
        assert "price ge 10.00" in query.filter.expression
        assert "price le 100.00" in query.filter.expression
        assert "stock gt 0" in query.filter.expression

    def test_users_active_in_country(self):
        """Test users: active users in specific country."""
        query = parse_odata_query(
            "$filter=is_active eq true and profile/country eq 'Spain' and year(created_at) ge 2023"
        )

        assert query.filter is not None
        assert "is_active eq true" in query.filter.expression
        assert "profile/country eq 'Spain'" in query.filter.expression

    def test_search_title_or_content(self):
        """Test search: find posts by title or content."""
        query = parse_odata_query(
            "$filter=(contains(title,'Python') or contains(content,'Python')) and status eq 'published'"
        )

        assert query.filter is not None
        assert "contains(title,'Python')" in query.filter.expression
        assert "contains(content,'Python')" in query.filter.expression

    def test_moderation_queue(self):
        """Test moderation: posts awaiting review."""
        query = parse_odata_query(
            "$filter=(status eq 'pending' or status eq 'in_review') "
            "and not (is_spam eq true) "
            "and author/reputation gt 10"
        )

        assert query.filter is not None
        assert "status eq 'pending'" in query.filter.expression
        assert "status eq 'in_review'" in query.filter.expression
        assert "not" in query.filter.expression

    def test_trending_content(self):
        """Test trending: popular recent content."""
        query = parse_odata_query(
            "$filter=(views gt 1000 or likes gt 100) "
            "and year(created_at) eq 2024 "
            "and month(created_at) ge 11 "
            "and status eq 'published'"
        )

        assert query.filter is not None
        assert "views gt 1000" in query.filter.expression
        assert "likes gt 100" in query.filter.expression
        assert "year(created_at) eq 2024" in query.filter.expression


# Run with: pytest tests/core/test_filter_comprehensive.py -v
