"""
Comprehensive tests for OData query parser based on ODATA_TEST_URLS_COMPREHENSIVE.md.

This test suite covers ~360+ test URLs across all OData query options and combinations.
"""

from fc_selector.protocols.odata.parsers.query import parse_odata_query
from fc_selector.protocols.odata.parsers.query.models import (
    ODataQuery,
)

# ==============================================================================
# 1. BASIC OPTIONS - $select
# ==============================================================================


class TestSelectBasic:
    """Tests for $select parameter - basic field selection."""

    def test_select_single_field(self):
        """Test selecting a single field."""
        query = parse_odata_query("$select=id")

        assert query.select is not None
        assert query.select.fields == ["id"]

    def test_select_multiple_fields_two(self):
        """Test selecting two fields."""
        query = parse_odata_query("$select=id,name")

        assert query.select is not None
        assert set(query.select.fields) == {"id", "name"}

    def test_select_multiple_fields_three(self):
        """Test selecting three fields."""
        query = parse_odata_query("$select=id,name,email")

        assert query.select is not None
        assert set(query.select.fields) == {"id", "name", "email"}

    def test_select_multiple_fields_four(self):
        """Test selecting four fields."""
        query = parse_odata_query("$select=id,name,email,created_at")

        assert query.select is not None
        assert set(query.select.fields) == {"id", "name", "email", "created_at"}

    def test_select_many_fields(self):
        """Test selecting many fields."""
        query = parse_odata_query("$select=id,title,content,author_id,status,created_at,updated_at")

        assert query.select is not None
        assert len(query.select.fields) == 7
        assert "id" in query.select.fields
        assert "title" in query.select.fields
        assert "updated_at" in query.select.fields

    def test_select_with_spaces_after_comma(self):
        """Test select with spaces after commas."""
        query = parse_odata_query("$select=id, name")

        assert query.select is not None
        assert set(query.select.fields) == {"id", "name"}

    def test_select_with_spaces_before_comma(self):
        """Test select with spaces before commas."""
        query = parse_odata_query("$select=id , name , email")

        assert query.select is not None
        assert set(query.select.fields) == {"id", "name", "email"}

    def test_select_with_multiple_spaces(self):
        """Test select with multiple spaces around commas."""
        query = parse_odata_query("$select=id,  name,  email")

        assert query.select is not None
        assert set(query.select.fields) == {"id", "name", "email"}

    def test_select_underscore_fields(self):
        """Test selecting fields with underscores."""
        query = parse_odata_query("$select=first_name,last_name")

        assert query.select is not None
        assert set(query.select.fields) == {"first_name", "last_name"}

    def test_select_camelcase_fields(self):
        """Test selecting camelCase fields."""
        query = parse_odata_query("$select=firstName,lastName")

        assert query.select is not None
        assert set(query.select.fields) == {"firstName", "lastName"}

    def test_select_timestamp_fields(self):
        """Test selecting timestamp fields."""
        query = parse_odata_query("$select=created_at,updated_at,deleted_at")

        assert query.select is not None
        assert set(query.select.fields) == {"created_at", "updated_at", "deleted_at"}

    def test_select_foreign_key_fields(self):
        """Test selecting foreign key fields."""
        query = parse_odata_query("$select=author_id,category_id")

        assert query.select is not None
        assert set(query.select.fields) == {"author_id", "category_id"}

    def test_select_multiple_fk_fields(self):
        """Test selecting multiple foreign key fields."""
        query = parse_odata_query("$select=user_id,post_id,comment_id")

        assert query.select is not None
        assert set(query.select.fields) == {"user_id", "post_id", "comment_id"}


# ==============================================================================
# 1. BASIC OPTIONS - $expand
# ==============================================================================


class TestExpandBasic:
    """Tests for $expand parameter - relation expansion."""

    def test_expand_single_relation_author(self):
        """Test expanding author relation."""
        query = parse_odata_query("$expand=author")

        assert query.expand is not None
        assert "author" in query.expand.nested_options
        assert query.expand.nested_options["author"] == {}

    def test_expand_single_relation_categories(self):
        """Test expanding categories relation."""
        query = parse_odata_query("$expand=categories")

        assert query.expand is not None
        assert "categories" in query.expand.nested_options

    def test_expand_single_relation_comments(self):
        """Test expanding comments relation."""
        query = parse_odata_query("$expand=comments")

        assert query.expand is not None
        assert "comments" in query.expand.nested_options

    def test_expand_two_relations_comma(self):
        """Test expanding two relations with comma separator."""
        query = parse_odata_query("$expand=author,categories")

        assert query.expand is not None
        assert "author" in query.expand.nested_options
        assert "categories" in query.expand.nested_options

    def test_expand_three_relations_comma(self):
        """Test expanding three relations with comma separator."""
        query = parse_odata_query("$expand=author,categories,comments")

        assert query.expand is not None
        assert len(query.expand.nested_options) == 3
        assert "author" in query.expand.nested_options
        assert "categories" in query.expand.nested_options
        assert "comments" in query.expand.nested_options

    def test_expand_two_relations_semicolon(self):
        """Test expanding relations with semicolon separator (alternative syntax)."""
        query = parse_odata_query("$expand=author;categories")

        assert query.expand is not None
        assert "author" in query.expand.nested_options
        assert "categories" in query.expand.nested_options

    def test_expand_three_relations_semicolon(self):
        """Test expanding three relations with semicolon separator."""
        query = parse_odata_query("$expand=author;categories;comments")

        assert query.expand is not None
        assert len(query.expand.nested_options) == 3

    def test_expand_relation_user(self):
        """Test expanding user relation."""
        query = parse_odata_query("$expand=user")

        assert query.expand is not None
        assert "user" in query.expand.nested_options

    def test_expand_relation_profile(self):
        """Test expanding profile relation."""
        query = parse_odata_query("$expand=profile")

        assert query.expand is not None
        assert "profile" in query.expand.nested_options

    def test_expand_relation_posts(self):
        """Test expanding posts relation."""
        query = parse_odata_query("$expand=posts")

        assert query.expand is not None
        assert "posts" in query.expand.nested_options

    def test_expand_relation_with_underscore(self):
        """Test expanding relation with underscore."""
        query = parse_odata_query("$expand=related_posts")

        assert query.expand is not None
        assert "related_posts" in query.expand.nested_options

    def test_expand_hierarchical_relation(self):
        """Test expanding hierarchical relation."""
        query = parse_odata_query("$expand=parent_category")

        assert query.expand is not None
        assert "parent_category" in query.expand.nested_options

    def test_expand_multiple_with_tags(self):
        """Test expanding multiple including tags."""
        query = parse_odata_query("$expand=author,comments,tags")

        assert query.expand is not None
        assert len(query.expand.nested_options) == 3
        assert "tags" in query.expand.nested_options


