"""
Base DTO with neutral object projection and legacy model conversion.

This module provides BaseODataDTO which uses type introspection to automatically
project plain objects and mappings; ORM extraction belongs to adapters.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from dataclasses import fields as dataclass_fields
from typing import Any, Self, cast, get_type_hints

from fc_selector.core.dtos.typed_dicts import generate_typeddict
from fc_selector.core.dtos.utils import dto_class_of, is_dto_type, is_many_relationship
from fc_selector.core.intent import QueryIntent


# Sentinel for unselected fields
class Unset:
    """Sentinel for unselected fields."""

    def __repr__(self):
        return "<UNSET>"


UNSET = Unset()

# Module-level caches for DTO introspection (shared across all DTOs).
# Keyed by DTO class (type), not by instance: DTO classes are defined statically
# in code, so these caches are bounded by the number of DTO classes and will not
# grow indefinitely.
_TYPE_HINTS_CACHE: dict[type, dict[str, Any]] = {}
_RELATIONSHIP_INFO_CACHE: dict[type, dict[str, dict[str, Any]]] = {}
_DTO_FIELDS_CACHE: dict[type, set[str]] = {}

# Security: Maximum recursion depth for nested DTOs to prevent infinite loops
MAX_DTO_RECURSION_DEPTH = 10


class RecursionLimitExceededError(Exception):
    """Raised when DTO conversion exceeds maximum recursion depth."""

    def __init__(self, depth: int, dto_class: str):
        self.depth = depth
        self.dto_class = dto_class
        super().__init__(
            f"Maximum DTO recursion depth ({depth}) exceeded while converting {dto_class}. "
            "This may indicate circular relationships in your DTOs."
        )


class _TypedDictDescriptor:
    """Descriptor that lazily generates a TypedDict on first ``DTO.__td__`` access."""

    def __get__(self, obj: Any, cls: type) -> type:
        if cls is BaseODataDTO:
            raise AttributeError("__td__ is only available on BaseODataDTO subclasses")
        td = generate_typeddict(cls)
        cls.__td__ = td  # type: ignore[attr-defined]
        return td


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
    - ``__td__`` attribute: auto-generated TypedDict for typed dict output

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
        >>>
        >>> # Auto-generated TypedDict
        >>> AuthorDTO.__td__  # TypedDict('AuthorDict', {'id': int, ...}, total=False)
    """

    is_odata_dto = True

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
                if is_dto_type(field_type):
                    relationships[field_name] = {
                        "dto_class": dto_class_of(field_type),
                        "is_many": is_many_relationship(field_type),
                    }
        return relationships

    @classmethod
    def from_object(
        cls,
        instance: Any,
        intent: QueryIntent | None = None,
        field_mapping: dict[str, str] | None = None,
        *,
        value_reader: Callable[[Any, str, bool | None], Any] | None = None,
        nested_mappings: dict[str, Any] | None = None,
        _depth: int = 0,
    ) -> Self:
        """Project plain objects/mappings using neutral intents, without ORM access.

        Adapters can supply a value reader to resolve their own relations. Paths
        use dots in the generic reader; framework lookup syntax stays in adapters.
        ``nested_mappings`` maps relation names to child ``field_mapping`` and
        ``nested_mappings`` options, keeping aliases scoped to each expansion.
        """
        if _depth > MAX_DTO_RECURSION_DEPTH:
            raise RecursionLimitExceededError(_depth, cls.__name__)
        intent = intent or QueryIntent()
        reader = value_reader or read_value
        selected = set(intent.select.fields) if intent.select is not None else None
        relations = intent.expand.relations if intent.expand else {}
        nested_mappings = nested_mappings or {}
        fields = cls._determine_fields_to_populate(cls._get_dto_fields(), selected, set(relations))
        relationships = cls._get_relationship_info()
        aliases = {v: k for k, v in (field_mapping or {}).items()}
        data = {}
        for name in fields:
            if name not in relationships:
                value = reader(instance, aliases.get(name, name), None)
                if value is not UNSET:
                    data[name] = value
                continue
            if name not in relations:
                continue
            info = relationships[name]
            dto_class = info["dto_class"]
            if dto_class is None or not hasattr(dto_class, "from_object"):
                continue
            value = reader(instance, name, info["is_many"])
            if info["is_many"]:
                data[name] = [
                    dto_class.from_object(
                        obj, relations[name], value_reader=reader, _depth=_depth + 1, **nested_mappings.get(name, {})
                    )
                    for obj in ([] if value is UNSET or value is None else value)
                ]
            else:
                data[name] = (
                    None
                    if value is UNSET or value is None
                    else dto_class.from_object(
                        value, relations[name], value_reader=reader, _depth=_depth + 1, **nested_mappings.get(name, {})
                    )
                )
        return cls(**data)

    @classmethod
    def from_model(
        cls,
        instance,
        selected_fields=None,
        expanded_fields=None,
        expand_options=None,
        field_mapping=None,
        *,
        _depth=0,
    ) -> Self:
        """Historical Django/OData facade. Use from_object for neutral projection."""
        from fc_selector.compat import from_model  # noqa: PLC0415

        return cast(
            Self,
            from_model(cls, instance, selected_fields, expanded_fields, expand_options, field_mapping, _depth=_depth),
        )

    @classmethod
    def _parse_nested_expand_options(cls, expand_value: str) -> tuple[set[str], dict]:
        """Legacy textual-options compatibility; never used by from_object."""
        from fc_selector.compat import parse_nested_options  # noqa: PLC0415

        return cast(tuple[set[str], dict], parse_nested_options(expand_value))

    def to_dict(self) -> dict[str, Any]:
        """Convert DTO to a plain dictionary, recursively handling nested DTOs.

        UNSET fields are omitted from the output. Nested DTOs and lists of DTOs
        are converted recursively.

        Returns:
            Dictionary with populated (non-UNSET) fields.
        """
        result: dict[str, Any] = {}
        for field in dataclass_fields(self):
            value = getattr(self, field.name)
            if value is UNSET:
                continue
            result[field.name] = _to_dict_value(value)
        return result


def read_value(instance: Any, path: str, many: bool | None = None) -> Any:
    """Read a dotted path from plain objects or mappings without ORM conventions."""
    value = instance
    for part in path.split("."):
        if value is None or value is UNSET:
            return value
        value = value.get(part, UNSET) if isinstance(value, Mapping) else getattr(value, part, UNSET)
    return value


def _to_dict_value(value: Any) -> Any:
    """Recursively convert a value, turning nested DTOs into dicts."""
    if isinstance(value, BaseODataDTO):
        return value.to_dict()
    if isinstance(value, list):
        return [_to_dict_value(item) for item in value]
    return value


# Attach the TypedDict descriptor *after* BaseODataDTO is fully defined
# to avoid @dataclass triggering __get__ during class creation.
BaseODataDTO.__td__ = _TypedDictDescriptor()  # type: ignore[attr-defined]
