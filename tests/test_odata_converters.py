"""
Tests for OData converters (odata_query_to_intent, intent_to_odata_query).

Covers fc_selector/protocols/odata/converters.py
"""

from fc_selector.core.intent import (
    ExpandIntent,
    FilterIntent,
    OrderField,
    OrderIntent,
    PaginationIntent,
    QueryIntent,
    SelectIntent,
)
from fc_selector.protocols.odata.converters import (
    _convert_expand_to_intent,
    _convert_expand_to_odata,
    intent_to_odata_query,
    odata_query_to_intent,
)
from fc_selector.protocols.odata.parsers.query import parse_odata_query


class TestODataQueryToIntent:
    """Tests for odata_query_to_intent converter."""

    def test_empty_query(self):
        """Empty query produces empty intent."""
        odata_query = parse_odata_query("")
        intent = odata_query_to_intent(odata_query)

        assert intent.filter is None
        assert intent.select is None
        assert intent.expand is None
        assert intent.orderby is None
        assert intent.pagination is None

    def test_filter_conversion(self):
        """Filter is converted to FilterIntent."""
        odata_query = parse_odata_query("$filter=status eq 'active'")
        intent = odata_query_to_intent(odata_query)

        assert intent.filter is not None
        assert intent.filter.expression == "status eq 'active'"
        assert intent.filter.ast is not None

    def test_select_conversion(self):
        """Select is converted to SelectIntent."""
        odata_query = parse_odata_query("$select=id,name,email")
        intent = odata_query_to_intent(odata_query)

        assert intent.select is not None
        assert intent.select.fields == ["id", "name", "email"]

    def test_select_empty_fields(self):
        """Empty select produces empty list."""
        odata_query = parse_odata_query("$top=10")  # No select
        intent = odata_query_to_intent(odata_query)

        # select is None when not provided
        assert intent.select is None

    def test_expand_simple(self):
        """Simple expand is converted."""
        odata_query = parse_odata_query("$expand=author")
        intent = odata_query_to_intent(odata_query)

        assert intent.expand is not None
        assert "author" in intent.expand.relations

    def test_expand_multiple(self):
        """Multiple expands are converted."""
        odata_query = parse_odata_query("$expand=author,categories")
        intent = odata_query_to_intent(odata_query)

        assert intent.expand is not None
        assert "author" in intent.expand.relations
        assert "categories" in intent.expand.relations

    def test_orderby_conversion(self):
        """Orderby is converted to OrderIntent."""
        odata_query = parse_odata_query("$orderby=created_at desc,name asc")
        intent = odata_query_to_intent(odata_query)

        assert intent.orderby is not None
        assert len(intent.orderby.fields) == 2
        assert intent.orderby.fields[0].field == "created_at"
        assert intent.orderby.fields[0].direction == "desc"
        assert intent.orderby.fields[1].field == "name"
        assert intent.orderby.fields[1].direction == "asc"

    def test_pagination_top_only(self):
        """Top creates pagination with limit."""
        odata_query = parse_odata_query("$top=10")
        intent = odata_query_to_intent(odata_query)

        assert intent.pagination is not None
        assert intent.pagination.limit == 10
        assert intent.pagination.offset is None

    def test_pagination_skip_only(self):
        """Skip creates pagination with offset."""
        odata_query = parse_odata_query("$skip=20")
        intent = odata_query_to_intent(odata_query)

        assert intent.pagination is not None
        assert intent.pagination.offset == 20
        assert intent.pagination.limit is None

    def test_pagination_top_and_skip(self):
        """Top and skip together."""
        odata_query = parse_odata_query("$top=10&$skip=20")
        intent = odata_query_to_intent(odata_query)

        assert intent.pagination is not None
        assert intent.pagination.limit == 10
        assert intent.pagination.offset == 20

    def test_pagination_with_count(self):
        """Count flag is converted."""
        odata_query = parse_odata_query("$count=true")
        intent = odata_query_to_intent(odata_query)

        assert intent.pagination is not None
        assert intent.pagination.include_count is True

    def test_full_query_conversion(self):
        """Full query with all parameters."""
        query = "$filter=active eq true&$select=id,name&$expand=author&$orderby=name desc&$top=10&$skip=5"
        odata_query = parse_odata_query(query)
        intent = odata_query_to_intent(odata_query)

        assert intent.filter is not None
        assert intent.select is not None
        assert intent.expand is not None
        assert intent.orderby is not None
        assert intent.pagination is not None
        assert intent.pagination.limit == 10
        assert intent.pagination.offset == 5


