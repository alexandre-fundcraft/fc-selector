"""Integration tests for OData $apply execution against the example/blog app."""

from django.contrib.auth.models import User
from django.db.models import F
from django.test import TestCase

from example.blog.models import Author, BlogPost, Category
from example.blog.selectors.blog_post import AuthorDTO, BlogPostDTO, BlogPostSelector
from fc_selector.core.exceptions import QueryError, UnsupportedFunctionError
from fc_selector.django.selector import ODataSelector


class _AliasedPostSelector(ODataSelector):
    class Meta:
        model = BlogPost
        dto_class = None
        field_aliases = {"post_status": "status", "score": "rating"}
        allowed_fields = ["post_status", "score"]


class _AnnotatedPostSelector(ODataSelector):
    class Meta:
        model = BlogPost
        dto_class = None
        allowed_fields = None
        field_annotations = {
            "score_doubled": lambda: F("rating") * 2,
        }


class _HybridBlogPostSelector(ODataSelector):
    class Meta:
        model = BlogPost
        dto_class = BlogPostDTO
        values_mode = True
        expandable_fields = {"author": AuthorDTO}
        field_annotations = {"score_doubled": lambda: F("rating") * 2}
        allowed_fields = ["title", "author", "score_doubled"]


class TestApplyExecution(TestCase):
    @classmethod
    def setUpTestData(cls):
        user1 = User.objects.create(username="alice")
        user2 = User.objects.create(username="bob")
        cls.author1 = Author.objects.create(user=user1)
        cls.author2 = Author.objects.create(user=user2)
        cls.cat = Category.objects.create(name="tech")
        BlogPost.objects.create(title="A", slug="a", content="x", author=cls.author1, status="published", rating=4.0)
        BlogPost.objects.create(title="B", slug="b", content="y", author=cls.author1, status="published", rating=5.0)
        BlogPost.objects.create(title="C", slug="c", content="z", author=cls.author2, status="draft", rating=3.0)

    def test_bare_count(self):
        selector = BlogPostSelector()
        result = selector.query_as_dicts("$apply=aggregate($count as total)")
        assert result == [{"total": 3}]

    def test_groupby_with_count(self):
        selector = BlogPostSelector()
        result = selector.query_as_dicts("$apply=groupby((status), aggregate($count as n))")
        by_status = {row["status"]: row["n"] for row in result}
        assert by_status == {"published": 2, "draft": 1}

    def test_groupby_with_standard_aggregates(self):
        selector = BlogPostSelector()
        result = selector.query_as_dicts(
            "$apply=groupby((status), aggregate(rating with average as avg_rating, rating with countdistinct as distinct_ratings))"
        )
        published = next(r for r in result if r["status"] == "published")
        assert published["avg_rating"] == 4.5
        assert published["distinct_ratings"] == 2

    def test_groupby_no_aggregate_returns_distinct_rows(self):
        selector = BlogPostSelector()
        result = selector.query_as_dicts("$apply=groupby((status))")
        assert {r["status"] for r in result} == {"published", "draft"}

    def test_filter_then_groupby(self):
        selector = BlogPostSelector()
        result = selector.query_as_dicts(
            "$apply=filter(status eq 'published')/groupby((status), aggregate($count as n))"
        )
        assert result == [{"status": "published", "n": 2}]

    def test_unknown_aggregate_method_raises(self):
        selector = BlogPostSelector()
        with self.assertRaises(UnsupportedFunctionError):
            selector.query_as_dicts("$apply=groupby((status), aggregate(rating with median as m))")

    def test_filter_only_pipeline_returns_dicts(self):
        selector = BlogPostSelector()
        result = selector.query_as_dicts("$apply=filter(status eq 'draft')")
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["status"] == "draft"

    def test_apply_with_expand_raises_query_error(self):
        selector = BlogPostSelector()
        with self.assertRaises(QueryError):
            selector.query_as_dicts("$apply=groupby((status))&$expand=author")

    def test_query_and_query_as_dtos_reject_apply(self):
        selector = BlogPostSelector()
        with self.assertRaises(QueryError):
            selector.query("$apply=groupby((status))")
        with self.assertRaises(QueryError):
            selector.query_as_dtos("$apply=groupby((status))")

    def test_bare_aggregate_not_terminal_raises_query_error(self):
        selector = BlogPostSelector()
        with self.assertRaises(QueryError):
            selector.query_as_dicts("$apply=aggregate($count as n)/filter(n gt 1)")

    def test_groupby_and_aggregate_with_field_aliases(self):
        selector = _AliasedPostSelector()
        result = selector.query_as_dicts("$apply=groupby((post_status), aggregate(score with average as avg_score))")
        assert any(r["post_status"] == "published" and r["avg_score"] == 4.5 for r in result)

    def test_filter_by_annotated_field_in_apply(self):
        selector = _AnnotatedPostSelector()
        result = selector.query_as_dicts("$apply=filter(score_doubled gt 8)/groupby((status))")
        assert result == [{"status": "published"}]

    def test_hybrid_expand_with_field_annotations(self):
        selector = _HybridBlogPostSelector()
        result = selector.query_as_dicts("$filter=score_doubled gt 8&$expand=author&$select=title")
        assert len(result) == 1
        assert result[0]["title"] == "B"
        assert "author" in result[0]