# ==============================================================================
# 1. BASIC OPTIONS - $filter
# ==============================================================================


class TestFilterBasic:
    """Tests for $filter parameter - basic filtering."""

    def test_filter_eq_string(self):
        """Test filter with eq operator and string value."""
        query = parse_odata_query("$filter=status eq 'published'")

        assert query.filter is not None
        assert query.filter.value == "status eq 'published'"

    def test_filter_eq_string_draft(self):
        """Test filter eq with draft status."""
        query = parse_odata_query("$filter=status eq 'draft'")

        assert query.filter is not None
        assert query.filter.value == "status eq 'draft'"

    def test_filter_gt_number(self):
        """Test filter with gt (greater than) operator."""
        query = parse_odata_query("$filter=rating gt 4.0")

        assert query.filter is not None
        assert query.filter.value == "rating gt 4.0"

    def test_filter_ge_number(self):
        """Test filter with ge (greater or equal) operator."""
        query = parse_odata_query("$filter=rating ge 4.0")

        assert query.filter is not None
        assert query.filter.value == "rating ge 4.0"

    def test_filter_lt_number(self):
        """Test filter with lt (less than) operator."""
        query = parse_odata_query("$filter=rating lt 3.0")

        assert query.filter is not None
        assert query.filter.value == "rating lt 3.0"

    def test_filter_le_number(self):
        """Test filter with le (less or equal) operator."""
        query = parse_odata_query("$filter=rating le 3.0")

        assert query.filter is not None
        assert query.filter.value == "rating le 3.0"

    def test_filter_views_gt(self):
        """Test filter views greater than."""
        query = parse_odata_query("$filter=views gt 1000")

        assert query.filter is not None
        assert "views gt 1000" in query.filter.value

    def test_filter_price_eq_decimal(self):
        """Test filter with decimal price."""
        query = parse_odata_query("$filter=price eq 99.99")

        assert query.filter is not None
        assert "99.99" in query.filter.value

    def test_filter_boolean_true(self):
        """Test filter with boolean true."""
        query = parse_odata_query("$filter=is_active eq true")

        assert query.filter is not None
        assert "is_active eq true" in query.filter.value

    def test_filter_boolean_false(self):
        """Test filter with boolean false."""
        query = parse_odata_query("$filter=is_active eq false")

        assert query.filter is not None
        assert "is_active eq false" in query.filter.value

    def test_filter_ne_operator(self):
        """Test filter with ne (not equal) operator."""
        query = parse_odata_query("$filter=age ne 18")

        assert query.filter is not None
        assert query.filter.value == "age ne 18"

    def test_filter_string_with_spaces(self):
        """Test filter with string containing spaces."""
        query = parse_odata_query("$filter=title eq 'Introduction to OData'")

        assert query.filter is not None
        assert "Introduction to OData" in query.filter.value

    def test_filter_name_with_spaces(self):
        """Test filter name with spaces."""
        query = parse_odata_query("$filter=name eq 'John Doe'")

        assert query.filter is not None
        assert "John Doe" in query.filter.value


class TestFilterLogicalOperators:
    """Tests for $filter with logical operators (and, or)."""

    def test_filter_and_two_conditions(self):
        """Test filter with AND operator."""
        query = parse_odata_query("$filter=status eq 'published' and rating gt 4.0")

        assert query.filter is not None
        assert "and" in query.filter.value
        assert "status eq 'published'" in query.filter.value
        assert "rating gt 4.0" in query.filter.value

    def test_filter_and_three_conditions(self):
        """Test filter with AND operator - three conditions."""
        query = parse_odata_query("$filter=status eq 'published' and rating gt 4.0 and views gt 100")

        assert query.filter is not None
        assert query.filter.value.count("and") == 2

    def test_filter_and_with_boolean(self):
        """Test filter AND with boolean."""
        query = parse_odata_query("$filter=is_active eq true and price lt 100")

        assert query.filter is not None
        assert "is_active eq true" in query.filter.value
        assert "price lt 100" in query.filter.value

    def test_filter_and_with_date(self):
        """Test filter AND with date."""
        query = parse_odata_query("$filter=created_at gt '2024-01-01' and status eq 'published'")

        assert query.filter is not None
        assert "2024-01-01" in query.filter.value

    def test_filter_or_two_conditions(self):
        """Test filter with OR operator."""
        query = parse_odata_query("$filter=status eq 'draft' or status eq 'published'")

        assert query.filter is not None
        assert "or" in query.filter.value

    def test_filter_or_different_statuses(self):
        """Test filter OR with different statuses."""
        query = parse_odata_query("$filter=status eq 'published' or status eq 'archived'")

        assert query.filter is not None
        assert "archived" in query.filter.value

    def test_filter_or_with_ratings(self):
        """Test filter OR with ratings."""
        query = parse_odata_query("$filter=rating eq 5.0 or rating eq 4.5")

        assert query.filter is not None
        assert "5.0" in query.filter.value
        assert "4.5" in query.filter.value

    def test_filter_complex_and_or(self):
        """Test filter with combination of AND and OR."""
        query = parse_odata_query("$filter=(status eq 'published' or status eq 'draft') and rating gt 4.0")

        assert query.filter is not None
        assert "or" in query.filter.value
        assert "and" in query.filter.value

    def test_filter_complex_and_or_reverse(self):
        """Test filter with AND and OR in different order."""
        query = parse_odata_query("$filter=status eq 'published' and (rating gt 4.0 or views gt 1000)")

        assert query.filter is not None
        assert "and" in query.filter.value
        assert "or" in query.filter.value


class TestFilterNavigation:
    """Tests for $filter with navigation paths."""

    def test_filter_navigation_simple(self):
        """Test filter with simple navigation."""
        query = parse_odata_query("$filter=author/name eq 'John'")

        assert query.filter is not None
        assert "author/name" in query.filter.value

    def test_filter_navigation_email(self):
        """Test filter navigation with email."""
        query = parse_odata_query("$filter=author/email eq 'john@example.com'")

        assert query.filter is not None
        assert "author/email" in query.filter.value

    def test_filter_navigation_boolean(self):
        """Test filter navigation with boolean."""
        query = parse_odata_query("$filter=author/is_active eq true")

        assert query.filter is not None
        assert "author/is_active" in query.filter.value

    def test_filter_navigation_slug(self):
        """Test filter navigation with slug."""
        query = parse_odata_query("$filter=category/slug eq 'technology'")

        assert query.filter is not None
        assert "category/slug" in query.filter.value

    def test_filter_navigation_two_levels(self):
        """Test filter with two-level navigation."""
        query = parse_odata_query("$filter=author/user/first_name eq 'Patricia'")

        assert query.filter is not None
        assert "author/user/first_name" in query.filter.value

    def test_filter_navigation_three_levels(self):
        """Test filter with three-level navigation."""
        query = parse_odata_query("$filter=author/user/profile/country eq 'Spain'")

        assert query.filter is not None
        assert "author/user/profile/country" in query.filter.value

    def test_filter_navigation_deep_path(self):
        """Test filter with deep navigation path."""
        query = parse_odata_query("$filter=post/author/user/email eq 'test@example.com'")

        assert query.filter is not None
        assert "post/author/user/email" in query.filter.value


