"""Integration tests for OData $apply execution against the example/blog app."""

from django.contrib.auth.models import User
from django.test import TestCase

from example.blog.models import Author, BlogPost, Category
from example.blog.selectors.blog_post import BlogPostSelector
from fc_selector.core.exceptions import UnsupportedFunctionError


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
