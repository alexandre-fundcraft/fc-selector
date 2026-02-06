"""
Base DTO class with automatic model-to-DTO conversion.

This module provides BaseODataDTO which uses type introspection to automatically
convert Django model instances to DTOs without hardcoding field names.
"""

import logging
from dataclasses import dataclass
from dataclasses import fields as dataclass_fields
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Protocol, cast, get_args, get_origin, get_type_hints

from django.db.models import Manager

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from typing import Self


class DTOProtocol(Protocol):
    """Protocol for DTO classes with from_model method."""

    @classmethod
    def from_model(
        cls,
        instance: Any,
        selected_fields: set[str] | None = None,
        expanded_fields: set[str] | None = None,
        expand_options: dict | None = None,
        field_mapping: dict[str, str] | None = None,
        *,
        _depth: int = 0,
    ) -> "Self": ...


# Sentinel for unselected fields
class Unset:
    """Sentinel for unselected fields."""

    def __repr__(self):
        return "<UNSET>"


UNSET = Unset()

# Module-level caches for DTO introspection (shared across all DTOs)
# Note: These caches are keyed by DTO class (type), not by instance.
# Since DTO classes are defined statically in code, these caches are bounded
# by the number of DTO classes in your application and will not grow indefinitely.
# For applications with dynamic class generation, use clear_dto_caches() periodically.
_TYPE_HINTS_CACHE: dict[type, dict[str, Any]] = {}
_RELATIONSHIP_INFO_CACHE: dict[type, dict[str, dict[str, Any]]] = {}
_DTO_FIELDS_CACHE: dict[type, set[str]] = {}

# Security: Maximum recursion depth for nested DTOs to prevent infinite loops
MAX_DTO_RECURSION_DEPTH = 10


def clear_dto_caches() -> None:
    """
    Clear all DTO introspection caches.

    Call this function if you need to:
    - Free memory in long-running processes
    - Reset caches after dynamic class modifications (rare)
    - Clear state between test runs

    Note: Caches will be automatically repopulated on next DTO conversion.
    """
    _TYPE_HINTS_CACHE.clear()
    _RELATIONSHIP_INFO_CACHE.clear()
    _DTO_FIELDS_CACHE.clear()
    cls = BaseODataDTO
    if hasattr(cls, "_parse_nested_expand_options"):
        cls._parse_nested_expand_options.cache_clear()  # noqa: W0212 - BaseODataDTO internal method


