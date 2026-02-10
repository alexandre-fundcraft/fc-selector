"""
Tests for DRF Spectacular integration.
"""

from rest_framework.viewsets import ViewSet

from fc_selector.django.drf.spectacular import (
    ODATA_PARAMETERS,
    get_odata_parameters,
    get_odata_schema_extension,
    postprocess_odata_schema,
    preprocess_odata_parameters,
)
from fc_selector.django.drf.viewsets.selector_mixin import ODataSelectorViewSetMixin


class MockODataViewSet(ODataSelectorViewSetMixin, ViewSet):
    pass


class MockNormalViewSet(ViewSet):
    pass


def test_preprocess_odata_parameters():
    """Test preprocess hook marks callbacks."""

    # Mock endpoints structure: (path, regex, method, callback)
    # Callback usually has .cls attribute pointing to ViewSet

    def callback_odata():
        pass

    callback_odata.cls = MockODataViewSet

    def callback_normal():
        pass

    callback_normal.cls = MockNormalViewSet

    endpoints = [
        ("/odata", "regex", "GET", callback_odata),
        ("/normal", "regex", "GET", callback_normal),
    ]

    preprocess_odata_parameters(endpoints)

    assert hasattr(callback_odata, "_odata_params_added")
    assert callback_odata._odata_params_added is True

    assert not hasattr(callback_normal, "_odata_params_added")


def test_postprocess_odata_schema_list():
    """Test postprocess hook adds parameters to list endpoint."""

    result = {"paths": {"/odata/": {"get": {"operationId": "odata_list", "tags": ["odata"], "parameters": []}}}}

    # It modifies result in place
    postprocess_odata_schema(result, generator=None, request=None, public=True)

    params = result["paths"]["/odata/"]["get"]["parameters"]
    param_names = [p["name"] for p in params]

    assert "$filter" in param_names
    assert "$select" in param_names
    assert "$expand" in param_names
    assert "$orderby" in param_names
    assert "$top" in param_names
    assert "$skip" in param_names
    assert "$count" in param_names


def test_postprocess_odata_schema_retrieve():
    """Test postprocess hook adds parameters to retrieve endpoint."""

    result = {
        "paths": {"/odata/{id}/": {"get": {"operationId": "odata_retrieve", "tags": ["odata"], "parameters": []}}}
    }

    postprocess_odata_schema(result, generator=None, request=None, public=True)

    params = result["paths"]["/odata/{id}/"]["get"]["parameters"]
    param_names = [p["name"] for p in params]

    # Retrieve should only have select and expand
    assert "$select" in param_names
    assert "$expand" in param_names
    assert "$filter" not in param_names
    assert "$top" not in param_names


def test_postprocess_odata_schema_existing_params():
    """Test postprocess hook respects existing parameters."""

    result = {
        "paths": {
            "/odata/": {
                "get": {
                    "operationId": "odata_list",
                    "parameters": [{"name": "$top", "in": "query", "description": "existing"}],
                }
            }
        }
    }

    postprocess_odata_schema(result, generator=None, request=None, public=True)

    params = result["paths"]["/odata/"]["get"]["parameters"]
    # Check that we didn't duplicate $top
    top_params = [p for p in params if p["name"] == "$top"]
    assert len(top_params) == 1
    assert top_params[0]["description"] == "existing"


def test_get_odata_schema_extension():
    """Test get_odata_schema_extension returns the callback."""
    assert get_odata_schema_extension() == preprocess_odata_parameters


def test_get_odata_parameters():
    """Test get_odata_parameters returns the list."""
    assert get_odata_parameters() == ODATA_PARAMETERS
