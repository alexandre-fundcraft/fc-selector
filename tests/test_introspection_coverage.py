"""
Tests to improve coverage of fc_selector/django/utils/introspection.py.
"""
import pytest

from fc_selector.core.exceptions import InvalidFieldError
from fc_selector.django.utils.introspection import (
    get_m2m_info,
    get_reverse_fk_info,
    is_m2m_relation,
    validate_field_name,
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
        assert info["related_model"] is ODataM2MTarget
        assert "target_fk_attname" in info
        assert "source_fk_attname" in info

    def test_get_m2m_info_reverse(self):
        """Test get_m2m_info with reverse M2M."""
        info = get_m2m_info(ODataM2MTarget, "tagged_items")
        assert info is not None
        assert info["related_model"] is ODataModelWithRelations
        assert "target_fk_attname" in info
        assert "source_fk_attname" in info

    def test_get_m2m_info_self_referential(self):
        """Test get_m2m_info with self-referential M2M (hits _resolve_through_fks branch)."""
        info = get_m2m_info(ODataSelfM2MModel, "friends")
        assert info is not None
        assert info["related_model"] is ODataSelfM2MModel
        assert info["source_fk_attname"] != info["target_fk_attname"]

    def test_get_m2m_info_none(self):
        """Test get_m2m_info with non-M2M field."""
        assert get_m2m_info(ODataModelWithRelations, "title") is None

    def test_validate_field_name_private_exception(self):
        """Test validate_field_name raises for private field."""
        with pytest.raises(InvalidFieldError) as exc:
            validate_field_name(ODataModelWithRelations, "_private", raise_exception=True)
        assert "access to private fields is not allowed" in str(exc.value)

    def test_validate_field_name_allowed_fields_path(self):
        """Test validate_field_name with path and allowed_fields."""
        # If it's a path and it's NOT in allowed_fields, it might be rejected.
        # Current logic for paths (__ in field_name) is to return False if not exists.
        assert validate_field_name(ODataModelWithRelations, "target__name", allowed_fields={"target"}) is False

    def test_validate_field_name_nonexistent_exception(self):
        """Test validate_field_name raises for non-existent field."""
        with pytest.raises(InvalidFieldError) as exc:
            validate_field_name(ODataModelWithRelations, "nonexistent", raise_exception=True)
        assert "field does not exist on model" in str(exc.value)

    def test_validate_field_name_allowed_fields_success(self):
        """Test validate_field_name succeeds if in allowed_fields even if not on model (e.g. annotation)."""
        assert validate_field_name(ODataModelWithRelations, "some_annotation", allowed_fields={"some_annotation"}) is True