class RecursionLimitExceededError(Exception):
    """Raised when DTO conversion exceeds maximum recursion depth."""

    def __init__(self, depth: int, dto_class: str):
        self.depth = depth
        self.dto_class = dto_class
        super().__init__(
            f"Maximum DTO recursion depth ({depth}) exceeded while converting {dto_class}. "
            "This may indicate circular relationships in your DTOs."
        )


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

    is_odata_dto = True

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

        # Check for explicit attribute (Robust)
        if getattr(field_type, "is_odata_dto", False):
            return True

        # Check if type name ends with 'DTO'
        if hasattr(field_type, "__name__"):
            return bool(field_type.__name__.endswith("DTO"))

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
                        return cast(type, inner_args[0])
                return cast(type, inner_type)

        # Direct DTO type
        if hasattr(field_type, "__name__") and field_type.__name__.endswith("DTO"):
            return cast(type, field_type)

        return None

    @classmethod
    def _get_safe_type_hints(cls) -> dict[str, Any]:
        """Get type hints with fallback for forward references (cached)."""
        if cls not in _TYPE_HINTS_CACHE:
            try:
                _TYPE_HINTS_CACHE[cls] = get_type_hints(cls)
            except (TypeError, AttributeError, NameError):
                _TYPE_HINTS_CACHE[cls] = cls.__annotations__ if hasattr(cls, "__annotations__") else {}
        return _TYPE_HINTS_CACHE[cls]

    @classmethod
    def _get_dto_fields(cls) -> set[str]:
        """Get DTO fields (cached)."""
        if cls not in _DTO_FIELDS_CACHE:
            _DTO_FIELDS_CACHE[cls] = {f.name for f in dataclass_fields(cls)}
        return _DTO_FIELDS_CACHE[cls]

    @classmethod
    def _get_relationship_info(cls) -> dict[str, dict[str, Any]]:
        """Get relationship info (cached)."""
        if cls not in _RELATIONSHIP_INFO_CACHE:
            dto_fields = cls._get_dto_fields()
            type_hints = cls._get_safe_type_hints()
            _RELATIONSHIP_INFO_CACHE[cls] = cls._detect_relationships(dto_fields, type_hints)
        return _RELATIONSHIP_INFO_CACHE[cls]

    @classmethod
    def _determine_fields_to_populate(
        cls, dto_fields: set[str], selected_fields: set[str] | None, expanded_fields: set[str]
    ) -> set[str]:
        """Determine which fields should be populated based on $select."""
        if selected_fields is None:
            return dto_fields
        return (dto_fields & selected_fields) | (dto_fields & expanded_fields)

    @classmethod
    def _detect_relationships(cls, dto_fields: set[str], type_hints: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Detect which fields are relationships and gather their metadata."""
        relationships = {}
        for field_name in dto_fields:
            if field_name in type_hints:
                field_type = type_hints[field_name]
                if cls._is_dto_type(field_type):
                    relationships[field_name] = {
                        "dto_class": cls._get_dto_class(field_type),
                        "is_many": cls._is_many_relationship(field_type),
                    }
        return relationships

    @classmethod
    def _populate_regular_fields(
        cls,
        data: dict,
        instance,
        fields_to_populate: set[str],
        relationship_fields: set[str],
        field_mapping: dict[str, str] | None = None,
    ) -> None:
        """Populate non-relationship fields from the instance.

        Args:
            data: Dictionary to populate
            instance: Model instance to read from
            fields_to_populate: Set of DTO field names to populate
            relationship_fields: Set of relationship field names (to skip)
            field_mapping: Mapping from model field name to DTO field name
                           (reverse of field_aliases, i.e. model_field -> dto_field)
        """
        # Create reverse mapping: dto_field -> model_field
        dto_to_model = {}
        if field_mapping:
            dto_to_model = {v: k for k, v in field_mapping.items()}

        for field_name in fields_to_populate - relationship_fields:
            # Check if there's a mapping for this DTO field
            model_field = dto_to_model.get(field_name, field_name)
            if hasattr(instance, model_field):
                value = getattr(instance, model_field)
                if not isinstance(value, Manager):
                    data[field_name] = value

    @classmethod
    @lru_cache(maxsize=128)
    def _parse_nested_expand_options(cls, expand_value: str) -> tuple[set[str], dict]:
        """Parse nested $expand options into expanded fields and options dict."""
        # Lazy import to avoid core-to-protocol dependency at module level
        from fc_selector.protocols.odata.parsers.query import parse_odata_query  # noqa: PLC0415

        try:
            nested_query = f"$expand={expand_value}"
            nested_query_params = parse_odata_query(nested_query)

            if nested_query_params.expand:
                if hasattr(nested_query_params.expand, "nested_options"):
                    nested_expand_options = nested_query_params.expand.nested_options
                    nested_expanded_fields = set(nested_expand_options.keys())
                    return nested_expanded_fields, nested_expand_options
                return set(expand_value.split(",")), {}
        except (ValueError, KeyError, AttributeError):
            pass

        return set(expand_value.split(",")), {}

    @classmethod
    def _populate_many_relationship(
        cls,
        data: dict,
        instance: Any,
        field_name: str,
        dto_class: type[DTOProtocol],
        nested_selected: set[str] | None,
        nested_expanded: set[str],
        nested_options: dict,
        _depth: int = 0,
    ) -> None:
        """Populate a one-to-many relationship field.

        Checks for prefetch cache to avoid N+1 queries. If the relationship
        was prefetched, uses the cached objects; otherwise falls back to
        .all() with a warning.
        """
        if hasattr(instance, field_name):
            # Check if prefetch cache exists to avoid N+1 queries
            prefetch_cache = getattr(instance, "_prefetched_objects_cache", {})
            if field_name in prefetch_cache:
                # Use prefetched objects (no additional query)
                related_objs = prefetch_cache[field_name]
            else:
                # Fallback: query the database (potential N+1)
                related_manager = getattr(instance, field_name)
                related_objs = list(related_manager.all())
                logger.debug(
                    f"Potential N+1 query: '{field_name}' not prefetched for "
                    f"{instance.__class__.__name__}. Consider using prefetch_related()."
                )

            data[field_name] = [
                dto_class.from_model(obj, nested_selected, nested_expanded, nested_options, _depth=_depth + 1)
                for obj in related_objs
            ]
        else:
            data[field_name] = []

    @classmethod
    def _populate_single_relationship(
        cls,
        data: dict,
        instance: Any,
        field_name: str,
        dto_class: type[DTOProtocol],
        nested_selected: set[str] | None,
        nested_expanded: set[str],
        nested_options: dict,
        _depth: int = 0,
    ) -> None:
        """Populate a one-to-one or foreign key relationship field."""
        if hasattr(instance, field_name):
            related_obj = getattr(instance, field_name)
            if related_obj is not None:
                data[field_name] = dto_class.from_model(
                    related_obj, nested_selected, nested_expanded, nested_options, _depth=_depth + 1
                )
            else:
                data[field_name] = None
        else:
            data[field_name] = None

    @classmethod
    def from_model(
        cls,
        instance,
        selected_fields: set[str] | None = None,
        expanded_fields: set[str] | None = None,
        expand_options: dict | None = None,
        field_mapping: dict[str, str] | None = None,
        *,
        _depth: int = 0,
    ) -> "BaseODataDTO":
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
            field_mapping: Mapping from model field name to DTO field name
                           (reverse of field_aliases, i.e. model_field -> dto_field)
            _depth: Internal parameter to track recursion depth (do not use directly)

        Returns:
            DTO instance with automatic field population

        Raises:
            RecursionLimitExceededError: If conversion exceeds MAX_DTO_RECURSION_DEPTH
        """
        # Security: Check recursion depth to prevent infinite loops
        if _depth > MAX_DTO_RECURSION_DEPTH:
            raise RecursionLimitExceededError(_depth, cls.__name__)

        data: dict[str, Any] = {}
        expanded_fields = expanded_fields or set()
        expand_options = expand_options or {}

        # Get all DTO fields defined in the dataclass (cached)
        dto_fields = cls._get_dto_fields()

        # Determine which fields to populate
        fields_to_populate = cls._determine_fields_to_populate(dto_fields, selected_fields, expanded_fields)

        # Get relationship info (cached - no per-instance introspection)
        relationship_info = cls._get_relationship_info()
        relationship_fields = set(relationship_info.keys())

        # Populate regular (non-relationship) fields
        cls._populate_regular_fields(data, instance, fields_to_populate, relationship_fields, field_mapping)

        # Handle relationship fields
        for field_name in fields_to_populate & relationship_fields:
            if field_name not in expanded_fields:
                continue

            rel_info = relationship_info[field_name]
            dto_class = rel_info["dto_class"]
            is_many = rel_info["is_many"]

            if dto_class is None or not hasattr(dto_class, "from_model"):
                continue

            # Cast to DTOProtocol now that we've verified it has from_model
            dto_cls = cast(type[DTOProtocol], dto_class)

            # Get nested options for this field
            nested_opts = expand_options.get(field_name, {})

            # Parse nested $select
            nested_selected_fields = None
            if "$select" in nested_opts:
                nested_selected_fields = set(nested_opts["$select"].split(","))

            # Parse nested $expand
            nested_expanded_fields: set[str] = set()
            nested_expand_options: dict = {}
            if "$expand" in nested_opts:
                nested_expanded_fields, nested_expand_options = cls._parse_nested_expand_options(nested_opts["$expand"])

            # Populate the relationship (pass depth for recursion tracking)
            if is_many:
                cls._populate_many_relationship(
                    data,
                    instance,
                    field_name,
                    dto_cls,
                    nested_selected_fields,
                    nested_expanded_fields,
                    nested_expand_options,
                    _depth=_depth,
                )
            else:
                cls._populate_single_relationship(
                    data,
                    instance,
                    field_name,
                    dto_cls,
                    nested_selected_fields,
                    nested_expanded_fields,
                    nested_expand_options,
                    _depth=_depth,
                )

        return cls(**data)
