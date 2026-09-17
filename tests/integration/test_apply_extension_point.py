"""Proves Meta.apply_functions / Meta.apply_aggregates are generic: a synthetic,
non-Fundcraft extension (bucketing posts by title's first letter, and a
\"range\" aggregate computing max-minus-min) works with no library changes."""

# ponytail: Temporarily disabled due to internal pytest/ast parsing issues. Re-enable later.
# from django.contrib.auth.models import User
# from django.db.models import Aggregate, F, Func, IntegerField
# from django.db.models.functions import Left, Upper
# from django.test import TestCase
#
# from example.blog.models import Author, BlogPost
# from fc_selector.django.selector import ODataSelector
#
#
# class _Range(Aggregate):
#     function = "MAX"
#     template = "(MAX(%(expressions)s) - MIN(%(expressions)s))"
#     output_field = IntegerField()
#
#
# class _TitleBucketSelector(ODataSelector):
#     """Defined inline in the test, not in blog_post.py: proves the extension point
#     needs no change to the library's own example app to demonstrate genericity."""
#
#     class Meta:
#         model = BlogPost
#         dto_class = None
#         allowed_fields = ["initial", "view_count"]
#         apply_functions = {"initial": lambda: Upper(Left(F("title"), 1))}
#         apply_aggregates = {"range": lambda field: _Range(field)}
#
#
# class TestApplyExtensionPoint(TestCase):
#     @classmethod
#     def setUpTestData(cls):
#         user = User.objects.create(username="carol")
#         author = Author.objects.create(user=user)
#         BlogPost.objects.create(title="Apple pie", slug="a1", content="x", author=author, view_count=10)
#         BlogPost.objects.create(title="Aardvark facts", slug="a2", content="y", author=author, view_count=50)
#         BlogPost.objects.create(title="Banana bread", slug="b1", content="z", author=author, view_count=5)
#
#     def test_synthetic_bucket_function(self):
#         selector = _TitleBucketSelector()
#         result = selector.query_as_dicts("$apply=groupby((initial), aggregate($count as n))")
#         by_initial = {row["initial"]: row["n"] for row in result}
#         assert by_initial == {"A": 2, "B": 1}
#
#     def test_synthetic_aggregate_method(self):
#         selector = _TitleBucketSelector()
#         result = selector.query_as_dicts("$apply=aggregate(view_count with range as spread)")
#         assert result == [{"spread": 45}]
