"""
Tests for parsing OData query parameters into a QueryIntent.

Covers fc_selector/protocols/odata/parsers/query/parser.py
"""

from fc_selector.protocols.odata.parsers.query import parse_odata_query
from fc_selector.protocols.odata.parsers.query.parser import _expand_intent


class TestParseODataQuery:
    """Tests for parse_odata_query."""

    def test_empty_query(self):
        """Empty query produces empty intent."""
        intent = parse_odata_query("")

        assert intent.filter is None
        assert intent.select is None
        assert intent.expand is None
        assert intent.orderby is None
        assert intent.pagination is None

    def test_filter_conversion(self):
        """Filter is converted to FilterIntent."""
        intent = parse_odata_query("$filter=status eq 'active'")

        assert intent.filter is not None
        assert intent.filter.expression == "status eq 'active'"
        assert intent.filter.ast is not None

    def test_select_conversion(self):
        """Select is converted to SelectIntent."""
        intent = parse_odata_query("$select=id,name,email")

        assert intent.select is not None
        assert intent.select.fields == ["id", "name", "email"]

    def test_select_empty_fields(self):
        """Empty select produces empty list."""
        intent = parse_odata_query("$top=10")  # No select

        # select is None when not provided
        assert intent.select is None

    def test_expand_simple(self):
        """Simple expand is converted."""
        intent = parse_odata_query("$expand=author")

        assert intent.expand is not None
        assert "author" in intent.expand.relations

    def test_expand_multiple(self):
        """Multiple expands are converted."""
        intent = parse_odata_query("$expand=author,categories")

        assert intent.expand is not None
        assert "author" in intent.expand.relations
        assert "categories" in intent.expand.relations

    def test_orderby_conversion(self):
        """Orderby is converted to OrderIntent."""
        intent = parse_odata_query("$orderby=created_at desc,name asc")

        assert intent.orderby is not None
        assert len(intent.orderby.fields) == 2
        assert intent.orderby.fields[0].field == "created_at"
        assert intent.orderby.fields[0].direction == "desc"
        assert intent.orderby.fields[1].field == "name"
        assert intent.orderby.fields[1].direction == "asc"

    def test_pagination_top_only(self):
        """Top creates pagination with limit."""
        intent = parse_odata_query("$top=10")

        assert intent.pagination is not None
        assert intent.pagination.limit == 10
        assert intent.pagination.offset is None

    def test_pagination_skip_only(self):
        """Skip creates pagination with offset."""
        intent = parse_odata_query("$skip=20")

        assert intent.pagination is not None
        assert intent.pagination.offset == 20
        assert intent.pagination.limit is None

    def test_pagination_top_and_skip(self):
        """Top and skip together."""
        intent = parse_odata_query("$top=10&$skip=20")

        assert intent.pagination is not None
        assert intent.pagination.limit == 10
        assert intent.pagination.offset == 20

    def test_pagination_with_count(self):
        """Count flag is converted."""
        intent = parse_odata_query("$count=true")

        assert intent.pagination is not None
        assert intent.pagination.include_count is True

    def test_full_query_conversion(self):
        """Full query with all parameters."""
        query = "$filter=active eq true&$select=id,name&$expand=author&$orderby=name desc&$top=10&$skip=5"
        intent = parse_odata_query(query)

        assert intent.filter is not None
        assert intent.select is not None
        assert intent.expand is not None
        assert intent.orderby is not None
        assert intent.pagination is not None
        assert intent.pagination.limit == 10
        assert intent.pagination.offset == 5


class TestExpandIntent:
    """Tests for the nested $expand -> QueryIntent conversion."""

    def test_simple_expand(self):
        """Simple relation without nested options."""
        nested_options = {"author": {}}
        expand_intent = _expand_intent(nested_options)

        assert "author" in expand_intent.relations
        nested = expand_intent.relations["author"]
        assert nested.filter is None
        assert nested.select is None

    def test_expand_with_filter(self):
        """Expand with nested $filter."""
        nested_options = {"posts": {"$filter": "status eq 'published'"}}
        expand_intent = _expand_intent(nested_options)

        nested = expand_intent.relations["posts"]
        assert nested.filter is not None
        assert nested.filter.expression == "status eq 'published'"

    def test_expand_with_select_string(self):
        """Expand with nested $select as string."""
        nested_options = {"author": {"$select": "id,name,email"}}
        expand_intent = _expand_intent(nested_options)

        nested = expand_intent.relations["author"]
        assert nested.select is not None
        assert nested.select.fields == ["id", "name", "email"]

    def test_expand_with_select_list(self):
        """Expand with nested $select as list."""
        nested_options = {"author": {"$select": ["id", "name"]}}
        expand_intent = _expand_intent(nested_options)

        nested = expand_intent.relations["author"]
        assert nested.select is not None
        assert nested.select.fields == ["id", "name"]

    def test_expand_with_orderby(self):
        """Expand with nested $orderby."""
        nested_options = {"posts": {"$orderby": "created_at desc,title asc"}}
        expand_intent = _expand_intent(nested_options)

        nested = expand_intent.relations["posts"]
        assert nested.orderby is not None
        assert len(nested.orderby.fields) == 2
        assert nested.orderby.fields[0].field == "created_at"
        assert nested.orderby.fields[0].direction == "desc"

    def test_expand_with_orderby_default_direction(self):
        """Expand orderby defaults to asc."""
        nested_options = {"posts": {"$orderby": "name"}}
        expand_intent = _expand_intent(nested_options)

        nested = expand_intent.relations["posts"]
        assert nested.orderby.fields[0].direction == "asc"

    def test_expand_with_top(self):
        """Expand with nested $top."""
        nested_options = {"posts": {"$top": "5"}}
        expand_intent = _expand_intent(nested_options)

        nested = expand_intent.relations["posts"]
        assert nested.pagination is not None
        assert nested.pagination.limit == 5

    def test_expand_with_top_and_skip(self):
        """Expand with nested $top and $skip."""
        nested_options = {"posts": {"$top": "10", "$skip": "5"}}
        expand_intent = _expand_intent(nested_options)

        nested = expand_intent.relations["posts"]
        assert nested.pagination.limit == 10
        assert nested.pagination.offset == 5

    def test_expand_with_nested_expand_dict(self):
        """Expand with recursive nested $expand as dict."""
        nested_options = {"author": {"$expand": {"profile": {}}}}
        expand_intent = _expand_intent(nested_options)

        nested = expand_intent.relations["author"]
        assert nested.expand is not None
        assert "profile" in nested.expand.relations

    def test_expand_with_nested_expand_string(self):
        """Expand with nested $expand as comma-separated string."""
        nested_options = {"author": {"$expand": "profile,settings"}}
        expand_intent = _expand_intent(nested_options)

        nested = expand_intent.relations["author"]
        assert nested.expand is not None
        assert "profile" in nested.expand.relations
        assert "settings" in nested.expand.relations
