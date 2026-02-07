"""
Functional E2E Tests for OData Endpoints.

Tests various OData query options to ensure correct data retrieval.
"""

import pytest


@pytest.mark.django_db
class TestODataFunctional:
    def test_filter_equality(self, api_client, scenario_data):
        """Test $filter=status eq 'published'."""
        response = api_client.get("/api/posts/?$filter=status eq 'published'")
        assert response.status_code == 200
        data = response.json()["value"]

        # Alice (5) + Charlie (5) = 10
        assert len(data) == 10
        assert all(item["status"] == "published" for item in data)

    def test_select_fields(self, api_client, scenario_data):
        """Test $select=id,title."""
        response = api_client.get("/api/posts/?$select=id,title")
        assert response.status_code == 200
        data = response.json()["value"]

        item = data[0]
        assert "id" in item
        assert "title" in item
        assert "content" not in item  # UNSET field should be omitted
        assert "status" not in item

    def test_expand_relation(self, api_client, scenario_data):
        """Test $expand=author."""
        response = api_client.get("/api/posts/?$expand=author&$top=1")
        assert response.status_code == 200
        data = response.json()["value"][0]

        assert "author" in data
        assert isinstance(data["author"], dict)
        assert "name" in data["author"]

    def test_nested_select_in_expand(self, api_client, scenario_data):
        """Test $expand=author($select=name)."""
        response = api_client.get("/api/posts/?$expand=author($select=name)")
        assert response.status_code == 200
        data = response.json()["value"][0]

        author = data["author"]
        assert "name" in author
        assert "bio" not in author  # Should be excluded by nested select

    def test_orderby_desc(self, api_client, scenario_data):
        """Test $orderby=view_count desc."""
        response = api_client.get("/api/posts/?$orderby=view_count desc")
        assert response.status_code == 200
        data = response.json()["value"]

        # Convert to int because DTO might return string for integers
        counts = [int(item["view_count"]) for item in data]
        # Verify descending order
        assert counts == sorted(counts, reverse=True)

    def test_pagination_top_skip(self, api_client, scenario_data):
        """Test $top=5&$skip=5."""
        # Total 15 posts.
        # Skip 5 (Alice's), Take 5 (Bob's)
        # Assuming default ordering is usually ID or created_at, let's force strict ordering
        response = api_client.get("/api/posts/?$orderby=id asc&$top=5&$skip=5")
        assert response.status_code == 200
        data = response.json()["value"]

        assert len(data) == 5
        # Scenario creates Alice(1..5), Bob(6..10), Charlie(11..15)
        # So we expect Bob's posts
        assert "Bob" in data[0]["title"]

    def test_count_total(self, api_client, scenario_data):
        """Test $count=true."""
        # Filter down to 5 records but skip 2. Total should still be 5.
        # Use explicit path to DB field (user/username) not property (name)
        response = api_client.get("/api/posts/?$filter=author/user/username eq 'bob'&$top=1&$count=true")
        assert response.status_code == 200
        data = response.json()

        assert "@odata.count" in data
        assert data["@odata.count"] == 5  # Bob has 5 posts total
        assert len(data["value"]) == 1  # But we only fetched 1

    def test_complex_combination(self, api_client, scenario_data):
        """Test Filter + Expand + Select + Order + Top."""
        # Get top 3 most viewed published posts, show title and author name
        url = (
            "/api/posts/?"
            "$filter=status eq 'published'&"
            "$orderby=view_count desc&"
            "$select=title,view_count&"
            "$expand=author($select=name)&"
            "$top=3"
        )
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.json()["value"]

        assert len(data) == 3
        first = data[0]

        # Check structure
        assert "title" in first
        assert "view_count" in first
        assert "content" not in first
        assert "author" in first
        assert "name" in first["author"]
        assert "bio" not in first["author"]

        # Check logic: Highest views are Charlie's (500*6=3000 approx)
        # Username 'charlie' is lower case in fixture
        assert "charlie" in first["author"]["name"].lower()


