"""Django utilities for fc_selector."""

from fc_selector.django.utils.aliases import resolve_field_alias
from fc_selector.django.utils.introspection import (
    M2MInfo,
    get_field_safe,
    get_m2m_info,
    get_related_model,
    get_reverse_fk_info,
    is_forward_relation,
    is_m2m_relation,
    validate_field_name,
)

__all__ = [
    "M2MInfo",
    "get_field_safe",
    "get_m2m_info",
    "get_related_model",
    "get_reverse_fk_info",
    "is_forward_relation",
    "is_m2m_relation",
    "resolve_field_alias",
    "validate_field_name",
]
