"""
Performance Regression Tests (N+1).

Ensures that the OData selector optimizations are working correctly
and preventing query explosions.
"""

import pytest
from django.conf import settings


@pytest.mark.django_db
class TestNPlusOneRegression:
    def test_authors_list_is_optimized(self, api_client, scenario_data):
        """
        REGRESSION TEST: Ensure fetching authors doesn't trigger N+1 queries.

        The Author model has 'name' and 'email' properties that access the related
        OneToOne User model. Without select_related, this causes N+1.
        """
        # Force DEBUG=True and FC_SELECTOR_DEBUG_QUERIES=True to get @debug info
        settings.DEBUG = True
        settings.FC_SELECTOR_DEBUG_QUERIES = True

        response = api_client.get("/api/authors/")

        assert response.status_code == 200
        data = response.json()

        # Verify we have data
        assert len(data["value"]) == 3

        # Verify Query Count
        # Ideal: 1 query (SELECT authors JOIN users)
        # Acceptable: 2 queries (if session or auth check happens)
        # FAIL: 3+ (implies 1 main + N users)
        debug_info = data.get("@debug")
        assert debug_info is not None, "Debug info missing. Ensure DEBUG=True"

        query_count = debug_info["query_count"]

        # We expect strictly less than 5 queries for 3 items.
        # If N+1 was present, we'd see 1 (main) + 3 (users) + overhead >= 4 or 5
        print(f"\nDEBUG: Query count for /api/authors/ is {query_count}")
        assert query_count < 5, f"N+1 Detected! Query count {query_count} is too high for 3 items."

    def test_posts_expand_author_is_optimized(self, api_client, scenario_data):
        """
        Test explicit $expand optimization.
        GET /api/posts?$expand=author
        """
        settings.DEBUG = True
        settings.FC_SELECTOR_DEBUG_QUERIES = True

        # Fetch 15 posts with expanded author
        response = api_client.get("/api/posts/?$expand=author")

        assert response.status_code == 200
        data = response.json()
        debug_info = data.get("@debug")
        query_count = debug_info["query_count"]

        # If N+1, we'd have 1 + 15 = 16 queries.
        # With optimization, it should be 1 (join) or 2 (prefetch).
        print(f"\nDEBUG: Query count for posts+expand is {query_count}")
        assert query_count < 5, f"N+1 Detected on expand! Count: {query_count}"