class TestConvertExpandToIntent:
    """Tests for _convert_expand_to_intent helper."""

    def test_simple_expand(self):
        """Simple relation without nested options."""
        nested_options = {"author": {}}
        expand_intent = _convert_expand_to_intent(nested_options)

        assert "author" in expand_intent.relations
        nested = expand_intent.relations["author"]
        assert nested.filter is None
        assert nested.select is None

    def test_expand_with_filter(self):
        """Expand with nested $filter."""
        nested_options = {"posts": {"$filter": "status eq 'published'"}}
        expand_intent = _convert_expand_to_intent(nested_options)

        nested = expand_intent.relations["posts"]
        assert nested.filter is not None
        assert nested.filter.expression == "status eq 'published'"

    def test_expand_with_select_string(self):
        """Expand with nested $select as string."""
        nested_options = {"author": {"$select": "id,name,email"}}
        expand_intent = _convert_expand_to_intent(nested_options)

        nested = expand_intent.relations["author"]
        assert nested.select is not None
        assert nested.select.fields == ["id", "name", "email"]

    def test_expand_with_select_list(self):
        """Expand with nested $select as list."""
        nested_options = {"author": {"$select": ["id", "name"]}}
        expand_intent = _convert_expand_to_intent(nested_options)

        nested = expand_intent.relations["author"]
        assert nested.select is not None
        assert nested.select.fields == ["id", "name"]

    def test_expand_with_orderby(self):
        """Expand with nested $orderby."""
        nested_options = {"posts": {"$orderby": "created_at desc,title asc"}}
        expand_intent = _convert_expand_to_intent(nested_options)

        nested = expand_intent.relations["posts"]
        assert nested.orderby is not None
        assert len(nested.orderby.fields) == 2
        assert nested.orderby.fields[0].field == "created_at"
        assert nested.orderby.fields[0].direction == "desc"

    def test_expand_with_orderby_default_direction(self):
        """Expand orderby defaults to asc."""
        nested_options = {"posts": {"$orderby": "name"}}
        expand_intent = _convert_expand_to_intent(nested_options)

        nested = expand_intent.relations["posts"]
        assert nested.orderby.fields[0].direction == "asc"

    def test_expand_with_top(self):
        """Expand with nested $top."""
        nested_options = {"posts": {"$top": "5"}}
        expand_intent = _convert_expand_to_intent(nested_options)

        nested = expand_intent.relations["posts"]
        assert nested.pagination is not None
        assert nested.pagination.limit == 5

    def test_expand_with_top_and_skip(self):
        """Expand with nested $top and $skip."""
        nested_options = {"posts": {"$top": "10", "$skip": "5"}}
        expand_intent = _convert_expand_to_intent(nested_options)

        nested = expand_intent.relations["posts"]
        assert nested.pagination.limit == 10
        assert nested.pagination.offset == 5

    def test_expand_with_nested_expand_dict(self):
        """Expand with recursive nested $expand as dict."""
        nested_options = {"author": {"$expand": {"profile": {}}}}
        expand_intent = _convert_expand_to_intent(nested_options)

        nested = expand_intent.relations["author"]
        assert nested.expand is not None
        assert "profile" in nested.expand.relations

    def test_expand_with_nested_expand_string(self):
        """Expand with nested $expand as comma-separated string."""
        nested_options = {"author": {"$expand": "profile,settings"}}
        expand_intent = _convert_expand_to_intent(nested_options)

        nested = expand_intent.relations["author"]
        assert nested.expand is not None
        assert "profile" in nested.expand.relations
        assert "settings" in nested.expand.relations


