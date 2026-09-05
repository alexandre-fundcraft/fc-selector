"""End-to-end check that field aliases still resolve after the regex pre-pass removal."""

import pytest
from django.utils import timezone

from fc_selector.django.selector import ODataSelector
from tests.integration.support.models import ODataTestModel


class AliasedSelector(ODataSelector):
    class Meta:
        model = ODataTestModel
        field_aliases = {"title": "name", "qty": "count"}


@pytest.mark.django_db
class TestAliasEndToEnd:
    def test_filter_by_alias(self):
        ODataTestModel.objects.create(created_at=timezone.now(), name="alpha", count=1)
        ODataTestModel.objects.create(created_at=timezone.now(), name="beta", count=2)

        rows = AliasedSelector().query("$filter=title eq 'alpha'")
        assert [r.name for r in rows] == ["alpha"]

    def test_orderby_alias(self):
        ODataTestModel.objects.create(created_at=timezone.now(), name="b", count=1)
        ODataTestModel.objects.create(created_at=timezone.now(), name="a", count=2)

        rows = AliasedSelector().query("$orderby=title asc")
        assert [r.name for r in rows] == ["a", "b"]

    def test_select_alias(self):
        ODataTestModel.objects.create(created_at=timezone.now(), name="alpha", count=7)
        rows = AliasedSelector().query_as_dicts("$select=title,qty")
        assert rows[0]["name"] == "alpha"
        assert rows[0]["count"] == 7

    def test_filter_alias_does_not_touch_string_literals(self):
        ODataTestModel.objects.create(created_at=timezone.now(), name="title", count=1)
        rows = AliasedSelector().query("$filter=title eq 'title'")
        assert [r.name for r in rows] == ["title"]