@pytest.mark.django_db
class TestODataStringFunctions:
    """Tests for OData string functions."""

    def test_filter_contains(self, api_client, scenario_data):
        """Test $filter=contains(title, 'Tech')."""
        response = api_client.get("/api/posts/?$filter=contains(title, 'Tech')")
        assert response.status_code == 200
        data = response.json()["value"]

        # Alice has 5 Tech posts
        assert len(data) == 5
        assert all("Tech" in item["title"] for item in data)

    def test_filter_startswith(self, api_client, scenario_data):
        """Test $filter=startswith(title, 'Alice')."""
        response = api_client.get("/api/posts/?$filter=startswith(title, 'Alice')")
        assert response.status_code == 200
        data = response.json()["value"]

        # Alice has 5 posts starting with 'Alice'
        assert len(data) == 5
        assert all(item["title"].startswith("Alice") for item in data)

    def test_filter_endswith(self, api_client, scenario_data):
        """Test $filter=endswith(title, '1')."""
        response = api_client.get("/api/posts/?$filter=endswith(title, '1')")
        assert response.status_code == 200
        data = response.json()["value"]

        # Each author has 1 post ending with '1' (Post 1)
        assert len(data) == 3
        assert all(item["title"].endswith("1") for item in data)


@pytest.mark.django_db
class TestODataLogicalOperators:
    """Tests for OData logical operators."""

    def test_filter_and(self, api_client, scenario_data):
        """Test $filter with AND operator."""
        response = api_client.get("/api/posts/?$filter=status eq 'published' and featured eq true")
        assert response.status_code == 200
        data = response.json()["value"]

        # Only Charlie's posts are published AND featured
        assert len(data) == 5
        assert all(item["status"] == "published" for item in data)
        assert all(item["featured"] is True for item in data)

    def test_filter_or(self, api_client, scenario_data):
        """Test $filter with OR operator."""
        response = api_client.get("/api/posts/?$filter=status eq 'draft' or featured eq true")
        assert response.status_code == 200
        data = response.json()["value"]

        # Bob's drafts (5) + Charlie's featured (5) = 10
        assert len(data) == 10
        for item in data:
            assert item["status"] == "draft" or item["featured"] is True

    def test_filter_not(self, api_client, scenario_data):
        """Test $filter with NOT operator."""
        response = api_client.get("/api/posts/?$filter=not (status eq 'published')")
        assert response.status_code == 200
        data = response.json()["value"]

        # Only Bob's drafts (5)
        assert len(data) == 5
        assert all(item["status"] != "published" for item in data)

    def test_filter_complex_logical(self, api_client, scenario_data):
        """Test $filter with complex logical expression."""
        # (published AND high views) OR featured
        response = api_client.get(
            "/api/posts/?$filter=(status eq 'published' and view_count gt 400) or featured eq true"
        )
        assert response.status_code == 200
        data = response.json()["value"]

        for item in data:
            view_count = int(item["view_count"]) if isinstance(item["view_count"], str) else item["view_count"]
            high_views_published = item["status"] == "published" and view_count > 400
            is_featured = item["featured"] is True
            assert high_views_published or is_featured


@pytest.mark.django_db
class TestODataNestedFilters:
    """Tests for OData filters on nested/related fields."""

    def test_filter_nested_relation(self, api_client, scenario_data):
        """Test $filter on nested relation field."""
        response = api_client.get("/api/posts/?$filter=author/user/username eq 'alice'")
        assert response.status_code == 200
        data = response.json()["value"]

        # Alice has 5 posts
        assert len(data) == 5

    def test_filter_nested_with_contains(self, api_client, scenario_data):
        """Test $filter with contains on direct field."""
        response = api_client.get("/api/posts/?$filter=contains(content, 'life')")
        assert response.status_code == 200
        data = response.json()["value"]

        # Bob has 5 posts with 'life' in content
        assert len(data) == 5


