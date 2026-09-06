"""
DTO helpers shared by the DTO base class, the TypedDict generator and the
DRF serializer.
"""

import dataclasses
from typing import Any, get_args, get_origin


def get_dto_fields(dto_class: type) -> list[str]:
    """
    Extract field names from a DTO class.

    Supports:
    - Dataclasses
    - Classes with __annotations__
    - BaseODataDTO (via _get_dto_fields)
    """
    if not dto_class:
        return []

    # If it has the internal cached method from BaseODataDTO
    if hasattr(dto_class, "_get_dto_fields"):
        return list(dto_class._get_dto_fields())  # noqa: SLF001 - BaseODataDTO internal method

    if dataclasses.is_dataclass(dto_class):
        return [f.name for f in dataclasses.fields(dto_class)]

    if hasattr(dto_class, "__annotations__"):
        return list(dto_class.__annotations__.keys())

    return []


def _unwrap(field_type: Any) -> Any:
    """Peel Optional[...] / list[...] / Optional[list[...]] down to the inner type."""
    origin = get_origin(field_type)
    if origin is None:
        return field_type

    args = get_args(field_type)
    if not args:
        return field_type

    inner = args[0]
    if get_origin(inner) is not None:
        inner_args = get_args(inner)
        if inner_args:
            return inner_args[0]
    return inner


def is_dto_type(field_type: Any) -> bool:
    """Check whether a type annotation refers to a DTO.

    Handles ``UserDTO``, ``Optional[UserDTO]``, ``list[UserDTO]`` and
    ``Optional[list[UserDTO]]``.

    A DTO is either a ``BaseODataDTO`` subclass (``is_odata_dto``) or, for the
    DRF serializer path where plain dataclasses are allowed, any class whose
    name ends in ``DTO``.
    """
    inner = _unwrap(field_type)

    if getattr(inner, "is_odata_dto", False):
        return True

    name = getattr(inner, "__name__", None)
    return bool(name and name.endswith("DTO"))


def is_many_relationship(field_type: Any) -> bool:
    """Check whether a type annotation is a to-many relationship (``list[DTO]``)."""
    origin = get_origin(field_type)
    if origin is list:
        return True

    args = get_args(field_type)
    return bool(args) and get_origin(args[0]) is list


def dto_class_of(field_type: Any) -> type | None:
    """Extract the DTO class from a type annotation, or None if it is not a DTO."""
    return _unwrap(field_type) if is_dto_type(field_type) else None