class TestFilterFunctions:
    """Tests for $filter with OData functions."""

    def test_filter_startswith(self):
        """Test filter with startswith function."""
        query = parse_odata_query("$filter=startswith(title,'Introduction')")

        assert query.filter is not None
        assert "startswith" in query.filter.value
        assert "Introduction" in query.filter.value

    def test_filter_endswith(self):
        """Test filter with endswith function."""
        query = parse_odata_query("$filter=endswith(email,'@gmail.com')")

        assert query.filter is not None
        assert "endswith" in query.filter.value
        assert "@gmail.com" in query.filter.value

    def test_filter_contains(self):
        """Test filter with contains function."""
        query = parse_odata_query("$filter=contains(title,'OData')")

        assert query.filter is not None
        assert "contains" in query.filter.value
        assert "OData" in query.filter.value

    def test_filter_tolower(self):
        """Test filter with tolower function."""
        query = parse_odata_query("$filter=tolower(name) eq 'john'")

        assert query.filter is not None
        assert "tolower" in query.filter.value

    def test_filter_toupper(self):
        """Test filter with toupper function."""
        query = parse_odata_query("$filter=toupper(status) eq 'PUBLISHED'")

        assert query.filter is not None
        assert "toupper" in query.filter.value

    def test_filter_round(self):
        """Test filter with round function."""
        query = parse_odata_query("$filter=round(rating) eq 4")

        assert query.filter is not None
        assert "round" in query.filter.value

    def test_filter_floor(self):
        """Test filter with floor function."""
        query = parse_odata_query("$filter=floor(price) eq 99")

        assert query.filter is not None
        assert "floor" in query.filter.value

    def test_filter_ceiling(self):
        """Test filter with ceiling function."""
        query = parse_odata_query("$filter=ceiling(rating) eq 5")

        assert query.filter is not None
        assert "ceiling" in query.filter.value

    def test_filter_year(self):
        """Test filter with year function."""
        query = parse_odata_query("$filter=year(created_at) eq 2024")

        assert query.filter is not None
        assert "year" in query.filter.value

    def test_filter_month(self):
        """Test filter with month function."""
        query = parse_odata_query("$filter=month(created_at) eq 12")

        assert query.filter is not None
        assert "month" in query.filter.value

    def test_filter_day(self):
        """Test filter with day function."""
        query = parse_odata_query("$filter=day(created_at) eq 25")

        assert query.filter is not None
        assert "day" in query.filter.value

    def test_filter_hour(self):
        """Test filter with hour function."""
        query = parse_odata_query("$filter=hour(created_at) eq 14")

        assert query.filter is not None
        assert "hour" in query.filter.value


# ==============================================================================
# 1. BASIC OPTIONS - $orderby
# ==============================================================================


class TestOrderByBasic:
    """Tests for $orderby parameter."""

    def test_orderby_single_field_implicit_asc(self):
        """Test orderby single field (implicit ascending)."""
        query = parse_odata_query("$orderby=name")

        assert query.orderby is not None
        assert query.orderby.fields == [("name", "asc")]

    def test_orderby_single_field_explicit_asc(self):
        """Test orderby single field with explicit asc."""
        query = parse_odata_query("$orderby=name asc")

        assert query.orderby is not None
        assert query.orderby.fields == [("name", "asc")]

    def test_orderby_single_field_desc(self):
        """Test orderby single field descending."""
        query = parse_odata_query("$orderby=created_at desc")

        assert query.orderby is not None
        assert query.orderby.fields == [("created_at", "desc")]

    def test_orderby_rating_desc(self):
        """Test orderby rating descending."""
        query = parse_odata_query("$orderby=rating desc")

        assert query.orderby is not None
        assert query.orderby.fields == [("rating", "desc")]

    def test_orderby_price_asc(self):
        """Test orderby price ascending."""
        query = parse_odata_query("$orderby=price asc")

        assert query.orderby is not None
        assert query.orderby.fields == [("price", "asc")]

    def test_orderby_two_fields(self):
        """Test orderby with two fields."""
        query = parse_odata_query("$orderby=status asc,created_at desc")

        assert query.orderby is not None
        assert len(query.orderby.fields) == 2
        assert query.orderby.fields[0] == ("status", "asc")
        assert query.orderby.fields[1] == ("created_at", "desc")

    def test_orderby_two_fields_same_direction(self):
        """Test orderby with two fields, both descending."""
        query = parse_odata_query("$orderby=rating desc,created_at desc")

        assert query.orderby is not None
        assert len(query.orderby.fields) == 2
        assert query.orderby.fields[0] == ("rating", "desc")
        assert query.orderby.fields[1] == ("created_at", "desc")

    def test_orderby_two_fields_both_asc(self):
        """Test orderby with two fields, both ascending."""
        query = parse_odata_query("$orderby=name asc,email asc")

        assert query.orderby is not None
        assert len(query.orderby.fields) == 2

    def test_orderby_four_fields(self):
        """Test orderby with four fields."""
        query = parse_odata_query("$orderby=category asc,title asc,created_at desc")

        assert query.orderby is not None
        assert len(query.orderby.fields) == 3

    def test_orderby_mixed_explicit_implicit(self):
        """Test orderby with mixed explicit and implicit directions."""
        query = parse_odata_query("$orderby=status,created_at desc")

        assert query.orderby is not None
        assert query.orderby.fields[0] == ("status", "asc")
        assert query.orderby.fields[1] == ("created_at", "desc")

    def test_orderby_with_extra_spaces(self):
        """Test orderby with extra spaces."""
        query = parse_odata_query("$orderby=name  asc")

        assert query.orderby is not None
        assert query.orderby.fields == [("name", "asc")]

    def test_orderby_with_spaces_around_comma(self):
        """Test orderby with spaces around comma."""
        query = parse_odata_query("$orderby=name asc , created_at desc")

        assert query.orderby is not None
        assert len(query.orderby.fields) == 2


# ==============================================================================
# 1. BASIC OPTIONS - $top and $skip
# ==============================================================================


