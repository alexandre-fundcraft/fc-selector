# `serializers`

## Module docstring

```
OData-compatible serializers with native field selection and expansion.
```

## API surface

- `ODataSerializer()`
  > ODataSerializer
- `ODataModelSerializer()`
  > ODataModelSerializer
  - `to_representation(self, instance)`
    > Add OData-specific representation logic and apply nested query options to expanded related objects. This method intercepts the serialization process to apply OData query options ($filter, $orderby, $top, $skip, $count) to expanded related fields before they are serialized.
  - `get_field_info(self)`
    > Get detailed field information for metadata generation. Returns: Dictionary mapping field names to field metadata
  - `_get_odata_type(self, field)`
    > Map DRF field types to OData types. Args: field: DRF field instance Returns: OData type string
  - `_get_collection_type(self, field)`
    > Get the OData collection type for ListField based on child field type. Args: field: ListField instance Returns: OData collection type string
  - `get_navigation_properties(self)`
    > Get navigation property information from expandable_fields. Returns: Dictionary mapping navigation property names to metadata
  - `Meta()`
    > ODataModelSerializer.Meta
- `ODataListSerializer()`
  > ODataListSerializer
  - `to_representation(self, data)`
    > Add OData collection formatting.
  - `_get_context_url(self)`
    > Generate OData context URL for collections.
- `create_odata_serializer(model_class, fields, expandable_fields, **kwargs)`
  > Factory function to create OData serializers for Django models. Args: model_class: Django model class fields: Fields to include in serialization expandable_fields: Dictionary of expandable field configurations **kwargs: Additional serializer options Returns: ODataModelSerializer subclass for the mod

## String constants

Templates and messages, in definition order.

### in `ODataSerializer`

```

    Base OData serializer with native field selection and expansion.

    This serializer provides:
    - Dynamic field selection via $select parameter
    - Field expansion via $expand parameter
    - OData context information
    - Support for OData query options

    The serializer uses native implementations instead of drf-flex-fields,
    providing better performance and simpler maintenance.
    
```

### in `ODataModelSerializer`

```

    OData-compatible model serializer with native field selection and expansion.

    This serializer provides:
    - Dynamic field selection via $select parameter
    - Field expansion via $expand parameter
    - OData context information
    - Support for OData query options ($select, $expand)
    - Automatic field type detection for metadata generation

    The serializer uses native implementations instead of drf-flex-fields,
    providing better performance and simpler maintenance.
    
```

### in `to_representation`

```
_expanded_fields_data
```

### in `to_representation`

```
Error applying OData query options to expanded field '
```

### in `_get_collection_type`

```
Collection(Edm.String)
```

### in `ODataListSerializer`

```

    Custom list serializer for OData collections.
    
```

