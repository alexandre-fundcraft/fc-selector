"""
Framework-agnostic base interface for OData selectors.

This module defines the contract that all ORM-specific selector implementations
must follow. It uses Protocol (PEP 544) for structural subtyping, making it
compatible with any ORM without tight coupling.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BaseSelectorInterface(Protocol):
    """
    Protocol defining the interface for OData selectors.

    This is a structural type (Protocol) rather than a base class,
    meaning implementations don't need to explicitly inherit from it.
    They just need to implement the required methods.

    Implementations:
    - DjangoODataSelector: Django ORM implementation
    - SQLAlchemyODataSelector: SQLAlchemy implementation (future)

    Example:
        >>> class DjangoODataSelector:
        ...     def query(self, query_string: str, **kwargs) -> QuerySet:
        ...         # Implementation using Django ORM
        ...         pass
        ...
        ...     def query_as_dtos(self, query_string: str, **kwargs) -> List[Any]:
        ...         # Implementation using Django ORM + DTOs
        ...         pass

        >>> # The class automatically conforms to BaseSelectorInterface
        >>> selector = DjangoODataSelector(BlogPost)
        >>> assert isinstance(selector, BaseSelectorInterface)  # True
    """

    def query(self, query_string: str, **kwargs) -> Any:
        """
        Execute OData query and return ORM-specific result.

        Args:
            query_string: OData query string (e.g., "$filter=status eq 'published'")
            **kwargs: Implementation-specific arguments (model, base query, etc.)

        Returns:
            ORM-specific result (QuerySet for Django, Query for SQLAlchemy, etc.)

        Example:
            >>> selector = DjangoODataSelector(BlogPost)
            >>> queryset = selector.query("$filter=status eq 'published'&$expand=author")
            >>> # Returns: Django QuerySet with optimizations applied
        """
        ...

    def query_as_dtos(self, query_string: str, **kwargs) -> list[Any]:
        """
        Execute OData query and return list of DTOs.

        This method should:
        1. Parse the OData query string using core parser
        2. Execute the query using the ORM
        3. Convert results to DTOs using the DTO converter
        4. Apply $select and $expand to DTOs

        Args:
            query_string: OData query string
            **kwargs: Implementation-specific arguments

        Returns:
            List of DTO instances with fields populated according to $select/$expand

        Example:
            >>> selector = BlogPostSelector()
            >>> dtos = selector.query_as_dtos(
            ...     "$select=id,title&$expand=author($select=name)"
            ... )
            >>> # Returns: [BlogPostDTO(id=1, title='...', author=AuthorDTO(name='...'))]
        """
        ...

    def to_dto(
        self,
        instance: Any,
        selected_fields: set[str] | None = None,
        expanded_fields: set[str] | None = None,
        expand_options: dict | None = None
    ) -> Any:
        """
        Convert single ORM instance to DTO.

        This method should use the DTO converter to transform an ORM
        instance to a DTO, applying field selection and expansion.

        Args:
            instance: ORM model instance
            selected_fields: Fields to include (from $select), None = all
            expanded_fields: Relationships to expand (from $expand)
            expand_options: Nested options for expanded fields

        Returns:
            DTO instance

        Example:
            >>> selector = BlogPostSelector()
            >>> post = BlogPost.objects.get(id=1)
            >>> dto = selector.to_dto(
            ...     post,
            ...     selected_fields={'id', 'title'},
            ...     expanded_fields={'author'}
            ... )
            >>> # Returns: BlogPostDTO(id=1, title='...', author=AuthorDTO(...))
        """
        ...

    def to_dtos(
        self,
        instances: list[Any],
        selected_fields: set[str] | None = None,
        expanded_fields: set[str] | None = None,
        expand_options: dict | None = None
    ) -> list[Any]:
        """
        Convert list of ORM instances to DTOs.

        Args:
            instances: List of ORM model instances
            selected_fields: Fields to include (from $select), None = all
            expanded_fields: Relationships to expand (from $expand)
            expand_options: Nested options for expanded fields

        Returns:
            List of DTO instances

        Example:
            >>> selector = BlogPostSelector()
            >>> posts = BlogPost.objects.all()[:10]
            >>> dtos = selector.to_dtos(
            ...     posts,
            ...     selected_fields={'id', 'title'},
            ...     expanded_fields={'author'}
            ... )
        """
        ...


class BaseSelector:
    """
    Optional base class providing common DTO conversion logic.

    Selectors can inherit from this class to get default implementations
    of to_dto() and to_dtos() that delegate to the DTO converter.

    This is optional - selectors can implement the Protocol directly
    without inheriting from this class.
    """

    def __init__(self, model=None, dto_class=None):
        """
        Initialize selector with model and DTO class.

        Args:
            model: ORM model class (Django Model, SQLAlchemy declarative, etc.)
            dto_class: DTO class to use for conversion
        """
        self.model = model
        self.dto_class = dto_class

    def to_dto(
        self,
        instance: Any,
        selected_fields: set[str] | None = None,
        expanded_fields: set[str] | None = None,
        expand_options: dict | None = None
    ) -> Any:
        """
        Convert single instance to DTO using DTO converter.

        This provides a default implementation that can be overridden.
        """
        if not self.dto_class:
            raise ValueError("dto_class not configured")

        # Use the DTO's from_model method (from BaseODataDTO)
        expanded_fields = expanded_fields or set()
        expand_options = expand_options or {}

        return self.dto_class.from_model(
            instance, selected_fields, expanded_fields, expand_options
        )

    def to_dtos(
        self,
        instances: list[Any],
        selected_fields: set[str] | None = None,
        expanded_fields: set[str] | None = None,
        expand_options: dict | None = None
    ) -> list[Any]:
        """
        Convert list of instances to DTOs.

        This provides a default implementation that can be overridden.
        """
        return [
            self.to_dto(inst, selected_fields, expanded_fields, expand_options)
            for inst in instances
        ]