class TestPaginationBasic:
    """Tests for $top and $skip parameters."""

    def test_top_value_1(self):
        """Test top with value 1."""
        query = parse_odata_query("$top=1")

        assert query.top is not None
        assert query.top.value == "1"

    def test_top_value_5(self):
        """Test top with value 5."""
        query = parse_odata_query("$top=5")

        assert query.top is not None
        assert query.top.value == "5"

    def test_top_value_10(self):
        """Test top with value 10."""
        query = parse_odata_query("$top=10")

        assert query.top is not None
        assert query.top.value == "10"

    def test_top_value_20(self):
        """Test top with value 20."""
        query = parse_odata_query("$top=20")

        assert query.top is not None
        assert query.top.value == "20"

    def test_top_value_50(self):
        """Test top with value 50."""
        query = parse_odata_query("$top=50")

        assert query.top is not None
        assert query.top.value == "50"

    def test_top_value_100(self):
        """Test top with value 100."""
        query = parse_odata_query("$top=100")

        assert query.top is not None
        assert query.top.value == "100"

    def test_top_value_1000(self):
        """Test top with value 1000."""
        query = parse_odata_query("$top=1000")

        assert query.top is not None
        assert query.top.value == "1000"

    def test_top_value_0(self):
        """Test top with value 0."""
        query = parse_odata_query("$top=0")

        assert query.top is not None
        assert query.top.value == "0"

    def test_top_large_value(self):
        """Test top with large value."""
        query = parse_odata_query("$top=999999")

        assert query.top is not None
        assert query.top.value == "999999"

    def test_skip_value_0(self):
        """Test skip with value 0."""
        query = parse_odata_query("$skip=0")

        assert query.skip is not None
        assert query.skip.value == "0"

    def test_skip_value_5(self):
        """Test skip with value 5."""
        query = parse_odata_query("$skip=5")

        assert query.skip is not None
        assert query.skip.value == "5"

    def test_skip_value_10(self):
        """Test skip with value 10."""
        query = parse_odata_query("$skip=10")

        assert query.skip is not None
        assert query.skip.value == "10"

    def test_skip_value_20(self):
        """Test skip with value 20."""
        query = parse_odata_query("$skip=20")

        assert query.skip is not None
        assert query.skip.value == "20"

    def test_skip_value_50(self):
        """Test skip with value 50."""
        query = parse_odata_query("$skip=50")

        assert query.skip is not None
        assert query.skip.value == "50"

    def test_skip_value_100(self):
        """Test skip with value 100."""
        query = parse_odata_query("$skip=100")

        assert query.skip is not None
        assert query.skip.value == "100"

    def test_skip_value_1000(self):
        """Test skip with value 1000."""
        query = parse_odata_query("$skip=1000")

        assert query.skip is not None
        assert query.skip.value == "1000"

    def test_skip_large_value(self):
        """Test skip with large value."""
        query = parse_odata_query("$skip=999999")

        assert query.skip is not None
        assert query.skip.value == "999999"

    def test_top_and_skip_together(self):
        """Test top and skip together."""
        query = parse_odata_query("$top=10&$skip=20")

        assert query.top is not None
        assert query.skip is not None
        assert query.top.value == "10"
        assert query.skip.value == "20"

    def test_pagination_page_1(self):
        """Test pagination first page."""
        query = parse_odata_query("$top=10&$skip=0")

        assert query.top.value == "10"
        assert query.skip.value == "0"

    def test_pagination_page_2(self):
        """Test pagination second page."""
        query = parse_odata_query("$top=10&$skip=10")

        assert query.top.value == "10"
        assert query.skip.value == "10"

    def test_pagination_page_3(self):
        """Test pagination third page."""
        query = parse_odata_query("$top=10&$skip=20")

        assert query.top.value == "10"
        assert query.skip.value == "20"

    def test_pagination_large_page_size(self):
        """Test pagination with large page size."""
        query = parse_odata_query("$top=20&$skip=40")

        assert query.top.value == "20"
        assert query.skip.value == "40"


# ==============================================================================
# 1. BASIC OPTIONS - $count
# ==============================================================================


class TestCountBasic:
    """Tests for $count parameter."""

    def test_count_true_lowercase(self):
        """Test count with lowercase true."""
        query = parse_odata_query("$count=true")

        assert query.count is True

    def test_count_false_lowercase(self):
        """Test count with lowercase false."""
        query = parse_odata_query("$count=false")

        assert query.count is False

    def test_count_true_capitalized(self):
        """Test count with capitalized True."""
        query = parse_odata_query("$count=True")

        assert query.count is True

    def test_count_true_uppercase(self):
        """Test count with uppercase TRUE."""
        query = parse_odata_query("$count=TRUE")

        assert query.count is True

    def test_count_false_capitalized(self):
        """Test count with capitalized False."""
        query = parse_odata_query("$count=False")

        assert query.count is False

    def test_count_false_uppercase(self):
        """Test count with uppercase FALSE."""
        query = parse_odata_query("$count=FALSE")

        assert query.count is False


# ==============================================================================
# 2. NESTED EXPANDS - With $select
# ==============================================================================


class TestNestedExpandsWithSelect:
    """Tests for nested expands with $select options."""

    def test_expand_with_select_single_field(self):
        """Test expand with select single field."""
        query = parse_odata_query("$expand=author($select=id)")

        assert query.expand is not None
        assert "author" in query.expand.nested_options
        assert "$select" in query.expand.nested_options["author"]
        assert query.expand.nested_options["author"]["$select"] == "id"

    def test_expand_with_select_two_fields(self):
        """Test expand with select two fields."""
        query = parse_odata_query("$expand=author($select=id,name)")

        assert query.expand is not None
        assert query.expand.nested_options["author"]["$select"] == "id,name"

    def test_expand_with_select_three_fields(self):
        """Test expand with select three fields."""
        query = parse_odata_query("$expand=author($select=id,name,email)")

        assert query.expand is not None
        assert query.expand.nested_options["author"]["$select"] == "id,name,email"

    def test_multiple_expands_each_with_select(self):
        """Test multiple expands, each with their own select."""
        query = parse_odata_query("$expand=author($select=id,name),categories($select=name)")

        assert query.expand is not None
        assert "author" in query.expand.nested_options
        assert "categories" in query.expand.nested_options
        assert query.expand.nested_options["author"]["$select"] == "id,name"
        assert query.expand.nested_options["categories"]["$select"] == "name"

    def test_multiple_expands_complex_selects(self):
        """Test multiple expands with complex selects."""
        query = parse_odata_query("$expand=author($select=id,name),categories($select=id,name,slug)")

        assert query.expand is not None
        assert "slug" in query.expand.nested_options["categories"]["$select"]

    def test_multiple_expands_with_timestamps(self):
        """Test multiple expands selecting timestamp fields."""
        query = parse_odata_query("$expand=author($select=id,name,email),comments($select=id,text,created_at)")

        assert query.expand is not None
        assert "created_at" in query.expand.nested_options["comments"]["$select"]

    def test_expand_with_select_semicolon_separator(self):
        """Test expand with select using semicolon separator."""
        query = parse_odata_query("$expand=author($select=id,name);categories($select=name)")

        assert query.expand is not None
        assert "author" in query.expand.nested_options
        assert "categories" in query.expand.nested_options

    def test_expand_with_select_multiple_semicolon(self):
        """Test multiple expands with semicolon and select."""
        query = parse_odata_query("$expand=author($select=id);categories($select=name);tags($select=id,name)")

        assert query.expand is not None
        assert len(query.expand.nested_options) == 3
        assert "tags" in query.expand.nested_options


