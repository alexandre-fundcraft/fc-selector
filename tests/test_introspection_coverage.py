"""
Tests to improve coverage of fc_selector/django/utils/introspection.py.
"""

import pytest

from fc_selector.django.utils.introspection import (
    get_m2m_info,
    get_reverse_fk_info,
    is_m2m_relation,
)
from tests.integration.support.models import (
    ODataChildModel,
    ODataM2MTarget,
    ODataModelWithRelations,
    ODataSelfM2MModel,
)


@pytest.mark.django_db
class TestIntrospectionCoverage:
    """Coverage tests for introspection utilities."""

    def test_is_m2m_relation_forward(self):
        """Test is_m2m_relation with forward M2M."""
        assert is_m2m_relation(ODataModelWithRelations, "tags") is True

    def test_is_m2m_relation_reverse(self):
        """Test is_m2m_relation with reverse M2M."""
        assert is_m2m_relation(ODataM2MTarget, "tagged_items") is True

    def test_is_m2m_relation_false(self):
        """Test is_m2m_relation with regular field."""
        assert is_m2m_relation(ODataModelWithRelations, "title") is False

    def test_get_reverse_fk_info(self):
        """Test get_reverse_fk_info with reverse FK."""
        # ODataChildModel has parent FK to ODataModelWithRelations with related_name="children"
        info = get_reverse_fk_info(ODataModelWithRelations, "children")
        assert info is not None
        child_model, fk_attname = info
        assert child_model is ODataChildModel
        assert fk_attname == "parent_id"

    def test_get_reverse_fk_info_none(self):
        """Test get_reverse_fk_info with non-reverse FK field."""
        assert get_reverse_fk_info(ODataModelWithRelations, "title") is None
        # Forward FK is not reverse FK
        assert get_reverse_fk_info(ODataModelWithRelations, "target") is None

    def test_get_m2m_info_forward(self):
        """Test get_m2m_info with forward M2M."""
        info = get_m2m_info(ODataModelWithRelations, "tags")
        assert info is not None
        _through, related_model, source_fk, target_fk = info
        assert related_model is ODataM2MTarget
        assert source_fk and target_fk

    def test_get_m2m_info_reverse(self):
        """Test get_m2m_info with reverse M2M."""
        info = get_m2m_info(ODataM2MTarget, "tagged_items")
        assert info is not None
        _through, related_model, source_fk, target_fk = info
        assert related_model is ODataModelWithRelations
        assert source_fk and target_fk

    def test_get_m2m_info_self_referential(self):
        """Test get_m2m_info with self-referential M2M (hits _resolve_through_fks branch)."""
        info = get_m2m_info(ODataSelfM2MModel, "friends")
        assert info is not None
        _through, related_model, source_fk, target_fk = info
        assert related_model is ODataSelfM2MModel
        assert source_fk != target_fk

    def test_get_m2m_info_none(self):
        """Test get_m2m_info with non-M2M field."""
        assert get_m2m_info(ODataModelWithRelations, "title") is None
