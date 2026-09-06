"""
Tests for QueryIntent and related models.
"""

from fc_selector.core.ast.nodes import Compare, Eq, Identifier, String
from fc_selector.core.intent import (
    ExpandIntent,
    FilterIntent,
    OrderField,
    OrderIntent,
    PaginationIntent,
    QueryIntent,
    SelectIntent,
)


class TestFilterIntent:
    """Tests for FilterIntent model."""

    def test_empty_filter(self):
        """FilterIntent with no expression or AST is not active."""
        intent = FilterIntent()
        assert not intent.has_filter()
        assert intent.ast is None

    def test_filter_with_expression(self):
        """FilterIntent with expression only is technically not active for execution."""
        # In the new architecture, expression is metadata.
        # has_filter() checks for AST because that's what's executable.
        intent = FilterIntent(expression="name eq 'John'")
        assert not intent.has_filter()  # Should be False if no AST
        assert intent.expression == "name eq 'John'"

    def test_filter_with_ast(self):
        """FilterIntent with AST is active."""
        ast_node = Compare(
            comparator=Eq(),
            left=Identifier(name="name"),
            right=String(val="'John'"),
        )
        intent = FilterIntent(ast=ast_node)
        assert intent.has_filter()
        assert intent.ast == ast_node


class TestSelectIntent:
    """Tests for SelectIntent model."""

    def test_empty_select(self):
        """SelectIntent with no fields is not active."""
        intent = SelectIntent()
        assert not intent.has_fields()

    def test_select_with_fields(self):
        """SelectIntent with fields is active."""
        intent = SelectIntent(fields=["id", "name", "email"])
        assert intent.has_fields()
        assert intent.fields == ["id", "name", "email"]


class TestExpandIntent:
    """Tests for ExpandIntent model."""

    def test_empty_expand(self):
        """ExpandIntent with no relations is not active."""
        intent = ExpandIntent()
        assert not intent.has_relations()
        assert list(intent.relations) == []

    def test_expand_with_relations(self):
        """ExpandIntent with relations is active."""
        intent = ExpandIntent(
            relations={
                "author": QueryIntent(),
                "category": QueryIntent(),
            }
        )
        assert intent.has_relations()
        assert set(intent.relations) == {"author", "category"}

    def test_nested_expand(self):
        """ExpandIntent supports nested QueryIntents."""
        nested = QueryIntent(
            select=SelectIntent(fields=["name"]),
            pagination=PaginationIntent(limit=5),
        )
        intent = ExpandIntent(relations={"author": nested})
        assert intent.relations["author"].select.fields == ["name"]
        assert intent.relations["author"].pagination.limit == 5


class TestOrderIntent:
    """Tests for OrderIntent model."""

    def test_empty_order(self):
        """OrderIntent with no fields is not active."""
        intent = OrderIntent()
        assert not intent.has_ordering()

    def test_order_with_fields(self):
        """OrderIntent with fields is active."""
        intent = OrderIntent(
            fields=[
                OrderField(field="created_at", direction="desc"),
                OrderField(field="name", direction="asc"),
            ]
        )
        assert intent.has_ordering()
        assert len(intent.fields) == 2

    def test_from_tuples(self):
        """OrderIntent.from_tuples creates OrderIntent from tuples."""
        intent = OrderIntent.from_tuples(
            [
                ("created_at", "desc"),
                ("name", "asc"),
            ]
        )
        assert intent.fields[0].field == "created_at"
        assert intent.fields[0].direction == "desc"
        assert intent.fields[1].field == "name"
        assert intent.fields[1].direction == "asc"


class TestPaginationIntent:
    """Tests for PaginationIntent model."""

    def test_empty_pagination(self):
        """PaginationIntent with no values is not active."""
        intent = PaginationIntent()
        assert not intent.has_pagination()

    def test_pagination_with_limit(self):
        """PaginationIntent with limit is active."""
        intent = PaginationIntent(limit=10)
        assert intent.has_pagination()
        assert intent.limit == 10
        assert intent.offset is None

    def test_pagination_with_offset(self):
        """PaginationIntent with offset is active."""
        intent = PaginationIntent(offset=20)
        assert intent.has_pagination()
        assert intent.offset == 20

    def test_pagination_full(self):
        """PaginationIntent with all values."""
        intent = PaginationIntent(limit=10, offset=20, include_count=True)
        assert intent.has_pagination()
        assert intent.limit == 10
        assert intent.offset == 20
        assert intent.include_count is True


class TestQueryIntent:
    """Tests for QueryIntent model."""

    def test_empty_intent(self):
        """A default QueryIntent carries no query options."""
        intent = QueryIntent()
        assert (intent.filter, intent.select, intent.expand, intent.orderby, intent.pagination) == (
            None,
            None,
            None,
            None,
            None,
        )

    def test_intent_with_filter(self):
        """QueryIntent with filter is not empty (if filter is active)."""
        ast = Compare(Eq(), Identifier("status"), String("'active'"))

        intent = QueryIntent(filter=FilterIntent(expression="status eq 'active'", ast=ast))
        assert intent.filter.has_filter()

    def test_intent_with_all_options(self):
        """QueryIntent with all options."""
        intent = QueryIntent(
            filter=FilterIntent(expression="status eq 'active'"),
            select=SelectIntent(fields=["id", "name"]),
            expand=ExpandIntent(relations={"author": QueryIntent()}),
            orderby=OrderIntent.from_tuples([("created_at", "desc")]),
            pagination=PaginationIntent(limit=10),
        )
        # Even if the filter is inactive (no AST), the other options are set
        assert not intent.filter.has_filter()
        assert intent.select.fields == ["id", "name"]
        assert "author" in intent.expand.relations
        assert intent.orderby.fields[0].field == "created_at"
        assert intent.pagination.limit == 10