# ==============================================================================
# 2. NESTED EXPANDS - With nested $expand
# ==============================================================================


class TestNestedExpandsRecursive:
    """Tests for recursive nested expands."""

    def test_expand_one_level_nesting(self):
        """Test expand with one level of nesting."""
        query = parse_odata_query("$expand=author($expand=user)")

        assert query.expand is not None
        assert "author" in query.expand.nested_options
        assert "$expand" in query.expand.nested_options["author"]
        assert query.expand.nested_options["author"]["$expand"] == "user"

    def test_expand_nested_profile(self):
        """Test expand with nested profile."""
        query = parse_odata_query("$expand=author($expand=profile)")

        assert query.expand is not None
        assert query.expand.nested_options["author"]["$expand"] == "profile"

    def test_expand_posts_nested_author(self):
        """Test expand posts with nested author."""
        query = parse_odata_query("$expand=posts($expand=author)")

        assert query.expand is not None
        assert "posts" in query.expand.nested_options
        assert query.expand.nested_options["posts"]["$expand"] == "author"

    def test_expand_hierarchical_parent(self):
        """Test expand with hierarchical parent relation."""
        query = parse_odata_query("$expand=category($expand=parent)")

        assert query.expand is not None
        assert "category" in query.expand.nested_options

    def test_expand_two_levels_nesting(self):
        """Test expand with two levels of nesting."""
        query = parse_odata_query("$expand=author($expand=user($expand=profile))")

        assert query.expand is not None
        assert "author" in query.expand.nested_options
        assert "$expand" in query.expand.nested_options["author"]

    def test_expand_two_levels_post_author_user(self):
        """Test expand post > author > user."""
        query = parse_odata_query("$expand=post($expand=author($expand=user))")

        assert query.expand is not None
        assert "post" in query.expand.nested_options

    def test_expand_two_levels_comment_post_author(self):
        """Test expand comment > post > author."""
        query = parse_odata_query("$expand=comment($expand=post($expand=author))")

        assert query.expand is not None
        assert "comment" in query.expand.nested_options

    def test_expand_three_levels_deep(self):
        """Test expand with three levels deep."""
        query = parse_odata_query("$expand=post($expand=author($expand=user($expand=profile)))")

        assert query.expand is not None
        assert "post" in query.expand.nested_options

    def test_expand_multiple_with_nested(self):
        """Test multiple expands where some have nested expands."""
        query = parse_odata_query("$expand=author($expand=user),categories($expand=parent)")

        assert query.expand is not None
        assert "author" in query.expand.nested_options
        assert "categories" in query.expand.nested_options

    def test_expand_multiple_one_nested_one_simple(self):
        """Test multiple expands, one nested and one simple."""
        query = parse_odata_query("$expand=author($expand=user($expand=profile)),categories")

        assert query.expand is not None
        assert "author" in query.expand.nested_options
        assert "categories" in query.expand.nested_options

    def test_expand_posts_and_comments_nested(self):
        """Test expand posts with author and comments with user."""
        query = parse_odata_query("$expand=posts($expand=author),comments($expand=user)")

        assert query.expand is not None
        assert len(query.expand.nested_options) == 2


# ==============================================================================
# 2. NESTED EXPANDS - With multiple options
# ==============================================================================


class TestNestedExpandsMultipleOptions:
    """Tests for nested expands with multiple query options."""

    def test_expand_with_select_and_expand(self):
        """Test expand with both select and nested expand."""
        query = parse_odata_query("$expand=author($select=id,name;$expand=user)")

        assert query.expand is not None
        assert "author" in query.expand.nested_options
        assert "$select" in query.expand.nested_options["author"]
        assert "$expand" in query.expand.nested_options["author"]

    def test_expand_select_and_nested_expand_simple(self):
        """Test expand with select and simple nested expand."""
        query = parse_odata_query("$expand=author($select=id;$expand=profile)")

        assert query.expand is not None
        assert query.expand.nested_options["author"]["$select"] == "id"
        assert query.expand.nested_options["author"]["$expand"] == "profile"

    def test_expand_posts_with_select_and_expand(self):
        """Test expand posts with select and nested expand author."""
        query = parse_odata_query("$expand=posts($select=title,content;$expand=author)")

        assert query.expand is not None
        assert "title,content" in query.expand.nested_options["posts"]["$select"]

    def test_expand_two_levels_with_select_at_each(self):
        """Test expand with select at each level."""
        query = parse_odata_query("$expand=author($select=id;$expand=user($select=username))")

        assert query.expand is not None
        assert "$expand" in query.expand.nested_options["author"]

    def test_expand_complex_nested_with_selects(self):
        """Test complex nested expand with selects at multiple levels."""
        query = parse_odata_query("$expand=author($select=id,name;$expand=user($select=id,username,email))")

        assert query.expand is not None
        assert "$select" in query.expand.nested_options["author"]

    def test_expand_three_levels_with_selects(self):
        """Test expand with three levels and select at each."""
        query = parse_odata_query("$expand=post($select=title;$expand=author($select=name;$expand=user))")

        assert query.expand is not None
        assert "post" in query.expand.nested_options

    def test_expand_with_select_expand_and_top(self):
        """Test expand with select, nested expand, and top."""
        query = parse_odata_query("$expand=author($select=id,name;$expand=user;$top=5)")

        assert query.expand is not None
        assert "$top" in query.expand.nested_options["author"]

    def test_expand_with_filter_and_orderby(self):
        """Test expand with filter and orderby options."""
        query = parse_odata_query("$expand=posts($select=title;$filter=status eq 'published';$orderby=created_at desc)")

        assert query.expand is not None
        assert "$filter" in query.expand.nested_options["posts"]
        assert "$orderby" in query.expand.nested_options["posts"]

    def test_expand_comments_with_orderby_top(self):
        """Test expand comments with orderby and top."""
        query = parse_odata_query("$expand=comments($select=text,created_at;$orderby=created_at desc;$top=10)")

        assert query.expand is not None
        assert "$orderby" in query.expand.nested_options["comments"]
        assert "$top" in query.expand.nested_options["comments"]

    def test_multiple_expands_each_with_options(self):
        """Test multiple expands each with their own options."""
        query = parse_odata_query("$expand=author($select=id,name;$expand=user),categories($select=name;$orderby=name)")

        assert query.expand is not None
        assert len(query.expand.nested_options) == 2
        assert "$orderby" in query.expand.nested_options["categories"]

    def test_multiple_expands_different_options(self):
        """Test multiple expands with different option combinations."""
        query = parse_odata_query("$expand=posts($select=title;$top=5),comments($select=text;$orderby=created_at desc)")

        assert query.expand is not None
        assert "$top" in query.expand.nested_options["posts"]
        assert "$orderby" in query.expand.nested_options["comments"]


