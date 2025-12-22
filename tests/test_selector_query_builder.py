"""
Tests for ODataSelector with ODataQueryBuilder integration.

Tests the new API that encapsulates the persistence layer and only exposes OData operations.
"""

from dataclasses import dataclass

import pytest
from django.utils import timezone

from fc_selector.core.dtos import UNSET, BaseODataDTO
from fc_selector.core.query_builder import ODataQueryBuilder
from fc_selector.django.selector import ODataSelector
from tests.integration.support.models import ODataTestModel


@dataclass
class ODataRelatedDTO(BaseODataDTO):
    """Test DTO for ODataRelatedModel."""
    id: int = UNSET
    title: str = UNSET
    value: int = UNSET


@dataclass
class ODataTestDTO(BaseODataDTO):
    """Test DTO for ODataTestModel."""
    id: int = UNSET
    name: str = UNSET
    description: str = UNSET
    count: int = UNSET
    rating: float = UNSET
    is_active: bool = UNSET
    status: str = UNSET
    related_items: list[ODataRelatedDTO] | None = UNSET


class ODataTestSelector(ODataSelector):
    """Selector for testing with DTO support."""

    class Meta:
        model = ODataTestModel
        dto_class = ODataTestDTO
        expandable_fields = {
            "related_items": ODataRelatedDTO,
        }


@pytest.mark.django_db
class TestSelectorGetOne:
    """Tests for get_one method."""

    def test_get_one_by_id_filter(self):
        """Test getting a single DTO with id filter."""


        obj = ODataTestModel.objects.create(
            name="Test Object",
            count=10,
            created_at=timezone.now()
        )

        selector = ODataTestSelector()
        query = ODataQueryBuilder().and_filter(f"id eq {obj.id}")
        dto = selector.get_one(query)

        assert dto is not None
        assert dto.id == obj.id
        assert dto.name == "Test Object"

    def test_get_one_not_found(self):
        """Test get_one returns None when not found."""
        selector = ODataTestSelector()
        query = ODataQueryBuilder().and_filter("id eq 99999")
        dto = selector.get_one(query)

        assert dto is None

    def test_get_one_with_select(self):
        """Test get_one with field selection."""


        obj = ODataTestModel.objects.create(
            name="Test Object",
            description="Test Description",
            count=10,
            created_at=timezone.now()
        )

        selector = ODataTestSelector()
        query = ODataQueryBuilder().select("id", "name").and_filter(f"id eq {obj.id}")
        dto = selector.get_one(query)

        assert dto is not None
        assert dto.id == obj.id
        assert dto.name == "Test Object"
        assert dto.description is UNSET  # Not selected

    def test_get_one_from_query_string(self):
        """Test get_one parsing existing query string and adding filter."""


        obj = ODataTestModel.objects.create(
            name="Test Object",
            count=10,
            created_at=timezone.now()
        )

        selector = ODataTestSelector()
        query = ODataQueryBuilder.from_query_string("$select=id,name").and_filter(f"id eq {obj.id}")
        dto = selector.get_one(query)

        assert dto is not None
        assert dto.id == obj.id
        assert dto.name == "Test Object"


@pytest.mark.django_db
class TestSelectorGetMany:
    """Tests for get_many method."""

    def test_get_many_all(self):
        """Test getting all records as DTOs."""


        ODataTestModel.objects.create(name="Object 1", count=1, created_at=timezone.now())
        ODataTestModel.objects.create(name="Object 2", count=2, created_at=timezone.now())
        ODataTestModel.objects.create(name="Object 3", count=3, created_at=timezone.now())

        selector = ODataTestSelector()
        dtos = selector.get_many()

        assert len(dtos) == 3

    def test_get_many_with_filter(self):
        """Test get_many with OData filter."""


        ODataTestModel.objects.create(name="Active 1", is_active=True, count=1, created_at=timezone.now())
        ODataTestModel.objects.create(name="Active 2", is_active=True, count=2, created_at=timezone.now())
        ODataTestModel.objects.create(name="Inactive", is_active=False, count=3, created_at=timezone.now())

        selector = ODataTestSelector()
        query = ODataQueryBuilder().filter("is_active eq true")
        dtos = selector.get_many(query)

        assert len(dtos) == 2
        assert all(dto.is_active == True for dto in dtos)

    def test_get_many_with_top(self):
        """Test get_many with pagination."""


        for i in range(5):
            ODataTestModel.objects.create(name=f"Object {i}", count=i, created_at=timezone.now())

        selector = ODataTestSelector()
        query = ODataQueryBuilder().top(2)
        dtos = selector.get_many(query)

        assert len(dtos) == 2

    def test_get_many_with_select(self):
        """Test get_many with field selection."""


        ODataTestModel.objects.create(
            name="Test",
            description="Desc",
            count=10,
            created_at=timezone.now()
        )

        selector = ODataTestSelector()
        query = ODataQueryBuilder().select("id", "name")
        dtos = selector.get_many(query)

        assert len(dtos) == 1
        assert dtos[0].name == "Test"
        assert dtos[0].description is UNSET