@pytest.mark.django_db
class TestODataMultipleOrderBy:
    """Tests for OData $orderby with multiple fields."""

    def test_orderby_multiple_fields(self, api_client, scenario_data):
        """Test $orderby with multiple fields."""
        response = api_client.get("/api/posts/?$orderby=status asc,view_count desc")
        assert response.status_code == 200
        data = response.json()["value"]

        # Should be ordered by status first (draft < published), then view_count desc
        # Draft posts should come first
        draft_posts = [p for p in data if p["status"] == "draft"]
        published_posts = [p for p in data if p["status"] == "published"]

        # All drafts before all published
        draft_indices = [data.index(p) for p in draft_posts]
        published_indices = [data.index(p) for p in published_posts]
        assert max(draft_indices) < min(published_indices)

        # Within each group, view_count should be descending
        draft_views = [p["view_count"] for p in draft_posts]
        assert draft_views == sorted(draft_views, reverse=True)

    def test_orderby_asc_and_desc_mixed(self, api_client, scenario_data):
        """Test $orderby with mixed asc/desc."""
        response = api_client.get("/api/posts/?$orderby=featured desc,id asc&$top=10")
        assert response.status_code == 200
        data = response.json()["value"]

        # Featured posts should come first
        featured_posts = [p for p in data if p["featured"] is True]
        non_featured_posts = [p for p in data if p["featured"] is not True]

        if featured_posts and non_featured_posts:
            featured_indices = [data.index(p) for p in featured_posts]
            non_featured_indices = [data.index(p) for p in non_featured_posts]
            assert max(featured_indices) < min(non_featured_indices)


@pytest.mark.django_db
class TestODataComparisons:
    """Tests for OData comparison operators."""

    def test_filter_greater_than(self, api_client, scenario_data):
        """Test $filter with gt (greater than)."""
        response = api_client.get("/api/posts/?$filter=view_count gt 200")
        assert response.status_code == 200
        data = response.json()["value"]

        assert all(int(item["view_count"]) > 200 for item in data)

    def test_filter_greater_than_or_equal(self, api_client, scenario_data):
        """Test $filter with ge (greater than or equal)."""
        response = api_client.get("/api/posts/?$filter=rating ge 4.5")
        assert response.status_code == 200
        data = response.json()["value"]

        # Alice (4.5) + Charlie (5.0) = 10 posts
        assert len(data) == 10
        assert all(float(item["rating"]) >= 4.5 for item in data)

    def test_filter_less_than(self, api_client, scenario_data):
        """Test $filter with lt (less than)."""
        response = api_client.get("/api/posts/?$filter=view_count lt 100")
        assert response.status_code == 200
        data = response.json()["value"]

        # Bob's posts with view_count 10, 20, 30, 40, 50 (5 posts)
        assert all(int(item["view_count"]) < 100 for item in data)

    def test_filter_less_than_or_equal(self, api_client, scenario_data):
        """Test $filter with le (less than or equal)."""
        response = api_client.get("/api/posts/?$filter=rating le 3.0")
        assert response.status_code == 200
        data = response.json()["value"]

        # Only Bob has rating 3.0
        assert len(data) == 5
        assert all(float(item["rating"]) <= 3.0 for item in data)

    def test_filter_not_equal(self, api_client, scenario_data):
        """Test $filter with ne (not equal)."""
        response = api_client.get("/api/posts/?$filter=status ne 'draft'")
        assert response.status_code == 200
        data = response.json()["value"]

        # Alice (5) + Charlie (5) = 10 published posts
        assert len(data) == 10
        assert all(item["status"] != "draft" for item in data)


@pytest.mark.django_db
class TestODataErrorCases:
    """Tests for OData error handling."""

    def test_invalid_field_in_filter(self, api_client, scenario_data):
        """Test $filter with non-existent field returns error."""
        response = api_client.get("/api/posts/?$filter=nonexistent_field eq 'value'")
        # Should return 400 Bad Request
        assert response.status_code == 400

    def test_invalid_top_value(self, api_client, scenario_data):
        """Test $top with invalid value returns error."""
        response = api_client.get("/api/posts/?$top=invalid")
        assert response.status_code == 400

    def test_negative_skip_value(self, api_client, scenario_data):
        """Test $skip with negative value returns error."""
        response = api_client.get("/api/posts/?$skip=-5")
        assert response.status_code == 400
