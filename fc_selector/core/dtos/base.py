
"""
Base DTO class with automatic model-to-DTO conversion.

This module provides BaseODataDTO which uses type introspection to automatically
convert Django model instances to DTOs without hardcoding field names.
"""

from dataclasses import dataclass
from dataclasses import fields as dataclass_fields
from typing import Any, get_args, get_origin, get_type_hints


# Sentinel for unselected fields
class _Unset:
    """Sentinel for unselected fields."""
    def __repr__(self):
        return "<UNSET>"

UNSET = _Unset()


@dataclass
class BaseODataDTO:
    """
    Base class for OData DTOs with automatic model conversion.

    This class provides automatic conversion from Django model instances to DTOs
    using type introspection. Subclasses only need to define their fields with
    type annotations - all conversion logic is handled automatically.

    Features:
    - Automatic field population using introspection
    - Automatic relationship detection via type hints
    - Support for $select (only populate selected fields)
    - Support for $expand (automatically convert related objects to DTOs)
    - Sentinel values for unselected fields

    Example:
        >>> @dataclass
        >>> class AuthorDTO(BaseODataDTO):
        ...     id: int = UNSET
        ...     name: str = UNSET
        ...     user: Optional[UserDTO] = UNSET

        >>> # Automatic conversion
        >>> dto = AuthorDTO.from_model(author_instance, selected_fields={'id', 'name'})
        >>> # dto.id = 1
        >>> # dto.name = "John"
        >>> # dto.user = UNSET  # Not selected
    """

    @classmethod
    def _is_dto_type(cls, field_type: Any) -> bool:
        """
        Check if a type annotation represents a DTO relationship.

        Detects DTOs by checking if the type name ends with 'DTO'.
        Handles Optional[...], List[...], Optional[List[...]], and direct DTO types.

        Args:
            field_type: Type annotation from get_type_hints()

        Returns:
            True if the type represents a DTO relationship

        Examples:
            >>> _is_dto_type(UserDTO)  # True
            >>> _is_dto_type(Optional[UserDTO])  # True
            >>> _is_dto_type(List[UserDTO])  # True
            >>> _is_dto_type(Optional[List[UserDTO]])  # True
            >>> _is_dto_type(str)  # False
        """
        # Handle Optional[T] (which is Union[T, None])
        origin = get_origin(field_type)
        if origin is not None:
            args = get_args(field_type)
            if args:
                # For Optional[T] or List[T], check the first arg
                field_type = args[0]

                # If it's still generic (e.g., List[DTO]), unwrap again
                inner_origin = get_origin(field_type)
                if inner_origin is not None:
                    inner_args = get_args(field_type)
                    if inner_args:
                        field_type = inner_args[0]

        # Check if type name ends with 'DTO'
        if hasattr(field_type, '__name__'):
            return field_type.__name__.endswith('DTO')

        return False

    @classmethod
    def _is_many_relationship(cls, field_type: Any) -> bool:
        """
        Check if a relationship is one-to-many (List[DTO]).

        Args:
            field_type: Type annotation from get_type_hints()

        Returns:
            True if the type is List[SomeDTO]
        """
        origin = get_origin(field_type)
        if origin is list:
            return True

        # Handle Optional[List[...]]
        if origin is not None:
            args = get_args(field_type)
            if args:
                inner_origin = get_origin(args[0])
                if inner_origin is list:
                    return True

        return False

    @classmethod
    def _get_dto_class(cls, field_type: Any) -> type | None:
        """
        Extract the DTO class from a type annotation.

        Args:
            field_type: Type annotation (e.g., UserDTO, Optional[UserDTO], List[UserDTO])

        Returns:
            The DTO class, or None if not a DTO type
        """
        # Handle Optional[T] or List[T]
        origin = get_origin(field_type)
        if origin is not None:
            args = get_args(field_type)
            if args:
                # For Optional[UserDTO] or List[UserDTO]
                inner_type = args[0]
                # If it's Optional[List[UserDTO]], go one level deeper
                inner_origin = get_origin(inner_type)
                if inner_origin is list:
                    inner_args = get_args(inner_type)
                    if inner_args:
                        return inner_args[0]
                return inner_type

        # Direct DTO type
        if hasattr(field_type, '__name__') and field_type.__name__.endswith('DTO'):
            return field_type

        return None

    @classmethod
    def from_model(cls, instance, selected_fields: set[str] | None = None,
                   expanded_fields: set[str] | None = None, expand_options: dict | None = None) -> 'BaseODataDTO':
        """
        Create DTO from model instance with automatic field selection.

        Uses type introspection to automatically:
        1. Detect which fields are relationships (DTOs)
        2. Populate regular fields from model instance
        3. Convert related objects to DTOs if expanded
        4. Handle both one-to-one and one-to-many relationships
        5. Apply nested $select to expanded relationships

        Args:
            instance: Django model instance to convert
            selected_fields: Set of field names from $select, or None for all fields
            expanded_fields: Set of relationship names from $expand
            expand_options: Nested options for expanded fields (e.g., {'author': {'$select': 'name'}})

        Returns:
            DTO instance with automatic field population
        """
        data = {}
        expanded_fields = expanded_fields or set()
        expand_options = expand_options or {}

        # DEBUG
        import sys
        print(f"DEBUG from_model: cls={cls.__name__}, expanded_fields={expanded_fields}, expand_options={expand_options}", file=sys.stderr)

        # Get all DTO fields defined in the dataclass
        dto_fields = {f.name for f in dataclass_fields(cls)}

        # Determine which fields to populate based on $select
        if selected_fields is None:
            fields_to_populate = dto_fields
        else:
            # Include both selected fields AND expanded fields
            # (expanded fields must be included even if not explicitly in $select)
            fields_to_populate = (dto_fields & selected_fields) | (dto_fields & expanded_fields)

        # Get type hints to detect relationships automatically
        try:
            type_hints = get_type_hints(cls)
        except Exception:
            # If type hints fail (e.g., forward references), fall back to annotations
            type_hints = cls.__annotations__ if hasattr(cls, '__annotations__') else {}

        # Automatically detect relationship fields by checking type hints
        relationship_fields = set()
        relationship_info = {}  # Store relationship metadata

        for field_name in dto_fields:
            if field_name in type_hints:
                field_type = type_hints[field_name]
                if cls._is_dto_type(field_type):
                    relationship_fields.add(field_name)
                    relationship_info[field_name] = {
                        'dto_class': cls._get_dto_class(field_type),
                        'is_many': cls._is_many_relationship(field_type)
                    }

        # Populate regular (non-relationship) fields
        for field_name in fields_to_populate - relationship_fields:
            if hasattr(instance, field_name):
                value = getattr(instance, field_name)
                # Skip Django RelatedManagers (they're relationship fields, not regular fields)
                from django.db.models import Manager
                if not isinstance(value, Manager):
                    data[field_name] = value

        # Handle relationship fields
        for field_name in fields_to_populate & relationship_fields:
            rel_info = relationship_info[field_name]
            dto_class = rel_info['dto_class']
            is_many = rel_info['is_many']

            if field_name in expanded_fields:
                # Get nested options for this field (e.g., {'$select': 'name', '$expand': 'user'})
                nested_opts = expand_options.get(field_name, {})

                # Parse nested $select if present
                nested_selected_fields = None
                if '$select' in nested_opts:
                    # Parse comma-separated field names
                    nested_selected_fields = set(nested_opts['$select'].split(','))

                # Parse nested $expand if present
                nested_expanded_fields = set()
                nested_expand_options = {}
                if '$expand' in nested_opts:
                    expand_value = nested_opts['$expand']

                    # Parse the nested expand using the OData parser
                    try:
                        from fc_selector.core.parsers.query import parse_odata_query

                        # Create a query string with just the expand
                        nested_query = f'$expand={expand_value}'
                        nested_query_params = parse_odata_query(nested_query)

                        if nested_query_params.expand:
                            if hasattr(nested_query_params.expand, 'nested_options'):
                                nested_expand_options = nested_query_params.expand.nested_options
                                nested_expanded_fields = set(nested_expand_options.keys())
                            else:
                                # Simple expand without options
                                nested_expanded_fields = set(expand_value.split(','))
                    except Exception:
                        # Fallback to simple comma split
                        nested_expanded_fields = set(expand_value.split(','))

                # Expanded: convert related objects to DTOs with nested options
                if is_many:
                    # One-to-many: List[DTO]
                    if hasattr(instance, field_name):
                        related_manager = getattr(instance, field_name)
                        related_objs = list(related_manager.all())
                        data[field_name] = [
                            dto_class.from_model(obj, nested_selected_fields, nested_expanded_fields, nested_expand_options)
                            for obj in related_objs
                        ]
                    else:
                        data[field_name] = []
                else:
                    # One-to-one or foreign key: Optional[DTO]
                    if hasattr(instance, field_name):
                        related_obj = getattr(instance, field_name)
                        if related_obj is not None:
                            data[field_name] = dto_class.from_model(related_obj, nested_selected_fields, nested_expanded_fields, nested_expand_options)
                        else:
                            data[field_name] = None
                    else:
                        data[field_name] = None
            else:
                # Not expanded: mark as UNSET (don't include relationship objects)
                # Relationship fields should only be included when expanded
                # Don't include in data dict - field will default to UNSET
                pass

        return cls(**data)
