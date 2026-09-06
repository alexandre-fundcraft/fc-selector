"""
Tests for the fluent Expand and OrderBy API.
"""

import pytest

from fc_selector.core.filters import Expand, Field, OrderBy
from fc_selector.core.intent import QueryIntent
from fc_selector.core.query_builder import QueryBuilder


class TestOrderBy:
    """Tests for OrderBy class."""

    def test_orderby_default_asc(self):
        """OrderBy defaults to ascending."""
        ob = OrderBy("name")
        assert ob.field == "name"
        assert ob.direction == "asc"

    def test_orderby_explicit_asc(self):
        """OrderBy.asc() sets ascending."""
        ob = OrderBy("name").asc()
        assert ob.direction == "asc"

    def test_orderby_desc(self):
        """OrderBy.desc() sets descending."""
        ob = OrderBy("created_at").desc()
        assert ob.field == "created_at"
        assert ob.direction == "desc"

    def test_orderby_repr(self):
        """OrderBy has readable repr."""
        assert "name" in repr(OrderBy("name"))
        assert "desc" in repr(OrderBy("name").desc())


class TestExpand:
    """Tests for Expand class."""

    def test_expand_simple(self):
        """Simple Expand with just relation name."""
        exp = Expand("author")
        assert exp.relation == "author"

    def test_expand_with_select(self):
        """Expand with nested select."""
        exp = Expand("author").select("id", "name", "email")
        assert exp._select_fields == ["id", "name", "email"]

    def test_expand_with_select_comma_string(self):
        """Expand.select() accepts comma-separated string."""
        exp = Expand("author").select("id,name,email")
        assert exp._select_fields == ["id", "name", "email"]

    def test_expand_with_filter(self):
        """Expand with nested filter."""
        exp = Expand("comments").filter(Field("approved").eq(True))
        assert exp._filter_ast is not None

    def test_expand_with_top(self):
        """Expand with top limit."""
        exp = Expand("comments").top(5)
        assert exp._top_value == 5

    def test_expand_with_skip(self):
        """Expand with skip offset."""
        exp = Expand("comments").skip(10)
        assert exp._skip_value == 10

    def test_expand_with_orderby_objects(self):
        """Expand with OrderBy objects."""
        exp = Expand("comments").orderby(OrderBy("created_at").desc(), OrderBy("id").asc())
        assert exp._orderby_specs == [("created_at", "desc"), ("id", "asc")]

    def test_expand_with_orderby_strings(self):
        """Expand.orderby() also accepts strings."""
        exp = Expand("comments").orderby("created_at desc", "id asc")
        assert exp._orderby_specs == [("created_at", "desc"), ("id", "asc")]

    def test_expand_nested(self):
        """Expand with nested expand."""
        exp = Expand("author").expand(Expand("profile").select("avatar", "bio"))
        assert exp._nested_expands is not None
        assert len(exp._nested_expands) == 1
        assert exp._nested_expands[0].relation == "profile"

    def test_expand_chained(self):
        """Expand with multiple chained options."""
        exp = (
            Expand("comments")
            .select("id", "text")
            .filter(Field("approved").eq(True))
            .orderby(OrderBy("created_at").desc())
            .top(5)
        )
        assert exp._select_fields == ["id", "text"]
        assert exp._filter_ast is not None
        assert exp._orderby_specs == [("created_at", "desc")]
        assert exp._top_value == 5

    def test_expand_filter_type_error(self):
        """Expand.filter() raises TypeError for non-Expression."""
        with pytest.raises(TypeError) as exc:
            Expand("comments").filter("not an expression")
        assert "Expression" in str(exc.value)

    def test_expand_nested_type_error(self):
        """Expand.expand() raises TypeError for non-Expand."""
        with pytest.raises(TypeError) as exc:
            Expand("author").expand("not an expand")
        assert "Expand" in str(exc.value)


