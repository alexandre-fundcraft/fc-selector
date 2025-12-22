"""
DTOs for OData - Data Transfer Objects with automatic model conversion.
"""

from .base import UNSET, BaseODataDTO
from .converter import DTOConverter, to_dto, to_dtos

__all__ = ['BaseODataDTO', 'UNSET', 'DTOConverter', 'to_dto', 'to_dtos']
