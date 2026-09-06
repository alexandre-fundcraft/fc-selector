"""
Tests for QueryBuilder.
"""

from fc_selector.core.query_builder import QueryBuilder


class TestQueryBuilderInit:
    """Tests for QueryBuilder initialization."""

    def test_init_empty(self):
        query = QueryBuilder()
        assert query.build_query_string() == ""

    def test_init_with_query_string(self):
        query = QueryBuilder("$filter=Price gt 100&$top=10")
        result = query.build_query_string()
        assert "$filter=Price gt 100" in result
        assert "$top=10" in result


class TestQueryBuilderFromQueryString:
    """Tests for from_query_string class method."""

    def test_from_empty_string(self):
        query = QueryBuilder("")
        assert query.build_query_string() == ""

    def test_from_none_string(self):
        query = QueryBuilder(None)
        assert query.build_query_string() == ""

    def test_from_select(self):
        query = QueryBuilder("$select=id,name")
        assert "$select=id,name" in query.build_query_string()

    def test_from_filter(self):
        query = QueryBuilder("$filter=status eq 'active'")
        assert "$filter=status eq 'active'" in query.build_query_string()

    def test_from_top_skip(self):
        query = QueryBuilder("$top=10&$skip=20")
        result = query.build_query_string()
        assert "$top=10" in result
        assert "$skip=20" in result

    def test_from_orderby(self):
        query = QueryBuilder("$orderby=name desc")
        assert "$orderby=name desc" in query.build_query_string()

    def test_from_expand(self):
        query = QueryBuilder("$expand=author,categories")
        assert "$expand=author,categories" in query.build_query_string()

    def test_from_count(self):
        query = QueryBuilder("$count=true")
        assert "$count=true" in query.build_query_string()

    def test_from_complex_query(self):
        query_string = "$filter=status eq 'published'&$select=id,title&$top=10&$orderby=created_at desc"
        query = QueryBuilder(query_string)
        result = query.build_query_string()
        assert "$filter=status eq 'published'" in result
        assert "$select=id,title" in result
        assert "$top=10" in result
        assert "$orderby=created_at desc" in result


class TestQueryBuilderFilter:
    """Tests for filter methods."""

    def test_filter_sets_expression(self):
        query = QueryBuilder().filter("status eq 'active'")
        assert query.build_query_string() == "$filter=status eq 'active'"

    def test_filter_replaces_existing(self):
        query = QueryBuilder().filter("status eq 'active'").filter("status eq 'draft'")
        assert query.build_query_string() == "$filter=status eq 'draft'"

    def test_and_filter_without_existing(self):
        query = QueryBuilder().and_filter("status eq 'active'")
        assert query.build_query_string() == "$filter=status eq 'active'"

    def test_and_filter_with_existing(self):
        query = QueryBuilder().filter("status eq 'active'").and_filter("featured eq true")
        assert query.build_query_string() == "$filter=(status eq 'active') and (featured eq true)"

    def test_or_filter_without_existing(self):
        query = QueryBuilder().or_filter("status eq 'active'")
        assert query.build_query_string() == "$filter=status eq 'active'"

    def test_or_filter_with_existing(self):
        query = QueryBuilder().filter("status eq 'active'").or_filter("status eq 'draft'")
        assert query.build_query_string() == "$filter=(status eq 'active') or (status eq 'draft')"

    def test_chained_and_filters(self):
        query = QueryBuilder().filter("status eq 'published'").and_filter("featured eq true").and_filter("rating gt 4")
        result = query.build_query_string()
        assert "status eq 'published'" in result
        assert "featured eq true" in result
        assert "rating gt 4" in result


class TestQueryBuilderSelect:
    """Tests for select method."""

    def test_select_single_field(self):
        query = QueryBuilder().select("id")
        assert query.build_query_string() == "$select=id"

    def test_select_multiple_fields(self):
        query = QueryBuilder().select("id", "name", "email")
        assert query.build_query_string() == "$select=id,name,email"

    def test_select_comma_separated_string(self):
        query = QueryBuilder().select("id,name,email")
        assert query.build_query_string() == "$select=id,name,email"