class TestExpandToIntent:
    """Tests for Expand.to_intent() method."""

    def test_to_intent_empty(self):
        """Empty expand returns empty QueryIntent."""
        exp = Expand("author")
        intent = exp.to_intent()
        assert intent == QueryIntent()

    def test_to_intent_with_select(self):
        """Expand with select creates SelectIntent."""
        exp = Expand("author").select("id", "name")
        intent = exp.to_intent()
        assert intent.select is not None
        assert intent.select.fields == ["id", "name"]

    def test_to_intent_with_filter(self):
        """Expand with filter creates FilterIntent."""
        exp = Expand("comments").filter(Field("approved").eq(True))
        intent = exp.to_intent()
        assert intent.filter is not None
        assert intent.filter.has_filter()

    def test_to_intent_with_pagination(self):
        """Expand with top/skip creates PaginationIntent."""
        exp = Expand("comments").top(5).skip(10)
        intent = exp.to_intent()
        assert intent.pagination is not None
        assert intent.pagination.limit == 5
        assert intent.pagination.offset == 10

    def test_to_intent_with_orderby(self):
        """Expand with orderby creates OrderIntent."""
        exp = Expand("comments").orderby(OrderBy("created_at").desc())
        intent = exp.to_intent()
        assert intent.orderby is not None
        assert intent.orderby.fields[0].field == "created_at"
        assert intent.orderby.fields[0].direction == "desc"

    def test_to_intent_with_nested_expand(self):
        """Expand with nested expand creates ExpandIntent."""
        exp = Expand("author").expand(Expand("profile").select("avatar"))
        intent = exp.to_intent()
        assert intent.expand is not None
        assert "profile" in intent.expand.relations
        assert intent.expand.relations["profile"].select.fields == ["avatar"]


class TestQueryBuilderExpandFluent:
    """Tests for QueryBuilder.expand() with Expand objects."""

    def test_expand_single_object(self):
        """expand() with single Expand object."""
        builder = QueryBuilder().expand(Expand("author").select("id", "name"))
        intent = builder.build()

        assert intent.expand is not None
        assert "author" in intent.expand.relations
        nested = intent.expand.relations["author"]
        assert nested.select.fields == ["id", "name"]

    def test_expand_multiple_objects(self):
        """expand() with multiple Expand objects."""
        builder = QueryBuilder().expand(
            Expand("author").select("id", "name"),
            Expand("category").select("id", "title"),
        )
        intent = builder.build()

        assert set(intent.expand.relations) == {"author", "category"}
        assert intent.expand.relations["author"].select.fields == ["id", "name"]
        assert intent.expand.relations["category"].select.fields == ["id", "title"]

    def test_expand_with_filter(self):
        """expand() with nested filter."""
        builder = QueryBuilder().expand(Expand("comments").filter(Field("approved").eq(True)).top(5))
        intent = builder.build()

        nested = intent.expand.relations["comments"]
        assert nested.filter is not None
        assert nested.filter.has_filter()
        assert nested.pagination.limit == 5

    def test_expand_mixed_type_error(self):
        """expand() raises TypeError when mixing strings and Expand objects."""
        with pytest.raises(TypeError) as exc:
            QueryBuilder().expand(
                Expand("author"),
                "category",  # String mixed with Expand
            )
        assert "cannot mix" in str(exc.value)

    def test_expand_strings_still_work(self):
        """expand() still works with strings (backward compatible)."""
        builder = QueryBuilder().expand("author", "category")
        intent = builder.build()

        assert set(intent.expand.relations) == {"author", "category"}


class TestQueryBuilderOrderbyFluent:
    """Tests for QueryBuilder.orderby() with OrderBy objects."""

    def test_orderby_single_object(self):
        """orderby() with single OrderBy object."""
        builder = QueryBuilder().orderby(OrderBy("created_at").desc())
        intent = builder.build()

        assert intent.orderby is not None
        assert len(intent.orderby.fields) == 1
        assert intent.orderby.fields[0].field == "created_at"
        assert intent.orderby.fields[0].direction == "desc"

    def test_orderby_multiple_objects(self):
        """orderby() with multiple OrderBy objects."""
        builder = QueryBuilder().orderby(OrderBy("created_at").desc(), OrderBy("name").asc())
        intent = builder.build()

        assert len(intent.orderby.fields) == 2
        assert intent.orderby.fields[0].field == "created_at"
        assert intent.orderby.fields[0].direction == "desc"
        assert intent.orderby.fields[1].field == "name"
        assert intent.orderby.fields[1].direction == "asc"

    def test_orderby_mixed_type_error(self):
        """orderby() raises TypeError when mixing strings and OrderBy objects."""
        with pytest.raises(TypeError) as exc:
            QueryBuilder().orderby(
                OrderBy("created_at").desc(),
                "name asc",  # String mixed with OrderBy
            )
        assert "cannot mix" in str(exc.value)

    def test_orderby_strings_still_work(self):
        """orderby() still works with strings (backward compatible)."""
        builder = QueryBuilder().orderby("created_at desc", "name asc")
        intent = builder.build()

        assert intent.orderby.fields[0].field == "created_at"
        assert intent.orderby.fields[0].direction == "desc"
