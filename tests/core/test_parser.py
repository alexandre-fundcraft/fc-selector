"""
Exhaustive tests for the OData query parser (core/query/parser.py).

This test suite ensures the parser correctly handles all OData query parameters
and combinations WITHOUT any Django dependencies.
"""

import pytest

from fc_selector.core.intent import QueryIntent
from fc_selector.protocols.odata.parsers.expand import parse_expand
from fc_selector.protocols.odata.parsers.filter.exceptions import ODataSyntaxError
from fc_selector.protocols.odata.parsers.query import parse_odata_query, parse_query_params


def expand_options(query_params):
    """The nested $expand options for a query, exactly as parse_expand returns them."""
    if isinstance(query_params, str):
        query_params = parse_query_params(query_params)
    return parse_expand((query_params or {}).get("$expand", "") or "")


class TestSelectParsing:
    """Tests for $select parameter parsing."""

    def test_select_single_field(self):
        """Test parsing $select with single field."""
        result = parse_odata_query("$select=id")

        assert result.select is not None
        assert ",".join(result.select.fields) == "id"
        assert result.select.fields == ["id"]

    def test_select_multiple_fields(self):
        """Test parsing $select with multiple fields."""
        result = parse_odata_query("$select=id,name,email")

        assert result.select is not None
        assert ",".join(result.select.fields) == "id,name,email"
        assert set(result.select.fields) == {"id", "name", "email"}

    def test_select_with_spaces(self):
        """Test parsing $select with spaces around commas."""
        result = parse_odata_query("$select=id, name , email")

        assert result.select is not None
        assert set(result.select.fields) == {"id", "name", "email"}

    def test_no_select(self):
        """Test query without $select."""
        result = parse_odata_query("$filter=status eq 'published'")

        assert result.select is None


class TestExpandParsing:
    """Tests for $expand parameter parsing."""

    def test_expand_single_field_simple(self):
        """Test parsing $expand with single field without options."""
        result = parse_odata_query("$expand=author")
        result_expand = expand_options("$expand=author")

        assert result.expand is not None
        assert "author" in result_expand
        assert result_expand["author"] == {}

    def test_expand_multiple_fields_simple(self):
        """Test parsing $expand with multiple fields without options."""
        result = parse_odata_query("$expand=author,categories")
        result_expand = expand_options("$expand=author,categories")

        assert result.expand is not None
        assert "author" in result_expand
        assert "categories" in result_expand
        assert result_expand["author"] == {}
        assert result_expand["categories"] == {}

    def test_expand_with_select_option(self):
        """Test parsing $expand with nested $select."""
        result = parse_odata_query("$expand=author($select=id,name)")
        result_expand = expand_options("$expand=author($select=id,name)")

        assert result.expand is not None
        assert "author" in result_expand
        assert "$select" in result_expand["author"]
        assert result_expand["author"]["$select"] == "id,name"

    def test_expand_with_nested_expand(self):
        """Test parsing $expand with nested $expand."""
        result = parse_odata_query("$expand=author($expand=user)")
        result_expand = expand_options("$expand=author($expand=user)")

        assert result.expand is not None
        assert "author" in result_expand
        assert "$expand" in result_expand["author"]
        assert result_expand["author"]["$expand"] == "user"

    def test_expand_with_multiple_options(self):
        """Test parsing $expand with multiple nested options."""
        result = parse_odata_query("$expand=author($select=id,name;$expand=user)")
        result_expand = expand_options("$expand=author($select=id,name;$expand=user)")

        assert result.expand is not None
        assert "author" in result_expand
        options = result_expand["author"]
        assert "$select" in options
        assert "$expand" in options
        assert options["$select"] == "id,name"
        assert options["$expand"] == "user"

    def test_expand_multiple_with_mixed_options(self):
        """Test parsing $expand with multiple fields, some with options, some without."""
        result = parse_odata_query("$expand=categories,author($select=id,name)")
        result_expand = expand_options("$expand=categories,author($select=id,name)")

        assert result.expand is not None
        assert "categories" in result_expand
        assert "author" in result_expand
        assert result_expand["categories"] == {}
        assert "$select" in result_expand["author"]

    def test_expand_semicolon_separator(self):
        """Test parsing $expand with semicolon separator (alternative syntax)."""
        result = parse_odata_query("$expand=categories;author($select=id,name)")
        result_expand = expand_options("$expand=categories;author($select=id,name)")

        assert result.expand is not None
        assert "categories" in result_expand
        assert "author" in result_expand

    def test_expand_deeply_nested(self):
        """Test parsing $expand with deeply nested options."""
        result = parse_odata_query("$expand=author($select=id;$expand=user($select=username))")
        result_expand = expand_options("$expand=author($select=id;$expand=user($select=username))")

        assert result.expand is not None
        assert "author" in result_expand
        options = result_expand["author"]
        assert "$select" in options
        assert "$expand" in options
        assert options["$expand"] == "user($select=username)"

    def test_no_expand(self):
        """Test query without $expand."""
        result = parse_odata_query("$select=id,name")

        assert result.expand is None