# ==============================================================================
# 2. NESTED EXPANDS - Deeply nested
# ==============================================================================


class TestDeeplyNestedExpands:
    """Tests for deeply nested expands (3+ levels)."""

    def test_three_levels_with_select_at_bottom(self):
        """Test three-level expand with select at deepest level."""
        query = parse_odata_query("$expand=post($expand=author($expand=user($select=username)))")

        assert query.expand is not None
        assert "post" in query.expand.nested_options

    def test_three_levels_comment_post_author_profile(self):
        """Test three levels: comment > post > author > profile."""
        query = parse_odata_query("$expand=comment($expand=post($expand=author($expand=profile)))")

        assert query.expand is not None
        assert "comment" in query.expand.nested_options

    def test_four_levels_deep(self):
        """Test four levels of nested expands."""
        query = parse_odata_query("$expand=reply($expand=comment($expand=post($expand=author($expand=user))))")

        assert query.expand is not None
        assert "reply" in query.expand.nested_options

    def test_four_levels_with_select(self):
        """Test four levels with select at deepest level."""
        query = parse_odata_query("$expand=post($expand=category($expand=parent($expand=root($select=name))))")

        assert query.expand is not None
        assert "post" in query.expand.nested_options

    def test_deep_nesting_with_options_at_each_level(self):
        """Test deep nesting with options at each level."""
        query = parse_odata_query(
            "$expand=author($select=id;$expand=user($select=id,username;$expand=profile($select=bio)))"
        )

        assert query.expand is not None
        assert "$select" in query.expand.nested_options["author"]

    def test_deep_nesting_all_selects(self):
        """Test deep nesting with select at all levels."""
        query = parse_odata_query(
            "$expand=post($select=title;$expand=author($select=name;$expand=user($select=email;$expand=profile)))"
        )

        assert query.expand is not None
        assert "post" in query.expand.nested_options

    def test_multiple_branches_nested(self):
        """Test expand with multiple nested branches."""
        query = parse_odata_query("$expand=author($expand=user,profile),categories($expand=parent)")

        assert query.expand is not None
        assert "author" in query.expand.nested_options
        assert "categories" in query.expand.nested_options

    def test_complex_multiple_branches(self):
        """Test complex expand with multiple branches and nesting."""
        query = parse_odata_query("$expand=post($expand=author($expand=user,profile),category($expand=parent))")

        assert query.expand is not None
        assert "post" in query.expand.nested_options


# ==============================================================================
# 3. OPTION COMBINATIONS - 2 options
# ==============================================================================


class TestTwoOptionCombinations:
    """Tests for combinations of two query options."""

    def test_select_and_expand(self):
        """Test select with expand."""
        query = parse_odata_query("$select=id,title&$expand=author")

        assert query.select is not None
        assert query.expand is not None
        assert "id" in query.select.fields
        assert "author" in query.expand.nested_options

    def test_select_and_expand_multiple(self):
        """Test select with multiple expands."""
        query = parse_odata_query("$select=id,title,content&$expand=author,categories")

        assert query.select is not None
        assert query.expand is not None
        assert len(query.select.fields) == 3
        assert len(query.expand.nested_options) == 2

    def test_select_and_filter(self):
        """Test select with filter."""
        query = parse_odata_query("$select=id,title&$filter=status eq 'published'")

        assert query.select is not None
        assert query.filter is not None

    def test_select_and_orderby(self):
        """Test select with orderby."""
        query = parse_odata_query("$select=id,title&$orderby=created_at desc")

        assert query.select is not None
        assert query.orderby is not None

    def test_select_and_top(self):
        """Test select with top."""
        query = parse_odata_query("$select=id,title&$top=10")

        assert query.select is not None
        assert query.top is not None
        assert query.top.value == "10"

    def test_select_and_skip(self):
        """Test select with skip."""
        query = parse_odata_query("$select=id,title&$skip=20")

        assert query.select is not None
        assert query.skip is not None

    def test_select_and_count(self):
        """Test select with count."""
        query = parse_odata_query("$select=id,title&$count=true")

        assert query.select is not None
        assert query.count is True

    def test_expand_and_filter(self):
        """Test expand with filter."""
        query = parse_odata_query("$expand=author&$filter=status eq 'published'")

        assert query.expand is not None
        assert query.filter is not None

    def test_expand_and_orderby(self):
        """Test expand with orderby."""
        query = parse_odata_query("$expand=author&$orderby=created_at desc")

        assert query.expand is not None
        assert query.orderby is not None

    def test_expand_and_top(self):
        """Test expand with top."""
        query = parse_odata_query("$expand=author&$top=10")

        assert query.expand is not None
        assert query.top is not None

    def test_expand_and_count(self):
        """Test expand with count."""
        query = parse_odata_query("$expand=author&$count=true")

        assert query.expand is not None
        assert query.count is True

    def test_filter_and_orderby(self):
        """Test filter with orderby."""
        query = parse_odata_query("$filter=status eq 'published'&$orderby=created_at desc")

        assert query.filter is not None
        assert query.orderby is not None

    def test_filter_and_top(self):
        """Test filter with top."""
        query = parse_odata_query("$filter=status eq 'published'&$top=10")

        assert query.filter is not None
        assert query.top is not None

    def test_filter_and_count(self):
        """Test filter with count."""
        query = parse_odata_query("$filter=status eq 'published'&$count=true")

        assert query.filter is not None
        assert query.count is True

    def test_orderby_and_top(self):
        """Test orderby with top."""
        query = parse_odata_query("$orderby=created_at desc&$top=10")

        assert query.orderby is not None
        assert query.top is not None

    def test_top_and_skip_pagination(self):
        """Test top and skip together for pagination."""
        query = parse_odata_query("$top=10&$skip=20")

        assert query.top is not None
        assert query.skip is not None
        assert query.top.value == "10"
        assert query.skip.value == "20"

    def test_top_and_count(self):
        """Test top with count."""
        query = parse_odata_query("$top=10&$count=true")

        assert query.top is not None
        assert query.count is True


