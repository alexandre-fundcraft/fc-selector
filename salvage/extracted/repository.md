# `repository`

## Module docstring

```
OData Repository

Repository layer for executing OData queries on Django models.
Provides a clean interface for using OData queries in repositories,
use cases, and any code that needs QuerySets.
```

## API surface

- `ODataRepository()`
  > ODataRepository
  - `__init__(self, model_class)`
    > Initialize repository. Args: model_class: Optional Django model. Can be set per-query if not provided.
  - `query(self, query_string, model_class, base_queryset)`
    > Execute OData query and return QuerySet. Args: query_string: OData query string (e.g., "$filter=status eq 'published'&$expand=author") model_class: Django model (overrides __init__ value) base_queryset: Optional base QuerySet to filter (default: Model.objects.all()) Returns: Optimized Django QuerySe
  - `query_from_request(self, request, model_class, base_queryset)`
    > Query from Django/DRF request. Args: request: Django/DRF request object model_class: Django model (overrides __init__ value) base_queryset: Optional base QuerySet to filter Returns: Optimized Django QuerySet
  - `count(self, query_string, model_class)`
    > Get count of matching records. Args: query_string: OData query string model_class: Django model (overrides __init__ value) Returns: Count of matching records Example: >>> repo = ODataRepository(BlogPost) >>> published_count = repo.count("$filter=status eq 'published'")
  - `exists(self, query_string, model_class)`
    > Check if any records match. Args: query_string: OData query string model_class: Django model (overrides __init__ value) Returns: True if any records match, False otherwise Example: >>> repo = ODataRepository(BlogPost) >>> has_drafts = repo.exists("$filter=status eq 'draft'")
  - `first(self, query_string, model_class)`
    > Get first matching record. Args: query_string: OData query string model_class: Django model (overrides __init__ value) Returns: First matching record or None Example: >>> repo = ODataRepository(BlogPost) >>> latest_post = repo.first("$orderby=created_at desc")
  - `get_list(self, query_string, model_class, base_queryset)`
    > Get evaluated list of objects. Args: query_string: OData query string model_class: Django model (overrides __init__ value) base_queryset: Optional base QuerySet to filter Returns: List of model instances Example: >>> repo = ODataRepository(BlogPost) >>> posts_list = repo.get_list("$filter=status eq 

## String constants

Templates and messages, in definition order.

### in `ODataRepository`

```

    Repository for executing OData queries on Django models.

    Provides a clean interface for using OData queries in repositories,
    use cases, and any code that needs QuerySets. This class leverages
    the existing odata-query library for parsing and filtering, combined
    with custom optimization logic for field selection and eager loading.

    Examples:
        >>> # Basic usage
        >>> repo = ODataRepository(BlogPost)
        >>> posts = repo.query("$filter=status eq 'published'&$expand=author")

        >>> # With business logic
        >>> base_qs = BlogPost.objects.filter(featured=True)
        >>> posts = repo.query("$filter=rating gt 4.0", base_queryset=base_qs)

        >>> # Helper methods
        >>> count = repo.count("$filter=status eq 'published'")
        >>> exists = repo.exists("$filter=title eq 'My Post'")
        >>> first_post = repo.first("$orderby=created_at desc")
    
```

