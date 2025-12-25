"""
Tests for QueryBuilder integration with fluent filter API.
"""

import pytest

from fc_selector.core.ast import nodes as ast
from fc_selector.core.filters import Field
from fc_selector.core.intent import QueryIntent
from fc_selector.core.query_builder import QueryBuilder


class TestQueryBuilderBuild:
    """Tests for QueryBuilder.build() method."""

    def test_build_empty(self):
        """Building empty query returns empty QueryIntent."""
        builder = QueryBuilder()
        intent = builder.build()

        assert isinstance(intent, QueryIntent)
        assert intent.is_empty()

    def test_build_with_filter(self):
        """Building query with filter."""
        builder = QueryBuilder().filter("status eq 'active'")
        intent = builder.build()

        assert intent.filter is not None
        assert intent.filter.expression == "status eq 'active'"

    def test_build_with_select(self):
        """Building query with select."""
        builder = QueryBuilder().select("id", "name", "email")
        intent = builder.build()

        assert intent.select is not None
        assert intent.select.fields == ["id", "name", "email"]

    def test_build_with_expand(self):
        """Building query with expand."""
        builder = QueryBuilder().expand("author", "category")
        intent = builder.build()

        assert intent.expand is not None
        assert set(intent.expand.get_relation_names()) == {"author", "category"}

    def test_build_with_orderby(self):
        """Building query with orderby."""
        builder = QueryBuilder().orderby("created_at desc", "name asc")
        intent = builder.build()

        assert intent.orderby is not None
        assert len(intent.orderby.fields) == 2
        assert intent.orderby.fields[0].field == "created_at"
        assert intent.orderby.fields[0].direction == "desc"
        assert intent.orderby.fields[1].field == "name"
        assert intent.orderby.fields[1].direction == "asc"

    def test_build_with_pagination(self):
        """Building query with pagination."""
        builder = QueryBuilder().top(10).skip(20).count(True)
        intent = builder.build()

        assert intent.pagination is not None
        assert intent.pagination.limit == 10
        assert intent.pagination.offset == 20
        assert intent.pagination.include_count is True

    def test_build_full_query(self):
        """Building full query with all options."""
        builder = (
            QueryBuilder()
            .filter("status eq 'active'")
            .select("id", "name")
            .expand("author")
            .orderby("created_at desc")
            .top(10)
            .skip(0)
        )
        intent = builder.build()

        assert intent.filter.expression == "status eq 'active'"
        assert intent.select.fields == ["id", "name"]
        assert "author" in intent.expand.relations
        assert intent.orderby.fields[0].field == "created_at"
        assert intent.pagination.limit == 10

    def test_build_from_query_string(self):
        """Building from parsed query string."""
        builder = QueryBuilder("$filter=id eq 1&$select=name&$top=5")
        intent = builder.build()

        assert intent.filter.expression == "id eq 1"
        assert intent.select.fields == ["name"]
        assert intent.pagination.limit == 5


class TestQueryBuilderWhere:
    """Tests for QueryBuilder.where() method."""

    def test_where_simple(self):
        """where() with simple expression."""
        builder = QueryBuilder().where(Field("name").eq("John"))
        intent = builder.build()

        assert intent.filter is not None
        assert intent.filter.ast is not None
        # Expression is None because we used AST directly
        assert intent.filter.expression is None

    def test_where_replaces_filter(self):
        """where() replaces existing string filter."""
        builder = QueryBuilder().filter("old eq 'value'").where(Field("new").eq("value"))
        intent = builder.build()

        # AST should be from where(), string filter cleared
        assert intent.filter.ast is not None
        assert intent.filter.expression is None

    def test_where_with_composition(self):
        """where() with composed expression."""
        builder = QueryBuilder().where(Field("status").eq("active") & Field("age").gt(18))
        intent = builder.build()

        node = intent.filter.ast
        assert isinstance(node, ast.BoolOp)
        assert isinstance(node.op, ast.And)

    def test_where_type_error(self):
        """where() raises TypeError for non-Expression."""
        with pytest.raises(TypeError) as exc:
            QueryBuilder().where("not an expression")

        assert "expects an Expression" in str(exc.value)


