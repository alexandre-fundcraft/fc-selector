# `viewsets`

## Module docstring

```
OData-compatible ViewSets that extend Django REST Framework functionality.
```

## API surface

- `ODataViewSet()`
  > ODataViewSet
  - `get_odata_entity_set_name(self)`
    > Get the entity set name for this viewset. Override this method to provide custom entity set names.
  - `get_odata_entity_type_name(self)`
    > Get the entity type name for this viewset. Override this method to provide custom entity type names.
  - `list(self, request, *args, **kwargs)`
    > Enhanced list method with OData collection formatting.
  - `_get_collection_context_url(self)`
    > Generate OData context URL for collections.
- `ODataModelViewSet()`
  > ODataModelViewSet
  - `get_odata_entity_set_name(self)`
    > Get the entity set name for this model.
  - `get_odata_entity_type_name(self)`
    > Get the entity type name for this model.
  - `perform_create(self, serializer)`
    > Enhanced create with OData support.
  - `perform_update(self, serializer)`
    > Enhanced update with OData support.
  - `create(self, request, *args, **kwargs)`
    > Enhanced create method with OData response formatting.
  - `update(self, request, *args, **kwargs)`
    > Enhanced update method with OData response formatting.
  - `get_navigation_links(self, request, navigation_property, pk)`
    > Get navigation property links for an entity.
  - `get_navigation_property(self, request, navigation_property, pk)`
    > Get navigation property values for an entity.
  - `_get_related_serializer_class(self, navigation_property)`
    > Get the serializer class for a navigation property.
- `ODataReadOnlyModelViewSet()`
  > ODataReadOnlyModelViewSet
  - `get_odata_entity_set_name(self)`
    > Get the entity set name for this model.
  - `get_odata_entity_type_name(self)`
    > Get the entity type name for this model.
- `create_odata_viewset(model_class, serializer_class, read_only, **kwargs)`
  > Factory function to create OData viewsets for Django models. Args: model_class: Django model class serializer_class: Optional custom serializer class read_only: If True, creates a ReadOnlyModelViewSet **kwargs: Additional viewset options Returns: ODataModelViewSet or ODataReadOnlyModelViewSet subcla

## String constants

Templates and messages, in definition order.

### in `ODataViewSet`

```

    Base OData ViewSet that provides OData query support for non-model viewsets.

    This viewset provides:
    - OData query parameter parsing and application
    - OData-formatted responses
    - $metadata endpoint support
    - Service document endpoint support
    
```

### in `ODataModelViewSet`

```

    OData-compatible ModelViewSet that provides full CRUD operations with OData query support.

    This viewset provides:
    - All standard ModelViewSet functionality
    - OData query parameter support ($filter, $orderby, $top, $skip, etc.)
    - Dynamic field selection and expansion
    - OData-formatted responses with proper context
    - $metadata and service document endpoints
    
```

### in `ODataModelViewSet`

```
\$links/(?P<navigation_property>[\w-]+)
```

### in `get_navigation_links`

```
get_navigation_properties
```

### in `get_navigation_links`

```
Navigation property "
```

### in `get_navigation_links`

```
Invalid navigation property access: 
```

### in `ODataModelViewSet`

```
(?P<navigation_property>[\w-]+)
```

### in `ODataReadOnlyModelViewSet`

```

    OData-compatible ReadOnlyModelViewSet for read-only entity sets.

    This viewset provides:
    - Read-only access to model instances
    - OData query parameter support
    - Dynamic field selection and expansion
    - OData-formatted responses
    
```

### in `<module>`

```
ODataReadOnlyModelViewSet
```

