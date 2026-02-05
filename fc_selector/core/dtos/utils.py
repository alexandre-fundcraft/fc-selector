"""
DTO utilities for fc_selector.
"""

import dataclasses


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
        return list(dto_class._get_dto_fields())

    if dataclasses.is_dataclass(dto_class):
        return [f.name for f in dataclasses.fields(dto_class)]

    if hasattr(dto_class, "__annotations__"):
        return list(dto_class.__annotations__.keys())

    return []