class TestQueryBuilderAndWhere:
    """Tests for QueryBuilder.and_where() method."""

    def test_and_where_with_existing_where(self):
        """and_where() combines with existing where()."""
        builder = QueryBuilder().where(Field("status").eq("active")).and_where(Field("age").gt(18))
        intent = builder.build()

        node = intent.filter.ast
        assert isinstance(node, ast.BoolOp)
        assert isinstance(node.op, ast.And)

    def test_and_where_with_string_filter(self):
        """and_where() combines with existing string filter."""
        builder = QueryBuilder("$filter=status eq 'active'").and_where(Field("age").gt(18))
        intent = builder.build()

        # Should have combined AST
        node = intent.filter.ast
        assert isinstance(node, ast.BoolOp)
        assert isinstance(node.op, ast.And)
        # String filter should be cleared
        assert intent.filter.expression is None

    def test_and_where_on_empty(self):
        """and_where() on empty builder just sets the filter."""
        builder = QueryBuilder().and_where(Field("name").eq("John"))
        intent = builder.build()

        node = intent.filter.ast
        assert isinstance(node, ast.Compare)


class TestQueryBuilderOrWhere:
    """Tests for QueryBuilder.or_where() method."""

    def test_or_where_with_existing_where(self):
        """or_where() combines with existing where()."""
        builder = QueryBuilder().where(Field("role").eq("admin")).or_where(Field("role").eq("superuser"))
        intent = builder.build()

        node = intent.filter.ast
        assert isinstance(node, ast.BoolOp)
        assert isinstance(node.op, ast.Or)

    def test_or_where_with_string_filter(self):
        """or_where() combines with existing string filter."""
        builder = QueryBuilder("$filter=role eq 'admin'").or_where(Field("role").eq("superuser"))
        intent = builder.build()

        node = intent.filter.ast
        assert isinstance(node, ast.BoolOp)
        assert isinstance(node.op, ast.Or)


class TestQueryBuilderGetFilterAst:
    """Tests for QueryBuilder.get_filter_ast() method."""

    def test_get_filter_ast_from_where(self):
        """get_filter_ast() returns AST from where()."""
        builder = QueryBuilder().where(Field("x").eq(1))
        ast_node = builder.get_filter_ast()

        assert ast_node is not None
        assert isinstance(ast_node, ast.Compare)

    def test_get_filter_ast_from_string(self):
        """get_filter_ast() parses string filter."""
        builder = QueryBuilder().filter("x eq 1")
        ast_node = builder.get_filter_ast()

        assert ast_node is not None
        assert isinstance(ast_node, ast.Compare)

    def test_get_filter_ast_empty(self):
        """get_filter_ast() returns None for empty filter."""
        builder = QueryBuilder()
        ast_node = builder.get_filter_ast()

        assert ast_node is None


class TestQueryBuilderMixedApi:
    """Tests for mixing string and fluent APIs."""

    def test_string_then_fluent(self):
        """Using string filter then fluent where."""
        builder = (
            QueryBuilder("$filter=base eq 'value'&$select=id")
            .and_where(Field("extra").gt(5))
            .select("id", "name")  # Overrides select
            .top(10)
        )
        intent = builder.build()

        # Filter should be combined
        assert intent.filter.ast is not None
        # Select should be overridden
        assert intent.select.fields == ["id", "name"]
        # Pagination from top()
        assert intent.pagination.limit == 10

    def test_fluent_filter_with_string_options(self):
        """Using fluent filter with string-style options."""
        builder = (
            QueryBuilder()
            .where(Field("active").eq(True))
            .select("id,name,email")  # String style
            .expand("author,posts")  # String style
            .orderby("created_at desc")
        )
        intent = builder.build()

        assert intent.filter.ast is not None
        assert intent.select.fields == ["id", "name", "email"]
        assert set(intent.expand.get_relation_names()) == {"author", "posts"}
