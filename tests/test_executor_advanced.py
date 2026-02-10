"""
Advanced tests for Django executor module.
"""

import pytest
from django.utils import timezone

from fc_selector.core.intent import ExpandIntent, QueryIntent
from fc_selector.django.executor import DjangoExecutor
from tests.integration.support.models import (
    ODataOneToOneChild,
    ODataOneToOneParent,
    ODataRelatedModel,
    ODataRootModel,
    ODataSimpleParent,
    ODataSimpleRoot,
    ODataTestModel,
)


@pytest.fixture
def one_to_one_setup(db):
    """Setup data for OneToOne testing."""
    child = ODataOneToOneChild.objects.create(name="Child")
    parent = ODataOneToOneParent.objects.create(child=child, description="Parent")
    root = ODataRootModel.objects.create(parent=parent)
    return root


@pytest.mark.django_db
class TestExecutorOptimization:
    """Tests for executor optimization logic."""

    def test_expand_introspected_dto_with_onetoone(self, db, django_assert_num_queries):
        """Test introspection resolving OneToOne fields."""
        child = ODataOneToOneChild.objects.create(name="Child")
        parent = ODataSimpleParent.objects.create(child=child, description="Parent")
        ODataSimpleRoot.objects.create(parent=parent)

        class SimpleParentDTO:
            description: str
            name: str  # Should resolve to child.name via OneToOne

        expandable_fields = {"parent": SimpleParentDTO}

        executor = DjangoExecutor(expandable_fields=expandable_fields)
        intent = QueryIntent(expand=ExpandIntent(relations={"parent": QueryIntent()}))

        qs = ODataSimpleRoot.objects.all()

        # Execute query
        with django_assert_num_queries(1):
            result = list(executor.execute(qs, intent))

        item = result[0]
        # Verify description loaded
        assert item.parent.description == "Parent"

        # Accessing child.name should NOT trigger query because it was auto-selected
        # via DTO introspection -> child__name
        with django_assert_num_queries(0):
            assert item.parent.child.name == "Child"

    def test_expand_with_property_and_onetoone(self, one_to_one_setup, django_assert_num_queries):
        """


        Test expanding a relation where the target model has a @property.


        Should skip only() for that relation and auto-select OneToOne fields.


        """

        expandable_fields = {
            "parent": ODataOneToOneParent,  # Triggers introspection but property overrides
        }

        executor = DjangoExecutor(expandable_fields=expandable_fields)

        intent = QueryIntent(expand=ExpandIntent(relations={"parent": QueryIntent()}))

        qs = ODataRootModel.objects.all()

        # Execute query

        with django_assert_num_queries(1):
            result = list(executor.execute(qs, intent))

        assert len(result) == 1

        item = result[0]

        # Accessing related property should NOT trigger extra queries

        # because OneToOneField 'child' should have been selected

        with django_assert_num_queries(0):
            assert item.parent.full_desc == "Child: Parent"

    def test_expand_explicit_only_fields_no_property(self, django_assert_num_queries):
        """Test explicit only_fields on a model without properties."""

        now = timezone.now()

        parent = ODataTestModel.objects.create(name="Parent", count=10, created_at=now, status="draft")

        ODataRelatedModel.objects.create(test_model=parent, title="Child", value=1)

        # Expand test_model from ODataRelatedModel, only asking for 'name'

        expandable_fields = {"test_model": {"only_fields": ["name"]}}

        executor = DjangoExecutor(expandable_fields=expandable_fields)

        intent = QueryIntent(expand=ExpandIntent(relations={"test_model": QueryIntent()}))

        qs = ODataRelatedModel.objects.all()

        with django_assert_num_queries(1):
            result = list(executor.execute(qs, intent))

        item = result[0]

        assert item.test_model.name == "Parent"

        # Accessing 'count' (not in only_fields) SHOULD trigger a query

        # Because only('name', 'id') was used

        with django_assert_num_queries(1):
            _ = item.test_model.count

    def test_expand_introspected_dto(self, django_assert_num_queries):
        """Test expanding with DTO introspection."""

        now = timezone.now()

        parent = ODataTestModel.objects.create(name="Parent", count=5, created_at=now, status="draft")

        ODataRelatedModel.objects.create(test_model=parent, title="Child", value=1)

        class ParentDTO:
            name: str

            # count not included

        expandable_fields = {"test_model": ParentDTO}

        executor = DjangoExecutor(expandable_fields=expandable_fields)

        intent = QueryIntent(expand=ExpandIntent(relations={"test_model": QueryIntent()}))

        qs = ODataRelatedModel.objects.all()

        with django_assert_num_queries(1):
            result = list(executor.execute(qs, intent))

        item = result[0]

        assert item.test_model.name == "Parent"

        # Count should be deferred as it wasn't in DTO

        with django_assert_num_queries(1):
            _ = item.test_model.count