class TestThreeOptionCombinations:
    """Tests for combinations of three query options."""

    def test_select_expand_filter(self):
        """Test select, expand, and filter together."""
        query = parse_odata_query("$select=id,title&$expand=author&$filter=status eq 'published'")

        assert query.select is not None
        assert query.expand is not None
        assert query.filter is not None

    def test_select_expand_orderby(self):
        """Test select, expand, and orderby together."""
        query = parse_odata_query("$select=id,title&$expand=author&$orderby=created_at desc")

        assert query.select is not None
        assert query.expand is not None
        assert query.orderby is not None

    def test_select_expand_top(self):
        """Test select, expand, and top together."""
        query = parse_odata_query("$select=id,title&$expand=author&$top=10")

        assert query.select is not None
        assert query.expand is not None
        assert query.top is not None

    def test_select_filter_orderby(self):
        """Test select, filter, and orderby together."""
        query = parse_odata_query("$select=id,title&$filter=status eq 'published'&$orderby=created_at desc")

        assert query.select is not None
        assert query.filter is not None
        assert query.orderby is not None

    def test_select_filter_top(self):
        """Test select, filter, and top together."""
        query = parse_odata_query("$select=id,title&$filter=status eq 'published'&$top=10")

        assert query.select is not None
        assert query.filter is not None
        assert query.top is not None

    def test_expand_filter_orderby(self):
        """Test expand, filter, and orderby together."""
        query = parse_odata_query("$expand=author&$filter=status eq 'published'&$orderby=created_at desc")

        assert query.expand is not None
        assert query.filter is not None
        assert query.orderby is not None

    def test_expand_filter_top(self):
        """Test expand, filter, and top together."""
        query = parse_odata_query("$expand=author&$filter=status eq 'published'&$top=10")

        assert query.expand is not None
        assert query.filter is not None
        assert query.top is not None

    def test_filter_orderby_top(self):
        """Test filter, orderby, and top together."""
        query = parse_odata_query("$filter=status eq 'published'&$orderby=created_at desc&$top=10")

        assert query.filter is not None
        assert query.orderby is not None
        assert query.top is not None

    def test_filter_orderby_count(self):
        """Test filter, orderby, and count together."""
        query = parse_odata_query("$filter=status eq 'published'&$orderby=created_at desc&$count=true")

        assert query.filter is not None
        assert query.orderby is not None
        assert query.count is True

    def test_orderby_top_skip(self):
        """Test orderby, top, and skip together."""
        query = parse_odata_query("$orderby=created_at desc&$top=10&$skip=20")

        assert query.orderby is not None
        assert query.top is not None
        assert query.skip is not None

    def test_top_skip_count(self):
        """Test top, skip, and count together."""
        query = parse_odata_query("$top=10&$skip=20&$count=true")

        assert query.top is not None
        assert query.skip is not None
        assert query.count is True


class TestAllOptionsCombined:
    """Tests for queries with all options combined."""

    def test_all_seven_options(self):
        """Test query with all 7 OData options."""
        query = parse_odata_query(
            "$select=id,title&$expand=author&$filter=status eq 'published'"
            "&$orderby=created_at desc&$top=10&$skip=20&$count=true"
        )

        assert query.select is not None
        assert query.expand is not None
        assert query.filter is not None
        assert query.orderby is not None
        assert query.top is not None
        assert query.skip is not None
        assert query.count is True

    def test_all_options_with_complex_expand(self):
        """Test all options with complex nested expand."""
        query = parse_odata_query(
            "$select=id,title&$expand=author($select=id,name),categories"
            "&$filter=status eq 'published'&$orderby=created_at desc"
            "&$top=10&$skip=20&$count=true"
        )

        assert query.select is not None
        assert query.expand is not None
        assert "$select" in query.expand.nested_options["author"]

    def test_all_options_with_nested_expand(self):
        """Test all options with nested expand."""
        query = parse_odata_query(
            "$select=id,title&$expand=author($select=id;$expand=user)"
            "&$filter=status eq 'published'&$orderby=created_at desc"
            "&$top=10&$skip=20&$count=true"
        )

        assert query.select is not None
        assert "$expand" in query.expand.nested_options["author"]

    def test_all_options_complex_filter(self):
        """Test all options with complex filter."""
        query = parse_odata_query(
            "$select=id,title&$expand=author"
            "&$filter=status eq 'published' and rating gt 4.0"
            "&$orderby=created_at desc&$top=10&$skip=20&$count=true"
        )

        assert query.filter is not None
        assert "and" in query.filter.value

    def test_all_options_multiple_orderby(self):
        """Test all options with multiple orderby fields."""
        query = parse_odata_query(
            "$select=id,title&$expand=author&$filter=status eq 'published'"
            "&$orderby=rating desc,created_at desc&$top=10&$skip=20&$count=true"
        )

        assert query.orderby is not None
        assert len(query.orderby.fields) == 2


# ==============================================================================
# 4. EDGE CASES AND SPECIAL CASES
# ==============================================================================


class TestEdgeCasesEmptyAndWhitespace:
    """Tests for empty strings and whitespace."""

    def test_empty_query_string(self):
        """Test parsing empty query string."""
        query = parse_odata_query("")

        assert isinstance(query, ODataQuery)
        assert query.select is None
        assert query.expand is None
        assert query.filter is None

    def test_whitespace_only(self):
        """Test parsing whitespace-only string."""
        query = parse_odata_query("   ")

        assert isinstance(query, ODataQuery)
        assert query.select is None

    def test_none_input(self):
        """Test parsing None input."""
        query = parse_odata_query(None)

        assert isinstance(query, ODataQuery)


class TestEdgeCasesURLEncoding:
    """Tests for URL-encoded queries."""

    def test_url_encoded_spaces(self):
        """Test URL-encoded spaces in filter."""
        query = parse_odata_query("$filter=author/user/first_name%20eq%20%27Patricia%27")

        assert query.filter is not None
        # After decoding, should contain readable text
        assert "first_name" in query.filter.value

    def test_url_encoded_quotes(self):
        """Test URL-encoded quotes."""
        query = parse_odata_query("$filter=status%20eq%20%27published%27")

        assert query.filter is not None

    def test_url_encoded_commas_in_select(self):
        """Test URL-encoded commas in select."""
        query = parse_odata_query("$select=id%2Cname%2Cemail")

        assert query.select is not None
        # Should parse correctly after decoding


