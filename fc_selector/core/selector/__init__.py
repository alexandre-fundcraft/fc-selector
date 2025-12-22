"""
Framework-agnostic selector interfaces and utilities.

This module provides base interfaces that can be implemented for any ORM:
- Django ORM
- SQLAlchemy
- Tortoise ORM
- etc.
"""

from .base import BaseSelectorInterface

__all__ = ['BaseSelectorInterface']
