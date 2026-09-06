"""
Performance Regression Tests (N+1).

Ensures that the OData selector optimizations are working correctly
and preventing query explosions.

Query counting uses pytest-django's ``django_assert_max_num_queries`` fixture.
"""

import pytest


@pytest.mark.django_db
class TestNPlusOneRegression:
    def test_authors_list_is_optimized(self, api_client, scenario_data, django_assert_max_num_queries):
        """
        REGRESSION TEST: Ensure fetching authors doesn't trigger N+1 queries.

        The Author model has 'name' and 'email' properties that access the related
        OneToOne User model. Without select_related, this causes N+1.

        Ideal is 1 query (SELECT authors JOIN users). If N+1 were present we would
        see 1 (main) + 3 (users) + overhead, so anything under 5 is acceptable.
        """
        with django_assert_max_num_queries(4):
            response = api_client.get("/api/authors/")

        assert response.status_code == 200
        assert len(response.json()["value"]) == 3

    def test_posts_expand_author_is_optimized(self, api_client, scenario_data, django_assert_max_num_queries):
        """
        Test explicit $expand optimization.
        GET /api/posts?$expand=author

        With N+1 we would see 1 + 15 = 16 queries for 15 posts.
        With optimization it should be 1 (join) or 2 (prefetch).
        """
        with django_assert_max_num_queries(4):
            response = api_client.get("/api/posts/?$expand=author")

        assert response.status_code == 200