class TestEdgeCasesInvalidValues:
    """Tests for invalid or extreme values."""

    def test_top_negative_value(self):
        """Test top with negative value (should parse but may fail validation)."""
        query = parse_odata_query("$top=-1")

        assert query.top is not None
        assert query.top.value == "-1"

    def test_skip_negative_value(self):
        """Test skip with negative value."""
        query = parse_odata_query("$skip=-1")

        assert query.skip is not None
        assert query.skip.value == "-1"

    def test_top_string_value(self):
        """Test top with string value (should parse but validation should fail)."""
        query = parse_odata_query("$top=abc")

        assert query.top is not None
        assert query.top.value == "abc"

    def test_count_invalid_value(self):
        """Test count with invalid value."""
        query = parse_odata_query("$count=maybe")

        # Parser should handle this, validator should reject
        assert query.count is not True


class TestComplexRealWorldQueries:
    """Tests for complex real-world query scenarios."""

    def test_blog_published_posts_with_author(self):
        """Test blog: list published posts with author and categories."""
        query = parse_odata_query(
            "$select=id,title,content,published_at"
            "&$expand=author($select=name,email),categories"
            "&$filter=status eq 'published'"
            "&$orderby=published_at desc"
            "&$top=10"
            "&$count=true"
        )

        assert query.select is not None
        assert query.expand is not None
        assert query.filter is not None
        assert query.orderby is not None
        assert query.top is not None
        assert query.count is True

    def test_blog_posts_by_author(self):
        """Test blog: posts from specific author."""
        query = parse_odata_query(
            "$expand=author($select=name)&$filter=author/id eq 123&$orderby=published_at desc&$top=20"
        )

        assert query.expand is not None
        assert query.filter is not None
        assert "author/id" in query.filter.value

    def test_blog_search_by_title(self):
        """Test blog: search posts by title."""
        query = parse_odata_query(
            "$select=id,title,excerpt&$filter=contains(title,'Django')&$orderby=published_at desc&$top=20"
        )

        assert query.select is not None
        assert query.filter is not None
        assert "contains" in query.filter.value

    def test_ecommerce_products_in_stock(self):
        """Test e-commerce: products in stock with category."""
        query = parse_odata_query(
            "$select=id,name,price,stock"
            "&$expand=category($select=name)"
            "&$filter=stock gt 0 and is_active eq true"
            "&$orderby=price asc"
            "&$top=50"
            "&$count=true"
        )

        assert query.select is not None
        assert query.expand is not None
        assert query.filter is not None
        assert "stock gt 0" in query.filter.value

    def test_ecommerce_products_by_category(self):
        """Test e-commerce: products from specific category."""
        query = parse_odata_query(
            "$select=id,name,price"
            "&$expand=category($select=name,slug)"
            "&$filter=category/slug eq 'electronics'"
            "&$orderby=price desc"
            "&$top=30"
        )

        assert query.filter is not None
        assert "category/slug" in query.filter.value

    def test_users_active_with_profile(self):
        """Test users: active users with profile."""
        query = parse_odata_query(
            "$select=id,username,email"
            "&$expand=profile($select=first_name,last_name,avatar)"
            "&$filter=is_active eq true"
            "&$orderby=created_at desc"
            "&$top=50"
            "&$count=true"
        )

        assert query.select is not None
        assert query.expand is not None
        assert query.filter is not None

    def test_users_search_by_name(self):
        """Test users: search by username or email."""
        query = parse_odata_query(
            "$select=id,username,email"
            "&$filter=contains(username,'john') or contains(email,'john')"
            "&$orderby=username"
            "&$top=20"
        )

        assert query.filter is not None
        assert "or" in query.filter.value

    def test_social_posts_with_likes(self):
        """Test social: posts with most likes."""
        query = parse_odata_query(
            "$select=id,content,likes_count"
            "&$expand=author($select=username,avatar)"
            "&$filter=likes_count gt 50"
            "&$orderby=likes_count desc"
            "&$top=10"
        )

        assert query.select is not None
        assert query.expand is not None
        assert query.filter is not None

    def test_project_tasks_pending(self):
        """Test project management: pending tasks with assignees."""
        query = parse_odata_query(
            "$select=id,title,status,due_date"
            "&$expand=assigned_to($select=name,email)"
            "&$filter=status eq 'pending' and due_date lt '2024-12-31'"
            "&$orderby=due_date asc"
            "&$top=50"
            "&$count=true"
        )

        assert query.select is not None
        assert query.expand is not None
        assert query.filter is not None
        assert "and" in query.filter.value


class TestParserValidation:
    """Tests for ODataQuery validation."""

    def test_valid_query_validates(self):
        """Test that valid query passes validation."""
        query = parse_odata_query("$select=id,name&$filter=status eq 'published'")

        assert query.validate() is True

    def test_empty_query_validates(self):
        """Test that empty query passes validation."""
        query = parse_odata_query("")

        assert query.validate() is True

    def test_to_dict_method(self):
        """Test ODataQuery.to_dict() method."""
        query = parse_odata_query("$select=id,name&$filter=status eq 'published'&$top=10&$count=true")

        result = query.to_dict()

        assert "$select" in result
        assert "$filter" in result
        assert "$top" in result
        assert "$count" in result
        assert result["$select"] == "id,name"
        assert result["$filter"] == "status eq 'published'"
        assert result["$top"] == "10"
        assert result["$count"] is True

    def test_to_dict_with_expand(self):
        """Test to_dict with expand options."""
        query = parse_odata_query("$select=id&$expand=author($select=name)")

        result = query.to_dict()

        assert "$select" in result
        assert "$expand" in result


class TestParserDictInput:
    """Tests for parsing dictionary input."""

    def test_dict_input_basic(self):
        """Test parsing dictionary input."""
        query_dict = {"$select": "id,name", "$filter": "status eq 'published'"}
        query = parse_odata_query(query_dict)

        assert query.select is not None
        assert query.filter is not None

    def test_dict_input_with_expand(self):
        """Test dict input with expand."""
        query_dict = {"$select": "id,title", "$expand": "author", "$top": "10"}
        query = parse_odata_query(query_dict)

        assert query.select is not None
        assert query.expand is not None
        assert query.top is not None

    def test_dict_input_all_options(self):
        """Test dict input with all options."""
        query_dict = {
            "$select": "id,title",
            "$expand": "author",
            "$filter": "status eq 'published'",
            "$orderby": "created_at desc",
            "$top": "10",
            "$skip": "20",
            "$count": "true",
        }
        query = parse_odata_query(query_dict)

        assert query.select is not None
        assert query.expand is not None
        assert query.filter is not None
        assert query.orderby is not None
        assert query.top is not None
        assert query.skip is not None
        assert query.count is True


# Run with: pytest tests/core/test_parser_comprehensive.py -v
