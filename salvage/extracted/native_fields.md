# `native_fields`

## Module docstring

```
Native field selection and expansion for OData serializers.

This module provides native implementations to replace drf-flex-fields dependency,
offering better performance and simpler maintenance while maintaining full API compatibility.
```

## API surface

- `parse_select_fields(select_string)`
  > Parse OData $select parameter into field structure. Handles both simple field selection and nested field selection for expanded properties. Args: select_string: Comma-separated list of field names, may include dots for nested fields Example: "id,title,author.name,author.email" Returns: Dictionary wi
- `parse_expand_fields(expand_string)`
  > Parse OData $expand parameter into expansion structure. Supports: - Simple expansion: "author" - Multiple expansions: "author,categories" - Nested $select: "author($select=name,email)" - Mixed: "author($select=name),categories" Args: expand_string: OData $expand expression Returns: Dictionary mappin
- `_parse_single_expand_field(field)`
  > Parse a single expand field expression. Args: field: Single expand expression, e.g., "author" or "author($select=name,email)" Returns: Tuple of (field_name, nested_select_string or None) Examples: >>> _parse_single_expand_field("author") ('author', None) >>> _parse_single_expand_field("author($selec
- `NativeFieldSelectionMixin()`
  > NativeFieldSelectionMixin
  - `__init__(self, *args, **kwargs)`
    > Initialize serializer and apply field selection.
  - `_apply_field_selection(self)`
    > Apply $select parameter to filter serializer fields. Algorithm: 1. Get $select from context['odata_params'] 2. If no $select, return (show all fields) 3. Parse field list (handle dots for nested fields) 4. For top-level fields, keep only selected ones 5. Store nested selections in context for child 
- `NativeFieldExpansionMixin()`
  > NativeFieldExpansionMixin
  - `__init__(self, *args, **kwargs)`
    > Initialize serializer and apply field expansion.
  - `_apply_field_expansion(self)`
    > Apply $expand parameter to add related serializers. Algorithm: 1. Get $expand from context['odata_params'] 2. Check expansion depth to prevent infinite recursion 3. Parse expansion expressions (handle nested query options) 4. For each expansion: a. Look up serializer in Meta.expandable_fields b. Cre
  - `_parse_serializer_config(self, config)`
    > Parse expandable_fields configuration. Supports two formats: 1. Tuple: (SerializerClass, {'many': True}) 2. Just the class: SerializerClass Args: config: Configuration from Meta.expandable_fields Returns: Tuple of (serializer_class, options_dict)
  - `_import_serializer_class(self, class_path)`
    > Import a serializer class from a string path. Args: class_path: Dotted path to serializer class, e.g., 'myapp.serializers.AuthorSerializer' Returns: The serializer class Raises: ImportError: If the class cannot be imported

## String constants

Templates and messages, in definition order.

### in `_parse_single_expand_field`

```
Malformed expand expression: 
```

### in `_parse_single_expand_field`

```
Unknown nested expression in expand: 
```

### in `NativeFieldSelectionMixin`

```

    Mixin for native field selection based on OData $select parameter.

    Replaces drf-flex-fields field filtering functionality with a native implementation
    that directly manipulates serializer fields during initialization.

    Usage:
        class MySerializer(NativeFieldSelectionMixin, serializers.ModelSerializer):
            class Meta:
                model = MyModel
                fields = '__all__'

    The mixin reads the $select parameter from context['odata_params'] and filters
    the serializer's fields accordingly.
    
```

### in `<module>`

```
NativeFieldSelectionMixin
```

### in `NativeFieldExpansionMixin`

```

    Mixin for native field expansion based on OData $expand parameter.

    Replaces drf-flex-fields expansion functionality with a native implementation
    that adds related serializers based on Meta.expandable_fields configuration.

    Usage:
        class MySerializer(NativeFieldExpansionMixin, serializers.ModelSerializer):
            class Meta:
                model = MyModel
                fields = '__all__'
                expandable_fields = {
                    'author': (AuthorSerializer, {'many': False}),
                    'categories': (CategorySerializer, {'many': True})
                }

    The mixin reads the $expand parameter from context['odata_params'] and adds
    the appropriate related serializers to the fields.
    
```

### in `_apply_field_expansion`

```
Maximum expansion depth (
```

### in `_apply_field_expansion`

```
) reached, stopping expansion to prevent infinite recursion
```

### in `_apply_field_expansion`

```
No Meta class defined
```

### in `_apply_field_expansion`

```
No expandable_fields defined in Meta
```

### in `_apply_field_expansion`

```
' in $expand is not in expandable_fields, ignoring
```

### in `_apply_field_expansion`

```
Error expanding field '
```

### in `_import_serializer_class`

```
Failed to import serializer class '
```

### in `_import_serializer_class`

```
Cannot import serializer class '
```

### in `<module>`

```
NativeFieldExpansionMixin
```

