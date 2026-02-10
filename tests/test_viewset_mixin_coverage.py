"""
Targeted tests to reach 100% coverage in fc_selector/django/drf/viewsets/selector_mixin.py
"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory, override_settings

from fc_selector.core import exceptions as core_ex
from fc_selector.django.drf.viewsets.selector_mixin import (
    ODataSelectorViewSetMixin,
    build_odata_response,
    get_odata_openapi_parameters,
)


@pytest.mark.django_db
class TestSelectorMixinCoverage:
    """Targeted tests for selector_mixin.py."""

    def test_build_odata_response_with_total_count(self):
        """Build response with explicit total_count."""
        rf = RequestFactory()
        request = rf.get("/odata/posts/")
        data = [{"id": 1}]
        response = build_odata_response(request, data, "$count=true", "posts", total_count=100)
        assert response["@odata.count"] == 100

    def test_build_odata_response_with_selector_count(self):
        """Build response where count is fetched via selector."""
        rf = RequestFactory()
        request = rf.get("/odata/posts/")
        data = [{"id": 1}]
        selector = MagicMock()
        selector.query.return_value.count.return_value = 42

        response = build_odata_response(request, data, "$count=true&$top=10", "posts", selector=selector)
        assert response["@odata.count"] == 42
        # Verify pagination params were stripped for count query
        selector.query.assert_called_once()
        called_qs = selector.query.call_args[0][0]
        assert "$top" not in called_qs
        assert "$count" not in called_qs

    def test_build_odata_response_pagination_bounds(self):
        """Test pagination parameter capping and validation."""
        rf = RequestFactory()
        request = rf.get("/odata/posts/")
        data = [{"id": i} for i in range(50)]

        # Test capping and negative values
        response = build_odata_response(request, data, "$top=9999999&$skip=-10", "posts")
        # skip becomes max(-10, 0) = 0
        # top becomes min(9999999, 10000) = 10000
        # Since len(data) == 50 and top == 10000, no nextLink
        assert "@odata.nextLink" not in response

        # Test nextLink generation
        response = build_odata_response(request, data, "$top=50&$skip=0", "posts")
        assert "@odata.nextLink" in response
        assert "$skip=50" in response["@odata.nextLink"]

    def test_build_odata_response_malformed_pagination(self):
        """Handle non-integer pagination values."""
        rf = RequestFactory()
        request = rf.get("/odata/posts/")
        response = build_odata_response(request, [], "$top=abc&$skip=def", "posts")
        assert response["value"] == []

    @override_settings(FC_SELECTOR_DEBUG_QUERIES=True, DEBUG=True)
    def test_build_odata_response_debug_queries(self):
        """Test debug queries inclusion."""
        rf = RequestFactory()
        request = rf.get("/odata/posts/")

        mock_conn = MagicMock()
        mock_conn.queries = [{"sql": "SELECT 1", "time": "0.001"}]
        with patch("fc_selector.django.drf.viewsets.selector_mixin.connection", mock_conn):
            response = build_odata_response(request, [], "", "posts")
            assert "@debug" in response
            assert response["@debug"]["query_count"] == 1

    @override_settings(FC_SELECTOR_DEBUG_QUERIES=True, DEBUG=True)
    def test_build_odata_response_debug_queries_truncated(self):
        """Test SQL truncation in debug info."""
        rf = RequestFactory()
        request = rf.get("/odata/posts/")
        long_sql = "SELECT " + ("x" * 1000)

        mock_conn = MagicMock()
        mock_conn.queries = [{"sql": long_sql, "time": "0.001"}]
        with patch("fc_selector.django.drf.viewsets.selector_mixin.connection", mock_conn):
            response = build_odata_response(request, [], "", "posts")
            assert "... [truncated]" in response["@debug"]["queries"][0]["sql"]

    @override_settings(FC_SELECTOR_DEBUG_QUERIES=True, DEBUG=False)
    def test_build_odata_response_debug_queries_no_debug_mode(self):
        """Warning when debug queries enabled but DEBUG is False."""
        rf = RequestFactory()
        request = rf.get("/odata/posts/")

        with pytest.warns(UserWarning, match="is enabled but DEBUG is False"):
            response = build_odata_response(request, [], "", "posts")
            assert "@debug" not in response

    def test_viewset_mixin_get_selector_errors(self):
        """get_selector error cases."""

        class BadViewSet(ODataSelectorViewSetMixin):
            pass

        with pytest.raises(NotImplementedError):
            BadViewSet().get_selector()

        class NotCallableViewSet(ODataSelectorViewSetMixin):
            selector_class = "not a class"

        with pytest.raises(TypeError):
            NotCallableViewSet().get_selector()

    @patch("fc_selector.django.drf.viewsets.selector_mixin.HAS_SPECTACULAR", False)
    def test_get_odata_openapi_parameters_no_spectacular(self):
        """Return empty list when spectacular is missing."""
        assert get_odata_openapi_parameters() == []

    @patch("fc_selector.django.drf.viewsets.selector_mixin.HAS_SPECTACULAR", True)
    def test_get_odata_openapi_parameters_with_spectacular(self):
        """Return parameter list when spectacular is present."""
        with patch("fc_selector.django.drf.viewsets.selector_mixin.OpenApiParameter") as mock_param:
            params = get_odata_openapi_parameters()
            assert len(params) > 0
            assert mock_param.called

    def test_mixin_list_error_handling(self):
        """Coverage for exception mapping in list()."""
        rf = RequestFactory()
        request = rf.get("/odata/posts/")

        mock_selector = MagicMock()

        class TestViewSet(ODataSelectorViewSetMixin):
            def selector_class(x):
                return mock_selector
            odata_entity_set_name = "posts"

            def get_serializer(self, *args, **kwargs):
                return MagicMock(data=[])

        viewset = TestViewSet()

        # Test InvalidFieldError
        mock_selector.query_as_dtos.side_effect = core_ex.InvalidFieldError("field", "Model")
        with pytest.raises(Exception):  # ODataFieldNotFoundError
            viewset.list(request)

        # Test InvalidValueError
        mock_selector.query_as_dtos.side_effect = core_ex.InvalidValueError("val", "int", "$top")
        with pytest.raises(Exception):  # ODataInvalidPaginationError
            viewset.list(request)

        # Test QueryError
        mock_selector.query_as_dtos.side_effect = core_ex.QueryError("error")
        with pytest.raises(Exception):  # ODataFilterError
            viewset.list(request)

    def test_mixin_retrieve_not_found(self):
        """Return 404 when get_one returns None."""
        rf = RequestFactory()
        request = rf.get("/odata/posts/1/")

        mock_selector = MagicMock()
        mock_selector.get_one.return_value = None

        class TestViewSet(ODataSelectorViewSetMixin):
            def selector_class(x):
                return mock_selector
            odata_entity_set_name = "posts"

        viewset = TestViewSet()
        response = viewset.retrieve(request, pk=1)
        assert response.status_code == 404

    def test_mixin_retrieve_error_handling(self):
        """Coverage for exception mapping in retrieve()."""
        rf = RequestFactory()
        request = rf.get("/odata/posts/1/")

        mock_selector = MagicMock()

        class TestViewSet(ODataSelectorViewSetMixin):
            def selector_class(x):
                return mock_selector
            odata_entity_set_name = "posts"

        viewset = TestViewSet()

        # Test InvalidFieldError
        mock_selector.get_one.side_effect = core_ex.InvalidFieldError("field", "Model")
        with pytest.raises(Exception):
            viewset.retrieve(request, pk=1)

        # Test InvalidValueError
        mock_selector.get_one.side_effect = core_ex.InvalidValueError("val", "int", "$top")
        with pytest.raises(Exception):
            viewset.retrieve(request, pk=1)

        # Test QueryError
        mock_selector.get_one.side_effect = core_ex.QueryError("error")
        with pytest.raises(Exception):
            viewset.retrieve(request, pk=1)

    def test_schema_decorators(self):
        """Coverage for schema decorator methods."""

        class TestViewSet(ODataSelectorViewSetMixin):
            pass

        assert callable(TestViewSet.get_list_schema_decorator())
        assert callable(TestViewSet.get_retrieve_schema_decorator())
