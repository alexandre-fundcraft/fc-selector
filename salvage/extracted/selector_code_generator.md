# `selector_code_generator`

## Module docstring

```
Code generator for OData Selectors with DTOs.

This module provides utilities to generate syntactically valid Python selector and DTO code
from model metadata, following the pattern of code_generator.py for serializers.
```

## API surface

- `generate_sentinel()`
  > Generate sentinel class definition. NOTE: This is deprecated - sentinel is now imported from BaseODataDTO. Kept for backward compatibility but will be removed in future versions. Returns: Empty string (sentinel imported instead)
- `generate_dto_imports(model_class, app_label)`
  > Generate import statements for DTOs. Args: model_class: Django model class app_label: App label for the model Returns: String containing import statements
- `generate_selector_imports(app_label)`
  > Generate import statements for selectors. Args: app_label: App label for the selector Returns: String containing import statements
- `generate_regeneration_command(app_label, model_name, single)`
  > Generate appropriate regeneration command based on context. Args: app_label: App label for the model model_name: Model name single: Whether the file was generated with --single option Returns: String containing the regeneration command
- `generate_dto_fields(fields, relationships, model_class)`
  > Generate field definitions for DTO dataclass. Args: fields: List of FieldInfo objects relationships: List of RelationshipInfo objects model_class: Django model class (for detecting self-references) Returns: String containing dataclass field definitions
- `generate_dto_from_model_method(fields, relationships, models_in_file)`
  > Generate from_model() classmethod for DTO using automatic field introspection. Args: fields: List of FieldInfo objects relationships: List of RelationshipInfo objects models_in_file: Set of model paths being generated in the same file Returns: String containing from_model() method
- `generate_dto_class(model_class, fields, relationships, models_in_file)`
  > Generate complete DTO dataclass code. Now generates DTOs that inherit from BaseODataDTO for automatic conversion. No explicit from_model() method is generated - it's inherited from the base class. Args: model_class: Django model class fields: List of FieldInfo objects relationships: List of Relation
- `generate_selector_expandable_fields(relationships, exclude_edges, app_label)`
  > Generate the expandable_fields dict for Selector Meta class. Args: relationships: List of RelationshipInfo objects exclude_edges: Set of edges to exclude from expandable_fields app_label: App label for the model Returns: String containing Python dict with proper indentation
- `generate_selector_class(model_class, app_label, relationships, exclude_edges)`
  > Generate complete selector class code. Args: model_class: Django model class app_label: App label for the model relationships: List of RelationshipInfo objects exclude_edges: Set of edges to exclude Returns: String containing complete selector class definition
- `generate_selector_file(model_class, app_label, fields, relationships, exclude_edges, single, models_in_file)`
  > Generate complete selector file with DTOs and Selectors. Args: model_class: Django model class app_label: App label for the model fields: List of FieldInfo objects relationships: List of RelationshipInfo objects exclude_edges: Set of edges to exclude single: Whether the file was generated with --sin
- `format_python_code(code)`
  > Format and validate Python code. Args: code: Python code string Returns: Formatted Python code Raises: SyntaxError: If code is not valid Python

## String constants

Templates and messages, in definition order.

### in `generate_dto_imports`

```


```

### in `generate_selector_imports`

```
from django_odata.django.selector import ODataSelector
```

### in `generate_regeneration_command`

```
python manage.py generate_odata_selector 
```

### in `generate_dto_fields`

```
 = UNSET  # @property
```

### in `generate_dto_from_model_method`

```
    def from_model(cls, instance, selected_fields=None, expanded_fields=None):
```

### in `generate_dto_from_model_method`

```
        Create DTO from model instance with automatic field selection.
```

### in `generate_dto_from_model_method`

```
        Uses introspection to populate only selected fields, avoiding
```

### in `generate_dto_from_model_method`

```
        explicit code generation for each field.
```

### in `generate_dto_from_model_method`

```
        from dataclasses import fields as dataclass_fields
```

### in `generate_dto_from_model_method`

```
        expanded_fields = expanded_fields or set()
```

### in `generate_dto_from_model_method`

```
        # Get all DTO fields
```

### in `generate_dto_from_model_method`

```
        dto_fields = {f.name for f in dataclass_fields(cls)}
```

### in `generate_dto_from_model_method`

```
        # Determine which fields to populate
```

### in `generate_dto_from_model_method`

```
        if selected_fields is None:
```

### in `generate_dto_from_model_method`

```
            fields_to_populate = dto_fields
```

### in `generate_dto_from_model_method`

```
            fields_to_populate = dto_fields & selected_fields
```

### in `generate_dto_from_model_method`

```
        # Relationship field names
```

### in `generate_dto_from_model_method`

```
        relationship_fields = {
```

### in `generate_dto_from_model_method`

```
        # Populate regular fields
```

### in `generate_dto_from_model_method`

```
        for field_name in fields_to_populate - relationship_fields:
```

### in `generate_dto_from_model_method`

```
            if hasattr(instance, field_name):
```

### in `generate_dto_from_model_method`

```
                data[field_name] = getattr(instance, field_name)
```

### in `generate_dto_from_model_method`

```
        # Handle relationships
```

### in `generate_dto_from_model_method`

```
' in fields_to_populate:
```

### in `generate_dto_from_model_method`

```
' in expanded_fields:
```

### in `generate_dto_from_model_method`

```
                related_objs = list(instance.
```

### in `generate_dto_from_model_method`

```
                data['
```

### in `generate_dto_from_model_method`

```
.from_model(obj) for obj in related_objs]
```

### in `generate_dto_from_model_method`

```
                if hasattr(instance, '
```

### in `generate_dto_from_model_method`

```
                    data['
```

### in `generate_dto_from_model_method`

```
.from_model(instance.
```

### in `generate_dto_from_model_method`

```
                else:
```

### in `generate_dto_from_model_method`

```
                # Not expanded, store FK ID or None
```

### in `generate_dto_from_model_method`

```
'] = getattr(instance, '
```

### in `generate_dto_from_model_method`

```
        return cls(**data)
```

### in `generate_dto_class`

```

@dataclass
class 
```

### in `generate_dto_class`

```
(BaseODataDTO):
    """DTO for 
```

### in `generate_dto_class`

```
 model."""

```

### in `generate_selector_class`

```

class 
```

### in `generate_selector_class`

```
(ODataSelector):
    """Selector for 
```

### in `generate_selector_class`

```
 with DTO support."""

    class Meta:
        model = 
```

### in `generate_selector_class`

```

        dto_class = 
```

### in `generate_selector_class`

```

        expandable_fields = 
```

### in `generate_selector_file`

```
"""
Auto-generated Selector and DTO for 
```

### in `generate_selector_file`

```
 model.
Generated on: 
```

### in `generate_selector_file`

```


DO NOT EDIT THIS FILE MANUALLY.
Regenerate using: 
```

### in `generate_selector_file`

```


Available options:
  --single   Generate one combined file instead of separate files
  --force    Overwrite existing files without prompting
"""

```

### in `generate_selector_file`

```



```

### in `generate_selector_file`

```



# ==================== DTOs ====================

```

### in `generate_selector_file`

```


# ==================== SELECTORS ====================

```

### in `format_python_code`

```
Generated code has syntax error: 
```

