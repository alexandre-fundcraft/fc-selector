"""
DTOs for OData - Data Transfer Objects with automatic model conversion.
"""

from .base import (
    UNSET,
    BaseODataDTO,
    RecursionLimitExceededError,
    Unset,
)

__all__ = [
    "BaseODataDTO",
    "UNSET",
    "Unset",
    "RecursionLimitExceededError",
]