class TestQueryBuilderExpand:
    """Tests for expand method."""

    def test_expand_single(self):
        query = QueryBuilder().expand("author")
        assert query.build_query_string() == "$expand=author"

    def test_expand_multiple(self):
        query = QueryBuilder().expand("author", "categories")
        assert query.build_query_string() == "$expand=author,categories"

    def test_expand_comma_separated(self):
        query = QueryBuilder().expand("author,categories")
        assert query.build_query_string() == "$expand=author,categories"


class TestQueryBuilderOrderBy:
    """Tests for orderby method."""

    def test_orderby_single(self):
        query = QueryBuilder().orderby("name")
        assert query.build_query_string() == "$orderby=name"

    def test_orderby_with_direction(self):
        query = QueryBuilder().orderby("name desc")
        assert query.build_query_string() == "$orderby=name desc"

    def test_orderby_multiple(self):
        query = QueryBuilder().orderby("name desc", "id asc")
        assert query.build_query_string() == "$orderby=name desc,id asc"


class TestQueryBuilderPagination:
    """Tests for top, skip, and count methods."""

    def test_top(self):
        query = QueryBuilder().top(10)
        assert query.build_query_string() == "$top=10"

    def test_skip(self):
        query = QueryBuilder().skip(20)
        assert query.build_query_string() == "$skip=20"

    def test_top_and_skip(self):
        query = QueryBuilder().top(10).skip(20)
        result = query.build_query_string()
        assert "$top=10" in result
        assert "$skip=20" in result

    def test_count_true(self):
        query = QueryBuilder().count(True)
        assert query.build_query_string() == "$count=true"

    def test_count_false(self):
        query = QueryBuilder().count(False)
        assert query.build_query_string() == "$count=false"


class TestQueryBuilderBuild:
    """Tests for build methods."""

    def test_build_query_string_empty(self):
        query = QueryBuilder()
        assert query.build_query_string() == ""

    def test_build_query_string_with_filter(self):
        query = QueryBuilder().filter("Price gt 100")
        assert query.build_query_string() == "$filter=Price gt 100"

    def test_build_query_string_from_existing(self):
        query = QueryBuilder("$select=id,name").filter("Price gt 100")
        result = query.build_query_string()
        assert "$filter=Price gt 100" in result
        assert "$select=id,name" in result

    def test_to_dict(self):
        query = QueryBuilder().filter("status eq 'active'").select("id", "name").top(10)
        result = query.to_dict()
        assert result["$filter"] == "status eq 'active'"
        assert result["$select"] == "id,name"
        assert result["$top"] == "10"


class TestQueryBuilderChaining:
    """Tests for method chaining."""

    def test_full_chain(self):
        query = (
            QueryBuilder()
            .filter("status eq 'published'")
            .and_filter("id eq 5")
            .select("id", "title", "author")
            .expand("author")
            .orderby("created_at desc")
            .top(10)
            .skip(0)
        )
        result = query.build_query_string()
        assert "$filter=" in result
        assert "status eq 'published'" in result
        assert "id eq 5" in result
        assert "$select=id,title,author" in result
        assert "$expand=author" in result
        assert "$orderby=created_at desc" in result
        assert "$top=10" in result
        assert "$skip=0" in result

    def test_from_query_string_and_modify(self):
        """Test parsing existing query and adding more filters."""
        query = QueryBuilder("$select=id,name&$top=10")
        query.and_filter("id eq 5")
        result = query.build_query_string()
        assert "$filter=id eq 5" in result
        assert "$select=id,name" in result
        assert "$top=10" in result


class TestQueryBuilderStringRepresentation:
    """Tests for string representation."""

    def test_str(self):
        query = QueryBuilder().filter("Price gt 100")
        assert str(query) == "$filter=Price gt 100"

    def test_str_from_query_string(self):
        query = QueryBuilder("$select=id,name").filter("Price gt 100")
        result = str(query)
        assert "$filter=Price gt 100" in result
        assert "$select=id,name" in result

    def test_repr(self):
        query = QueryBuilder().filter("status eq 'active'")
        assert "QueryBuilder" in repr(query)
        assert "status eq 'active'" in repr(query)