class TestFilterParsing:
    """Tests for $filter parameter parsing."""

    def test_filter_simple_equality(self):
        """Test parsing simple equality filter."""
        result = parse_odata_query("$filter=status eq 'published'")

        assert result.filter is not None
        assert result.filter.expression == "status eq 'published'"

    def test_filter_with_and(self):
        """Test parsing filter with AND operator."""
        result = parse_odata_query("$filter=status eq 'published' and rating gt 4.0")

        assert result.filter is not None
        assert result.filter.expression == "status eq 'published' and rating gt 4.0"

    def test_filter_with_or(self):
        """Test parsing filter with OR operator."""
        result = parse_odata_query("$filter=status eq 'draft' or status eq 'published'")

        assert result.filter is not None
        assert result.filter.expression == "status eq 'draft' or status eq 'published'"

    def test_filter_with_navigation(self):
        """Test parsing filter with navigation property."""
        result = parse_odata_query("$filter=author/name eq 'John'")

        assert result.filter is not None
        assert result.filter.expression == "author/name eq 'John'"

    def test_filter_with_nested_navigation(self):
        """Test parsing filter with nested navigation."""
        result = parse_odata_query("$filter=author/user/first_name eq 'Patricia'")

        assert result.filter is not None
        assert result.filter.expression == "author/user/first_name eq 'Patricia'"

    def test_filter_with_functions(self):
        """Test parsing filter with OData functions."""
        result = parse_odata_query("$filter=startswith(title,'Introduction')")

        assert result.filter is not None
        assert result.filter.expression == "startswith(title,'Introduction')"

    def test_malformed_filter_raises_error(self):
        """Test that malformed $filter raises an error instead of silently passing."""
        with pytest.raises((ODataSyntaxError, ValueError)):
            parse_odata_query("$filter=this is not valid odata!!")

    def test_no_filter(self):
        """Test query without $filter."""
        result = parse_odata_query("$select=id,name")

        assert result.filter is None


class TestOrderByParsing:
    """Tests for $orderby parameter parsing."""

    def test_orderby_single_field_default(self):
        """Test parsing $orderby with single field (default ascending)."""
        result = parse_odata_query("$orderby=name")

        assert result.orderby is not None
        assert [(f.field, f.direction) for f in result.orderby.fields] == [("name", "asc")]

    def test_orderby_single_field_asc(self):
        """Test parsing $orderby with explicit asc."""
        result = parse_odata_query("$orderby=name asc")

        assert result.orderby is not None
        assert [(f.field, f.direction) for f in result.orderby.fields] == [("name", "asc")]

    def test_orderby_single_field_desc(self):
        """Test parsing $orderby with desc."""
        result = parse_odata_query("$orderby=created_at desc")

        assert result.orderby is not None
        assert [(f.field, f.direction) for f in result.orderby.fields] == [("created_at", "desc")]

    def test_orderby_multiple_fields(self):
        """Test parsing $orderby with multiple fields."""
        result = parse_odata_query("$orderby=status asc,created_at desc")

        assert result.orderby is not None
        assert [(f.field, f.direction) for f in result.orderby.fields] == [("status", "asc"), ("created_at", "desc")]

    def test_orderby_with_spaces(self):
        """Test parsing $orderby with extra spaces."""
        result = parse_odata_query("$orderby=name  asc , created_at   desc")

        assert result.orderby is not None
        assert [(f.field, f.direction) for f in result.orderby.fields] == [("name", "asc"), ("created_at", "desc")]

    def test_orderby_case_insensitive_desc(self):
        """Test parsing $orderby with uppercase DESC."""
        result = parse_odata_query("$orderby=name DESC")

        assert result.orderby is not None
        assert [(f.field, f.direction) for f in result.orderby.fields] == [("name", "desc")]

    def test_orderby_case_insensitive_asc(self):
        """Test parsing $orderby with mixed case Asc."""
        result = parse_odata_query("$orderby=name Asc")

        assert result.orderby is not None
        assert [(f.field, f.direction) for f in result.orderby.fields] == [("name", "asc")]

    def test_orderby_field_ending_with_desc_word(self):
        """Test that field names like sort_desc are not confused with direction."""
        result = parse_odata_query("$orderby=sort_desc DESC")

        assert result.orderby is not None
        assert [(f.field, f.direction) for f in result.orderby.fields] == [("sort_desc", "desc")]

    def test_no_orderby(self):
        """Test query without $orderby."""
        result = parse_odata_query("$select=id,name")

        assert result.orderby is None