class TestIntentToODataQuery:
    """Tests for intent_to_odata_query converter."""

    def test_empty_intent(self):
        """Empty intent produces empty query."""
        intent = QueryIntent()
        odata_query = intent_to_odata_query(intent)

        assert odata_query.filter is None
        assert odata_query.select is None
        assert odata_query.expand is None
        assert odata_query.orderby is None
        assert odata_query.top is None
        assert odata_query.skip is None

    def test_filter_intent_conversion(self):
        """FilterIntent is converted."""
        # Parse a filter to get the AST
        parsed = parse_odata_query("$filter=status eq 'active'")
        intent = QueryIntent(filter=FilterIntent(expression="status eq 'active'", ast=parsed.filter.ast))
        odata_query = intent_to_odata_query(intent)

        assert odata_query.filter is not None
        assert odata_query.filter.value == "status eq 'active'"

    def test_select_intent_conversion(self):
        """SelectIntent is converted."""
        intent = QueryIntent(select=SelectIntent(fields=["id", "name", "email"]))
        odata_query = intent_to_odata_query(intent)

        assert odata_query.select is not None
        assert odata_query.select.value == "id,name,email"
        assert odata_query.select.fields == ["id", "name", "email"]

    def test_expand_intent_conversion(self):
        """ExpandIntent is converted."""
        intent = QueryIntent(expand=ExpandIntent(relations={"author": QueryIntent(), "category": QueryIntent()}))
        odata_query = intent_to_odata_query(intent)

        assert odata_query.expand is not None
        assert "author" in odata_query.expand.value
        assert "category" in odata_query.expand.value

    def test_orderby_intent_conversion(self):
        """OrderIntent is converted."""
        intent = QueryIntent(
            orderby=OrderIntent(
                fields=[OrderField(field="name", direction="asc"), OrderField(field="date", direction="desc")]
            )
        )
        odata_query = intent_to_odata_query(intent)

        assert odata_query.orderby is not None
        # asc is default, so "name" without direction, "date desc"
        assert "name" in odata_query.orderby.value
        assert "date desc" in odata_query.orderby.value

    def test_pagination_intent_conversion(self):
        """PaginationIntent is converted."""
        intent = QueryIntent(pagination=PaginationIntent(limit=10, offset=20, include_count=True))
        odata_query = intent_to_odata_query(intent)

        assert odata_query.top is not None
        assert odata_query.top.value == "10"
        assert odata_query.skip is not None
        assert odata_query.skip.value == "20"
        assert odata_query.count is True

    def test_pagination_limit_only(self):
        """Pagination with only limit."""
        intent = QueryIntent(pagination=PaginationIntent(limit=50))
        odata_query = intent_to_odata_query(intent)

        assert odata_query.top.value == "50"
        assert odata_query.skip is None

    def test_pagination_offset_only(self):
        """Pagination with only offset."""
        intent = QueryIntent(pagination=PaginationIntent(offset=100))
        odata_query = intent_to_odata_query(intent)

        assert odata_query.top is None
        assert odata_query.skip.value == "100"


class TestConvertExpandToOData:
    """Tests for _convert_expand_to_odata helper."""

    def test_simple_expand(self):
        """Simple expand without nested options."""
        expand = ExpandIntent(relations={"author": QueryIntent()})
        result = _convert_expand_to_odata(expand)

        assert "author" in result
        assert result["author"] == {}

    def test_expand_with_filter(self):
        """Expand with filter."""
        # Need to include AST for has_filter() to return True
        parsed = parse_odata_query("$filter=status eq 'published'")
        expand = ExpandIntent(
            relations={
                "posts": QueryIntent(filter=FilterIntent(expression="status eq 'published'", ast=parsed.filter.ast))
            }
        )
        result = _convert_expand_to_odata(expand)

        assert result["posts"]["$filter"] == "status eq 'published'"

    def test_expand_with_select(self):
        """Expand with select."""
        expand = ExpandIntent(relations={"author": QueryIntent(select=SelectIntent(fields=["id", "name"]))})
        result = _convert_expand_to_odata(expand)

        assert result["author"]["$select"] == "id,name"

    def test_expand_with_orderby(self):
        """Expand with orderby."""
        expand = ExpandIntent(
            relations={
                "posts": QueryIntent(
                    orderby=OrderIntent(
                        fields=[OrderField(field="date", direction="desc"), OrderField(field="title", direction="asc")]
                    )
                )
            }
        )
        result = _convert_expand_to_odata(expand)

        assert "date desc" in result["posts"]["$orderby"]
        assert "title" in result["posts"]["$orderby"]

    def test_expand_with_pagination(self):
        """Expand with pagination."""
        expand = ExpandIntent(relations={"posts": QueryIntent(pagination=PaginationIntent(limit=5, offset=10))})
        result = _convert_expand_to_odata(expand)

        assert result["posts"]["$top"] == "5"
        assert result["posts"]["$skip"] == "10"

    def test_expand_with_nested_expand(self):
        """Expand with recursive nested expand."""
        expand = ExpandIntent(
            relations={"author": QueryIntent(expand=ExpandIntent(relations={"profile": QueryIntent()}))}
        )
        result = _convert_expand_to_odata(expand)

        assert "$expand" in result["author"]
        assert "profile" in result["author"]["$expand"]


class TestRoundTrip:
    """Tests for round-trip conversion (odata -> intent -> odata)."""

    def test_roundtrip_filter(self):
        """Filter survives round-trip."""
        original = parse_odata_query("$filter=name eq 'test'")
        intent = odata_query_to_intent(original)
        result = intent_to_odata_query(intent)

        assert result.filter.value == original.filter.value

    def test_roundtrip_select(self):
        """Select survives round-trip."""
        original = parse_odata_query("$select=id,name,email")
        intent = odata_query_to_intent(original)
        result = intent_to_odata_query(intent)

        assert set(result.select.fields) == set(original.select.fields)

    def test_roundtrip_pagination(self):
        """Pagination survives round-trip."""
        original = parse_odata_query("$top=10&$skip=20")
        intent = odata_query_to_intent(original)
        result = intent_to_odata_query(intent)

        assert result.top.value == original.top.value
        assert result.skip.value == original.skip.value