@pytest.mark.django_db
class TestSelectorGetByPk:
    """Tests for get_by_pk convenience method."""

    def test_get_by_pk_found(self):
        """Test get_by_pk returns DTO when found."""


        obj = ODataTestModel.objects.create(
            name="Test Object",
            count=10,
            created_at=timezone.now()
        )

        selector = ODataTestSelector()
        dto = selector.get_by_pk(obj.id)

        assert dto is not None
        assert dto.id == obj.id
        assert dto.name == "Test Object"

    def test_get_by_pk_not_found(self):
        """Test get_by_pk returns None when not found."""
        selector = ODataTestSelector()
        dto = selector.get_by_pk(99999)

        assert dto is None

    def test_get_by_pk_with_query_builder(self):
        """Test get_by_pk with additional query options."""


        obj = ODataTestModel.objects.create(
            name="Test Object",
            description="Description",
            count=10,
            created_at=timezone.now()
        )

        selector = ODataTestSelector()
        query = ODataQueryBuilder().select("id", "name")
        dto = selector.get_by_pk(obj.id, query)

        assert dto is not None
        assert dto.id == obj.id
        assert dto.name == "Test Object"
        assert dto.description is UNSET  # Not selected


@pytest.mark.django_db
class TestSelectorCountBy:
    """Tests for count_by method."""

    def test_count_by_all(self):
        """Test counting all records."""


        ODataTestModel.objects.create(name="Object 1", count=1, created_at=timezone.now())
        ODataTestModel.objects.create(name="Object 2", count=2, created_at=timezone.now())

        selector = ODataTestSelector()
        count = selector.count_by()

        assert count == 2

    def test_count_by_with_filter(self):
        """Test counting with OData filter."""


        ODataTestModel.objects.create(name="Active", is_active=True, count=1, created_at=timezone.now())
        ODataTestModel.objects.create(name="Inactive", is_active=False, count=2, created_at=timezone.now())

        selector = ODataTestSelector()
        query = ODataQueryBuilder().filter("is_active eq true")
        count = selector.count_by(query)

        assert count == 1


@pytest.mark.django_db
class TestSelectorExistsBy:
    """Tests for exists_by method."""

    def test_exists_by_true(self):
        """Test exists_by returns True when records exist."""


        ODataTestModel.objects.create(name="Test", count=1, created_at=timezone.now())

        selector = ODataTestSelector()
        exists = selector.exists_by()

        assert exists == True

    def test_exists_by_false(self):
        """Test exists_by returns False when no records exist."""
        selector = ODataTestSelector()
        query = ODataQueryBuilder().filter("name eq 'nonexistent'")
        exists = selector.exists_by(query)

        assert exists == False

    def test_exists_by_with_filter(self):
        """Test exists_by with OData filter."""


        ODataTestModel.objects.create(name="Active", is_active=True, count=1, created_at=timezone.now())

        selector = ODataTestSelector()

        query_active = ODataQueryBuilder().filter("is_active eq true")
        assert selector.exists_by(query_active) == True

        query_inactive = ODataQueryBuilder().filter("is_active eq false")
        assert selector.exists_by(query_inactive) == False


@pytest.mark.django_db
class TestSelectorODataQueryIntegration:
    """Integration tests for complete OData query flows."""

    def test_complex_query_flow(self):
        """Test a complete query flow with multiple OData operations."""


        # Create test data
        for i in range(10):
            ODataTestModel.objects.create(
                name=f"Object {i}",
                description=f"Description {i}",
                count=i,
                is_active=i % 2 == 0,
                status="published" if i < 5 else "draft",
                created_at=timezone.now()
            )

        selector = ODataTestSelector()

        # Complex query: published, active, select specific fields, limit to 3
        query = (
            ODataQueryBuilder()
            .filter("status eq 'published'")
            .and_filter("is_active eq true")
            .select("id", "name", "status")
            .top(3)
        )

        dtos = selector.get_many(query)

        assert len(dtos) <= 3
        for dto in dtos:
            assert dto.status == "published"
            # is_active not selected, so it's UNSET (but filter was applied)
            assert dto.is_active is UNSET
            assert dto.description is UNSET  # Not selected

    def test_from_request_query_string_pattern(self):
        """Test the pattern of parsing request query string and adding filters."""


        obj = ODataTestModel.objects.create(
            name="Target Object",
            count=100,
            created_at=timezone.now()
        )
        ODataTestModel.objects.create(name="Other Object", count=50, created_at=timezone.now())

        selector = ODataTestSelector()

        # Simulate: query_string comes from request, then we add id filter
        request_query_string = "$select=id,name,count"
        query = ODataQueryBuilder.from_query_string(request_query_string).and_filter(f"id eq {obj.id}")

        dto = selector.get_one(query)

        assert dto is not None
        assert dto.id == obj.id
        assert dto.name == "Target Object"
        assert dto.count == 100
        assert dto.description is UNSET  # Not in $select
