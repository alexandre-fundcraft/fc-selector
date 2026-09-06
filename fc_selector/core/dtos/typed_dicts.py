"""
Auto-generate TypedDict classes from BaseODataDTO definitions.

Access via ``PostDTO.__td__`` — a lazy descriptor on BaseODataDTO that
generates a ``TypedDict`` on first access and caches it on the class.

All fields use ``total=False`` (i.e. every key is ``NotRequired``)
because ``$select`` can omit any field from the output dict.
"""

from __future__ import annotations

import functools
import operator
import types
from typing import Any, TypedDict, Union, get_args, get_origin

from fc_selector.core.dtos.utils import is_dto_type

# Track DTOs currently being generated to break circular references.
_GENERATING: set[type] = set()


def generate_typeddict(dto_class: type) -> type:
    """Build a ``TypedDict`` whose fields mirror *dto_class*.

    Nested DTO references are resolved recursively (``AuthorDTO`` →
    ``AuthorDict``).  Circular references fall back to ``dict``.
    """
    name = dto_class.__name__
    if name.endswith("DTO"):
        name = name[:-3] + "Dict"
    else:
        name = name + "Dict"

    # Guard against circular references.
    if dto_class in _GENERATING:
        return dict  # type: ignore[return-value]

    _GENERATING.add(dto_class)
    try:
        hints = dto_class._get_safe_type_hints()  # type: ignore[attr-defined]
        fields: dict[str, Any] = {}
        for field_name, field_type in hints.items():
            fields[field_name] = _resolve_type(field_type)
        return TypedDict(name, fields, total=False)  # type: ignore[operator,no-any-return]
    finally:
        _GENERATING.discard(dto_class)


# ---------------------------------------------------------------------------
# Type resolution helpers
# ---------------------------------------------------------------------------


def _resolve_type(tp: Any) -> Any:
    """Swap DTO references inside a type annotation for their TypedDicts."""
    # Direct DTO class → its TypedDict (lazily built by the __td__ descriptor)
    if isinstance(tp, type) and is_dto_type(tp):
        return getattr(tp, "__td__", dict)

    origin = get_origin(tp)
    if origin is None:
        # Plain type (int, str, …) — keep as-is.
        return tp

    args = get_args(tp)
    if not args:
        return tp

    # Union — typing.Union or PEP 604 types.UnionType (X | Y)
    if origin is Union or isinstance(tp, types.UnionType):
        new_args = tuple(_resolve_type(a) for a in args)
        # Reconstruct via | operator to produce a types.UnionType on 3.10+
        return functools.reduce(operator.or_, new_args)

    # list[X], set[X], frozenset[X], …
    new_args = tuple(_resolve_type(a) for a in args)
    return origin[new_args] if new_args != args else tp
