# `selector`

## Module docstring

```
OData Selector

Selector layer for executing OData queries on Django models.
Provides a clean interface for using OData queries in selectors,
use cases, and any code that needs QuerySets.
```

## API surface

- `ODataSelector()`
  > ODataSelector
  - `__init__(self, model_class)`
    > Initialize selector. Args: model_class: Optional Django model. Can be set per-query if not provided.
  - `query(self, query_string, model_class, base_queryset)`
    > Execute OData query and return QuerySet. Args: query_string: OData query string (e.g., "$filter=status eq 'published'&$expand=author") model_class: Django model (overrides __init__ value) base_queryset: Optional base QuerySet to filter (default: Model.objects.all()) Returns: Optimized Django QuerySe
  - `query_from_request(self, request, model_class, base_queryset)`
    > Query from Django/DRF request. Args: request: Django/DRF request object model_class: Django model (overrides __init__ value) base_queryset: Optional base QuerySet to filter Returns: Optimized Django QuerySet
  - `count(self, query_string, model_class)`
    > Get count of matching records. Args: query_string: OData query string model_class: Django model (overrides __init__ value) Returns: Count of matching records Example: >>> selector = ODataSelector(BlogPost) >>> published_count = selector.count("$filter=status eq 'published'")
  - `exists(self, query_string, model_class)`
    > Check if any records match. Args: query_string: OData query string model_class: Django model (overrides __init__ value) Returns: True if any records match, False otherwise Example: >>> selector = ODataSelector(BlogPost) >>> has_drafts = selector.exists("$filter=status eq 'draft'")
  - `first(self, query_string, model_class)`
    > Get first matching record. Args: query_string: OData query string model_class: Django model (overrides __init__ value) Returns: First matching record or None Example: >>> selector = ODataSelector(BlogPost) >>> latest_post = selector.first("$orderby=created_at desc")
  - `get_list(self, query_string, model_class, base_queryset)`
    > Get evaluated list of objects. Args: query_string: OData query string model_class: Django model (overrides __init__ value) base_queryset: Optional base QuerySet to filter Returns: List of model instances Example: >>> selector = ODataSelector(BlogPost) >>> posts_list = selector.get_list("$filter=stat

## String constants

Templates and messages, in definition order.

### in `ODataSelector`

```

    Selector for executing OData queries on Django models.

    Provides a clean interface for using OData queries in selectors,
    use cases, and any code that needs QuerySets. This class leverages
    the existing odata-query library for parsing and filtering, combined
    with custom optimization logic for field selection and eager loading.

    Examples:
        >>> # Basic usage
        >>> selector = ODataSelector(BlogPost)
        >>> posts = selector.query("$filter=status eq 'published'&$expand=author")

        >>> # With business logic
        >>> base_qs = BlogPost.objects.filter(featured=True)
        >>> posts = selector.query("$filter=rating gt 4.0", base_queryset=base_qs)

        >>> # Helper methods
        >>> count = selector.count("$filter=status eq 'published'")
        >>> exists = selector.exists("$filter=title eq 'My Post'")
        >>> first_post = selector.first("$orderby=created_at desc")
    
```

