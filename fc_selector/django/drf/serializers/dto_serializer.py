"""
Generic OData serializer for DTOs with customization support.

This serializer works with ODataSelector and DTOs to provide:
- Automatic serialization of DTO fields
- Field exclusion/hiding (e.g., password fields)
- Support for nested DTOs
- UNSET field handling
"""

from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass
from typing import Any

from rest_framework import serializers

from fc_selector.core.dtos import UNSET

# Cache for dynamically created serializers to avoid recursion
_serializer_cache: dict[type, type] = {}


class ODataDTOSerializer(serializers.Serializer):
    """
    Generic serializer for OData DTOs with customization support.

    This serializer automatically serializes DTOs created by ODataSelector,
    handling sentinel values (UNSET) and providing field customization.

    Features:
    - Automatic field detection from DTO dataclass
    - Field exclusion via Meta.exclude or Meta.fields
    - Custom field serializers via Meta.extra_kwargs
    - Nested DTO serialization
    - UNSET field handling (fields are omitted from output)

    Example:
        >>> class UserDTOSerializer(ODataDTOSerializer):
        ...     class Meta:
        ...         dto_class = UserDTO
        ...         exclude = ['password']  # Hide password field
        ...         extra_kwargs = {
        ...             'email': {'write_only': True}  # Make email write-only
        ...         }

        >>> # Use with ODataSelector
        >>> selector = UserSelector()
        >>> dtos = selector.query_as_dtos("$select=id,username,email")
        >>> serializer = UserDTOSerializer(dtos, many=True)
        >>> serializer.data
        [{'id': 1, 'username': 'john'}]  # email excluded, password excluded
    """

    class Meta:
        dto_class = None  # Must be set in subclass
        fields = None  # None = all fields, or list of field names to include
        exclude = None  # List of field names to exclude
        read_only_fields = None  # List of field names that are read-only
        extra_kwargs = None  # Dict of field_name -> kwargs for customization

    def __init__(self, *args, **kwargs):
        """Initialize serializer and configure fields from DTO class."""
        super().__init__(*args, **kwargs)

        # Get Meta configuration
        dto_class = getattr(self.Meta, "dto_class", None)
        if not dto_class:
            raise ValueError(f"{self.__class__.__name__} must define Meta.dto_class")

        if not is_dataclass(dto_class):
            raise ValueError(f"dto_class must be a dataclass, got {type(dto_class)}")

        self.dto_class = dto_class
        self._configure_fields()

    def _configure_fields(self):
        """Configure serializer fields based on DTO class and Meta options."""
        from typing import get_type_hints

        # Get field configuration from Meta
        fields_option = getattr(self.Meta, "fields", None)
        exclude_option = getattr(self.Meta, "exclude", None) or []
        read_only_fields = getattr(self.Meta, "read_only_fields", None) or []
        extra_kwargs = getattr(self.Meta, "extra_kwargs", None) or {}

        # Get all DTO fields
        dto_fields = {f.name: f for f in dataclass_fields(self.dto_class)}

        # Get type hints to access actual type objects
        try:
            type_hints = get_type_hints(self.dto_class)
        except (TypeError, AttributeError, NameError):
            # Fallback to annotations if type hints fail
            type_hints = getattr(self.dto_class, "__annotations__", {})

        # Determine which fields to include
        if fields_option is None:
            # Include all fields except excluded ones
            field_names = set(dto_fields.keys()) - set(exclude_option)
        else:
            # Only include specified fields (and respect exclude)
            field_names = set(fields_option) - set(exclude_option)

        # Create serializer fields
        for field_name in field_names:
            if field_name not in dto_fields:
                continue

            dto_field = dto_fields[field_name]

            # Get the actual type from type hints
            field_type = type_hints.get(field_name, dto_field.type)

            # Get extra kwargs for this field
            field_kwargs = extra_kwargs.get(field_name, {}).copy()

            # Add read_only if specified
            if field_name in read_only_fields:
                field_kwargs["read_only"] = True

            # Create appropriate serializer field based on DTO field type
            serializer_field = self._create_field_for_dto_field(field_type, field_kwargs)

            self.fields[field_name] = serializer_field

    def _create_field_for_dto_field(self, field_type, field_kwargs: dict[str, Any]) -> serializers.Field:
        """
        Create appropriate serializer field for a DTO field type.

        Args:
            field_type: Type annotation from type hints
            field_kwargs: Extra kwargs from Meta.extra_kwargs

        Returns:
            Serializer field instance
        """

        # Check if it's a nested DTO (ends with 'DTO')
        if self._is_dto_type(field_type):
            # Nested DTO - serialize as dict to avoid recursion issues
            # The to_representation method will handle converting the DTO to a dict
            is_many = self._is_many_relationship(field_type)

            field_kwargs.setdefault("allow_null", True)
            field_kwargs.setdefault("required", False)

            # Use SerializerMethodField to manually serialize nested DTOs
            if is_many:
                return serializers.ListField(child=serializers.DictField(), **field_kwargs)
            else:
                return serializers.DictField(**field_kwargs)

        # Map Python types to DRF field types
        type_map = {
            int: serializers.IntegerField,
            str: serializers.CharField,
            bool: serializers.BooleanField,
            float: serializers.FloatField,
            dict: serializers.DictField,
            list: serializers.ListField,
        }

        # Get base type (unwrap Optional)
        base_type = self._get_base_type(field_type)

        # Get appropriate field class
        field_class = type_map.get(base_type, serializers.CharField)

        # Set common kwargs
        field_kwargs.setdefault("allow_null", True)
        field_kwargs.setdefault("required", False)

        # For ListField, don't pass unexpected kwargs
        if field_class == serializers.ListField:
            # Remove kwargs that ListField doesn't support
            field_kwargs.pop("max_length", None)
            field_kwargs.pop("min_length", None)

        return field_class(**field_kwargs)

    def _is_dto_type(self, field_type: Any) -> bool:
        """Check if a type annotation represents a DTO."""
        from typing import get_args, get_origin

        # Unwrap Optional and List
        origin = get_origin(field_type)
        if origin is not None:
            args = get_args(field_type)
            if args:
                field_type = args[0]
                # Unwrap again for Optional[List[DTO]]
                inner_origin = get_origin(field_type)
                if inner_origin is not None:
                    inner_args = get_args(field_type)
                    if inner_args:
                        field_type = inner_args[0]

        # Check if type name ends with 'DTO'
        if hasattr(field_type, "__name__"):
            return bool(str(field_type.__name__).endswith("DTO"))

        return False

    def _is_many_relationship(self, field_type: Any) -> bool:
        """Check if a relationship is one-to-many (List[DTO])."""
        from typing import get_args, get_origin

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

    def _extract_dto_class(self, field_type: Any) -> type:
        """Extract the DTO class from a type annotation."""
        from typing import cast, get_args, get_origin

        # Handle Optional[T] or List[T]
        origin = get_origin(field_type)
        if origin is not None:
            args = get_args(field_type)
            if args:
                inner_type = args[0]
                # If it's Optional[List[DTO]], go one level deeper
                inner_origin = get_origin(inner_type)
                if inner_origin is list:
                    inner_args = get_args(inner_type)
                    if inner_args:
                        return cast(type, inner_args[0])
                return cast(type, inner_type)

        # Direct DTO type
        return cast(type, field_type)

    def _get_base_type(self, field_type: Any) -> type:
        """Get base type, unwrapping Optional."""
        from typing import cast, get_args, get_origin

        origin = get_origin(field_type)
        if origin is not None:
            args = get_args(field_type)
            if args:
                # Return first non-None type
                for arg in args:
                    if arg is not type(None):
                        return cast(type, arg)

        return field_type if isinstance(field_type, type) else str

    def to_representation(self, instance):
        """
        Convert DTO instance to dictionary, handling UNSET fields.

        UNSET fields are omitted from the output entirely.

        Args:
            instance: DTO instance

        Returns:
            Dictionary representation
        """
        if not is_dataclass(instance):
            raise ValueError(f"Expected dataclass instance, got {type(instance)}")

        data = {}

        for field_name, field in self.fields.items():
            if not hasattr(instance, field_name):
                continue

            value = getattr(instance, field_name)

            # Skip UNSET fields - they're not included in the response
            if value is UNSET:
                continue

            # Handle nested DTOs - convert them to dicts recursively
            if is_dataclass(value):
                data[field_name] = self._dto_to_dict(value)
            elif isinstance(value, list) and value and is_dataclass(value[0]):
                # List of DTOs
                data[field_name] = [self._dto_to_dict(item) for item in value]
            elif value is None and (getattr(field, "many", False) or isinstance(field, serializers.ListField)):
                # Handle None values for list fields
                data[field_name] = None
            elif value is None:
                # Handle other None values
                data[field_name] = None
            else:
                # Use standard field serialization
                data[field_name] = field.to_representation(value)

        return data

    def _dto_to_dict(self, dto_instance):
        """
        Recursively convert a DTO to a dictionary.

        For nested DTOs, this method tries to find and use their corresponding
        serializers to apply field exclusions (like password hiding).

        Args:
            dto_instance: DTO instance to convert

        Returns:
            Dictionary representation
        """
        if not is_dataclass(dto_instance):
            return dto_instance

        # Try to find exclusions for this DTO type
        dto_class = type(dto_instance)
        dto_class_name = dto_class.__name__

        # Check if the DTO class itself has _excluded_fields attribute
        excluded_fields = set()
        if hasattr(dto_class, "_excluded_fields"):
            excluded_fields = set(dto_class._excluded_fields)
        else:
            # Try to import and use the corresponding serializer
            # Common pattern: UserDTO -> UserDTOSerializer
            try:
                # Try to get the serializer from the current module's parent
                import importlib

                # Get the module where the DTO is defined
                dto_module_name = dto_class.__module__

                # Try common patterns for serializer modules
                # Example: blog.selectors.blog_post -> blog.dto_serializers
                base_module = (
                    dto_module_name.split(".selectors.")[0]
                    if ".selectors." in dto_module_name
                    else dto_module_name.rsplit(".", 1)[0]
                )

                possible_serializer_modules = [
                    base_module + ".dto_serializers",
                    dto_module_name.rsplit(".", 1)[0] + ".dto_serializers",
                    dto_module_name.replace("_selector", "_dto_serializers"),
                ]

                serializer_class_name = dto_class_name + "Serializer"

                for module_name in possible_serializer_modules:
                    try:
                        module = importlib.import_module(module_name)
                        if hasattr(module, serializer_class_name):
                            serializer_class = getattr(module, serializer_class_name)
                            if hasattr(serializer_class, "Meta") and hasattr(serializer_class.Meta, "exclude"):
                                excluded_fields = set(serializer_class.Meta.exclude or [])
                                break
                    except (ImportError, AttributeError):
                        continue
            except (ImportError, AttributeError, TypeError, ValueError):
                # If anything fails, just continue without exclusions
                pass

        result = {}
        for field in dataclass_fields(dto_instance):
            # Skip excluded fields (e.g., password)
            if field.name in excluded_fields:
                continue

            value = getattr(dto_instance, field.name)

            # Skip UNSET fields
            if value is UNSET:
                continue

            # Recursively handle nested DTOs
            if is_dataclass(value):
                result[field.name] = self._dto_to_dict(value)
            elif isinstance(value, list) and value and is_dataclass(value[0]):
                result[field.name] = [self._dto_to_dict(item) for item in value]
            else:
                result[field.name] = value

        return result

    def to_internal_value(self, data):
        """
        Validate and convert input data.

        This is used for POST/PUT/PATCH requests.

        Args:
            data: Input dictionary

        Returns:
            Validated data dictionary
        """
        # Use standard DRF validation
        return super().to_internal_value(data)
