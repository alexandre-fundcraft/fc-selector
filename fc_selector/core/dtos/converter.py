"""
Framework-agnostic DTO converter.

This module provides utilities for converting ORM instances to DTOs
without depending on any specific ORM framework.

The actual conversion logic is in BaseODataDTO.from_model(), which uses
type introspection to automatically detect fields and relationships.
This module just provides a cleaner API for using that functionality.
"""

from typing import Any


class DTOConverter:
    """
    Framework-agnostic DTO converter using type introspection.

    This converter works with any ORM model that has attributes matching
    the DTO field names. It uses BaseODataDTO.from_model() for the actual
    conversion, which automatically:
    - Detects regular fields and relationship fields via type hints
    - Applies $select to limit fields
    - Applies $expand to include related objects as DTOs
    - Handles nested $select and $expand options

    Example:
        >>> from blog.selectors import BlogPostDTO
        >>> from blog.models import BlogPost
        >>>
        >>> # Convert single instance
        >>> post = BlogPost.objects.get(id=1)
        >>> dto = DTOConverter.to_dto(
        ...     BlogPostDTO,
        ...     post,
        ...     selected_fields={'id', 'title'},
        ...     expanded_fields={'author'}
        ... )
        >>> # dto.id = 1
        >>> # dto.title = "My Post"
        >>> # dto.author = AuthorDTO(...)
        >>> # dto.content = UNSET  # Not selected
        >>>
        >>> # Convert multiple instances
        >>> posts = BlogPost.objects.all()[:10]
        >>> dtos = DTOConverter.to_dtos(
        ...     BlogPostDTO,
        ...     posts,
        ...     selected_fields={'id', 'title'}
        ... )
    """

    @staticmethod
    def to_dto(
        dto_class: type,
        instance: Any,
        selected_fields: set[str] | None = None,
        expanded_fields: set[str] | None = None,
        expand_options: dict | None = None,
    ) -> Any:
        """
        Convert single ORM instance to DTO.

        Uses BaseODataDTO.from_model() for automatic conversion based on
        type introspection. No need to hardcode field mappings.

        Args:
            dto_class: DTO class (must inherit from BaseODataDTO)
            instance: ORM model instance (Django Model, SQLAlchemy model, etc.)
            selected_fields: Set of field names from $select, None = all fields
            expanded_fields: Set of relationship names from $expand
            expand_options: Nested options for expanded fields
                           Example: {'author': {'$select': 'name,email'}}

        Returns:
            DTO instance with fields populated according to parameters

        Raises:
            ValueError: If dto_class doesn't inherit from BaseODataDTO

        Example:
            >>> dto = DTOConverter.to_dto(
            ...     BlogPostDTO,
            ...     blog_post_instance,
            ...     selected_fields={'id', 'title', 'author'},
            ...     expanded_fields={'author'},
            ...     expand_options={'author': {'$select': 'name'}}
            ... )
        """
        # Verify dto_class has from_model method (from BaseODataDTO)
        if not hasattr(dto_class, "from_model"):
            raise ValueError(f"{dto_class.__name__} must inherit from BaseODataDTO to use automatic conversion")

        # Initialize defaults
        expanded_fields = expanded_fields or set()
        expand_options = expand_options or {}

        # Use BaseODataDTO.from_model() for automatic conversion
        return dto_class.from_model(
            instance,
            selected_fields=selected_fields,
            expanded_fields=expanded_fields,
            expand_options=expand_options,
        )

    @staticmethod
    def to_dtos(
        dto_class: type,
        instances: list[Any],
        selected_fields: set[str] | None = None,
        expanded_fields: set[str] | None = None,
        expand_options: dict | None = None,
    ) -> list[Any]:
        """
        Convert list of ORM instances to DTOs.

        This is a convenience method that applies to_dto() to each instance.

        Args:
            dto_class: DTO class (must inherit from BaseODataDTO)
            instances: List of ORM model instances
            selected_fields: Set of field names from $select, None = all fields
            expanded_fields: Set of relationship names from $expand
            expand_options: Nested options for expanded fields

        Returns:
            List of DTO instances

        Example:
            >>> posts = BlogPost.objects.filter(status='published')
            >>> dtos = DTOConverter.to_dtos(
            ...     BlogPostDTO,
            ...     list(posts),
            ...     selected_fields={'id', 'title'}
            ... )
        """
        return [
            DTOConverter.to_dto(dto_class, inst, selected_fields, expanded_fields, expand_options) for inst in instances
        ]


# For convenience, provide module-level functions
to_dto = DTOConverter.to_dto
to_dtos = DTOConverter.to_dtos

__all__ = ["DTOConverter", "to_dto", "to_dtos"]
