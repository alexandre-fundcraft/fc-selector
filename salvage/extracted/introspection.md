# `introspection`

## Module docstring

```
Model introspection utilities for SPECKIT-008: Auto-Generate OData Serializers.

This module provides utilities to extract comprehensive metadata from Django models,
including fields, relationships, and properties.
```

## API surface

- `FieldInfo()`
  > FieldInfo
- `RelationshipInfo()`
  > RelationshipInfo
- `get_model_fields(model_class)`
  > Extract all fields from a Django model. Includes database fields, foreign keys, many-to-many, and one-to-one fields. Excludes auto-created reverse relations. Args: model_class: Django model class Returns: List of FieldInfo objects
- `get_model_properties(model_class)`
  > Extract @property decorated methods from a Django model. Args: model_class: Django model class Returns: List of property names
- `get_model_relationships(model_class)`
  > Extract all relationships from a Django model. Includes forward relationships (FK, M2M, O2O) and reverse relationships. Args: model_class: Django model class Returns: List of RelationshipInfo objects
- `get_all_model_info(model_class)`
  > Get comprehensive metadata for a Django model. Args: model_class: Django model class Returns: Dictionary with 'fields', 'relationships', and 'properties' keys

## String constants

Templates and messages, in definition order.

### in `FieldInfo`

```
Information about a model field.
```

### in `RelationshipInfo`

```
Information about a model relationship.
```

