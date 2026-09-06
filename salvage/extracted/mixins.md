# `mixins`

## Module docstring

```
Mixin classes for adding OData functionality to Django REST Framework components.
```

## API surface

- `ODataSerializerMixin()`
  > ODataSerializerMixin
  - `get_odata_context(self)`
    > Get OData context information for the serializer. Returns: Dictionary containing OData context
  - `to_representation(self, instance)`
    > Add OData-specific representation logic.
- `ODataMixin()`
  > ODataMixin
  - `get_odata_query_params(self)`
    > Extract and parse OData query parameters from the request. Returns: Dictionary containing parsed OData query parameters
  - `apply_odata_query(self, queryset)`
    > Apply OData query parameters to the queryset. Args: queryset: Base queryset to filter Returns: Filtered and ordered queryset Raises: ODataFilterError: If filter parsing or execution fails
  - `get_queryset(self)`
    > Get the queryset with OData query parameters applied and optimized for field selection and expanded relations.
  - `_apply_odata_optimizations(self, queryset)`
    > Apply OData optimizations using the extracted optimization functions. This method replaces the inline optimization logic with calls to the extracted functions for better maintainability and reusability.
  - `_validate_expand_fields(self, expand_fields, model)`
    > Validate that expand fields exist on the model. Args: expand_fields: Dictionary of fields to expand model: Django model class Raises: ODataExpandError: If any expand field doesn't exist
  - `get_serializer_context(self)`
    > Add OData context to serializer.
  - `list(self, request, *args, **kwargs)`
    > Enhanced list method with OData response formatting.
  - `retrieve(self, request, *args, **kwargs)`
    > Enhanced retrieve method with OData response formatting.
  - `metadata(self, request)`
    > Return OData metadata document.
  - `service_document(self, request)`
    > Return OData service document.

## String constants

Templates and messages, in definition order.

### in `ODataSerializerMixin`

```

    Mixin for serializers to add OData-specific functionality.
    
```

### in `ODataMixin`

```

    Mixin for ViewSets to add OData query support.
    
```

### in `apply_odata_query`

```
Error applying OData query: 
```

### in `apply_odata_query`

```
Unexpected error processing OData query: 
```

### in `_apply_odata_optimizations`

```
Error parsing $expand parameter: 
```

### in `_apply_odata_optimizations`

```
given in select_related:
```

### in `_apply_odata_optimizations`

```
invalid parameter to prefetch_related
```

### in `retrieve`

```
The requested resource was not found.
```

### in `metadata`

```
No model class found for metadata generation.
```

### in `metadata`

```
Error generating metadata: 
```

### in `metadata`

```
Error generating metadata document.
```

### in `service_document`

```
No model class found for service document generation.
```

### in `service_document`

```
Error generating service document: 
```

### in `service_document`

```
Error generating service document.
```

