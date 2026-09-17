"""Tests for Meta.field_annotations / Meta.annotation_dependencies: on-demand,
dependency-resolved queryset annotations for fields a plain field_aliases
dotted-path rename can't express (concatenation, conditional expressions,
cross-field arithmetic)."""

from django.contrib.auth.models import User
from django.db import connection
from django.db.models import Case, CharField, Count, F, Value, When
from django.db.models.functions import Concat
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from example.blog.models import Author, BlogPost
from fc_selector.django.selector import ODataSelector


def _full_name():
    return Concat(F("user__first_name"), Value(" "), F("user__last_name"), output_field=CharField())


def _is_prolific():
    """Depends on 'post_count' being annotated first — proves annotation_dependencies."""
    return Case(When(post_count__gte=2, then=Value(True)), default=Value(False))


class _AuthorStatsSelector(ODataSelector):
    class Meta:
        model = Author
        dto_class = None
        allowed_fields = ["full_name", "is_prolific"]
        field_annotations = {
            "full_name": _full_name,
            "post_count": lambda: Count("posts"),
            "is_prolific": _is_prolific,
        }
        annotation_dependencies = {"is_prolific": ("post_count",)}


class TestFieldAnnotations(TestCase):
    @classmethod
    def setUpTestData(cls):
        user1 = User.objects.create(username="alice", first_name="Alice", last_name="Smith")
        user2 = User.objects.create(username="bob", first_name="Bob", last_name="Jones")
        author1 = Author.objects.create(user=user1)
        author2 = Author.objects.create(user=user2)
        BlogPost.objects.create(title="A", slug="a1", content="x", author=author1)
        BlogPost.objects.create(title="B", slug="a2", content="y", author=author1)
        BlogPost.objects.create(title="C", slug="b1", content="z", author=author2)

    def test_annotation_used_in_filter(self):
        selector = _AuthorStatsSelector()
        result = selector.query_as_dicts("$filter=full_name eq 'Alice Smith'&$select=full_name")
        assert result == [{"full_name": "Alice Smith"}]

    def test_dependent_annotation_resolves_transitively(self):
        selector = _AuthorStatsSelector()
        result = selector.query_as_dicts("$filter=is_prolific eq true&$select=full_name")
        assert result == [{"full_name": "Alice Smith"}]

    def test_untouched_annotation_is_never_computed(self):
        """A field the request never references must not be annotated — proves
        on-demand behavior, not "annotate everything registered"."""
        selector = _AuthorStatsSelector()
        with CaptureQueriesContext(connection) as queries:
            result = selector.query_as_dicts("$select=full_name")
        assert result[0]["full_name"] in ("Alice Smith", "Bob Jones")
        executed_sql = " ".join(q["sql"] for q in queries)
        assert "post_count" not in executed_sql
        assert "COUNT" not in executed_sql

        _, intent = selector._parse("$select=full_name")
        prepared_qs = selector._executor._execute_prepared(selector.get_queryset(), intent)
        assert "post_count" not in prepared_qs.query.annotations
        assert "is_prolific" not in prepared_qs.query.annotations
        assert "full_name" in prepared_qs.query.annotations