class TestPaginationParsing:
    """Tests for $top and $skip parameters."""

    def test_top(self):
        """Test parsing $top."""
        result = parse_odata_query("$top=10")

        assert result.pagination is not None and result.pagination.limit is not None
        assert result.pagination.limit == 10

    def test_skip(self):
        """Test parsing $skip."""
        result = parse_odata_query("$skip=20")

        assert result.pagination is not None and result.pagination.offset is not None
        assert result.pagination.offset == 20

    def test_top_and_skip(self):
        """Test parsing both $top and $skip."""
        result = parse_odata_query("$top=10&$skip=20")

        assert result.pagination is not None and result.pagination.limit is not None
        assert result.pagination is not None and result.pagination.offset is not None
        assert result.pagination.limit == 10
        assert result.pagination.offset == 20

    def test_no_pagination(self):
        """Test query without pagination."""
        result = parse_odata_query("$select=id,name")

        assert result.pagination is None or result.pagination.limit is None
        assert result.pagination is None or result.pagination.offset is None


class TestCountParsing:
    """Tests for $count parameter."""

    def test_count_true(self):
        """Test parsing $count=true."""
        result = parse_odata_query("$count=true")

        assert result.pagination.include_count is True

    def test_count_false(self):
        """Test parsing $count=false."""
        result = parse_odata_query("$count=false")

        assert result.pagination is None or result.pagination.include_count is False

    def test_count_case_insensitive(self):
        """Test parsing $count with different cases."""
        result1 = parse_odata_query("$count=True")
        result2 = parse_odata_query("$count=TRUE")

        assert result1.pagination.include_count is True
        assert result2.pagination.include_count is True

    def test_no_count(self):
        """Test query without $count."""
        result = parse_odata_query("$select=id,name")

        assert result.pagination is None


class TestCombinedParameters:
    """Tests for queries with multiple parameters combined."""

    def test_select_and_filter(self):
        """Test parsing $select with $filter."""
        result = parse_odata_query("$select=id,title&$filter=status eq 'published'")

        assert result.select is not None
        assert result.filter is not None
        assert set(result.select.fields) == {"id", "title"}
        assert result.filter.expression == "status eq 'published'"

    def test_select_and_expand(self):
        """Test parsing $select with $expand."""
        result = parse_odata_query("$select=id,title&$expand=author")
        result_expand = expand_options("$select=id,title&$expand=author")

        assert result.select is not None
        assert result.expand is not None
        assert "author" in result_expand

    def test_all_parameters(self):
        """Test parsing query with all parameters."""
        query = (
            "$select=id,title"
            "&$expand=author($select=name)"
            "&$filter=status eq 'published'"
            "&$orderby=created_at desc"
            "&$top=10"
            "&$skip=20"
            "&$count=true"
        )
        result = parse_odata_query(query)

        assert result.select is not None
        assert result.expand is not None
        assert result.filter is not None
        assert result.orderby is not None
        assert result.pagination is not None and result.pagination.limit is not None
        assert result.pagination is not None and result.pagination.offset is not None
        assert result.pagination.include_count is True

    def test_complex_real_world_query(self):
        """Test parsing complex real-world query."""
        query = (
            "$expand=categories;author($select=id;$expand=user($select=id,username))"
            "&$filter=author/user/first_name eq 'Patricia'"
        )
        result = parse_odata_query(query)
        result_expand = expand_options(query)

        assert result.expand is not None
        assert "categories" in result_expand
        assert "author" in result_expand
        assert "$select" in result_expand["author"]
        assert "$expand" in result_expand["author"]
        assert result.filter is not None


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_string(self):
        """Test parsing empty query string."""
        result = parse_odata_query("")

        assert isinstance(result, QueryIntent)
        assert result.select is None
        assert result.expand is None
        assert result.filter is None

    def test_none_input(self):
        """Test parsing None input."""
        result = parse_odata_query(None)

        assert isinstance(result, QueryIntent)

    def test_whitespace_only(self):
        """Test parsing whitespace-only string."""
        result = parse_odata_query("   ")

        assert isinstance(result, QueryIntent)
        assert result.select is None

    def test_url_encoded_query(self):
        """Test parsing URL-encoded query string."""
        # The parser should handle URL-encoded strings
        result = parse_odata_query("$filter=author/user/first_name%20eq%20%27Patricia%27")

        assert result.filter is not None
        # After URL decoding, it should be readable
        assert "first_name eq 'Patricia'" in result.filter.expression

    def test_dict_input(self):
        """Test parsing dictionary input."""
        query_dict = {"$select": "id,name", "$filter": "status eq 'published'"}
        result = parse_odata_query(query_dict)

        assert result.select is not None
        assert result.filter is not None
