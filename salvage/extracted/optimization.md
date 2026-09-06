# `optimization`

## Module docstring

```
OData QuerySet Optimization Functions

Extracted from ODataMixin to provide reusable QuerySet optimization logic
that can be used independently of DRF serializers and views.
```

## API surface

- `optimize_queryset_for_select(queryset, select_fields, expand_fields)`
  > Apply .only() optimization for field selection. This optimization reduces data transfer from database to application by fetching only the fields specified in the $select parameter. Algorithm: 1. If no $select, return queryset unchanged (fetch all fields) 2. Parse selected fields 3. Add model's prima
- `optimize_queryset_for_expand(queryset, expand_fields)`
  > Automatically optimize queryset for expanded relations using select_related and prefetch_related. This method detects $expand parameters and applies appropriate eager loading to prevent N+1 queries. Args: queryset: Base queryset to optimize expand_fields: Dictionary mapping field names to their ODat
- `build_only_fields_list(model, selected_fields, expand_fields)`
  > Build list of fields for .only() method. Must include: - Requested fields from $select - Model's primary key (Django requirement) - Foreign key fields for expanded relations (Django requirement) Args: model: Django model class selected_fields: List of field names from $select parameter expand_fields
- `categorize_relations(model, field_names)`
  > Categorize fields into select_related vs prefetch_related. Args: model: Django model class field_names: List of field names to categorize Returns: Tuple of (select_related_fields, prefetch_related_fields) Examples: >>> categorize_relations(BlogPost, ['author', 'categories']) (['author'], ['categorie
- `is_forward_relation(model, field_name)`
  > Check if field is a forward relation (ForeignKey/OneToOne). Args: model: Django model class field_name: Name of the field to check Returns: True if forward relation, False otherwise
- `apply_query_optimizations(queryset, select_related_fields, prefetch_related_fields, expand_fields)`
  > Apply select_related and prefetch_related with field selection optimizations. Args: queryset: Base queryset select_related_fields: Fields to select_related prefetch_related_fields: Fields to prefetch_related expand_fields: Dictionary of expanded fields with options Returns: Queryset with optimizatio
- `apply_related_field_selection(queryset, select_related_fields, expand_fields)`
  > Apply field selection to select_related fields using only(). For each related field, determine which fields to fetch based on nested $select in $expand parameter. Args: queryset: Queryset with select_related already applied select_related_fields: List of field names that were select_related expand_f
- `apply_prefetch_field_selection(queryset, prefetch_related_fields, expand_fields)`
  > Apply field selection to prefetch_related fields using Prefetch objects. For each prefetch_related field, create a Prefetch object with a custom queryset that uses only() to limit fields based on nested $select. Args: queryset: Queryset with prefetch_related already applied prefetch_related_fields: 
- `get_existing_only_fields(queryset)`
  > Extract existing only() fields from queryset. Args: queryset: Django queryset Returns: List of field names currently in only(), or empty list Examples: >>> qs = Model.objects.only('id', 'name') >>> get_existing_only_fields(qs) ['id', 'name']

## String constants

Templates and messages, in definition order.

### in `optimize_queryset_for_select`

```
Applied field selection optimization: only(
```

### in `build_only_fields_list`

```
Skipping non-database field '
```

### in `build_only_fields_list`

```
Could not add FK for '
```

### in `<module>`

```
select_related_fields
```

### in `<module>`

```
prefetch_related_fields
```

### in `apply_related_field_selection`

```
' for related model '
```

### in `apply_related_field_selection`

```
Added related field selection for '
```

### in `apply_related_field_selection`

```
Could not optimize fields for 
```

### in `apply_related_field_selection`

```
Added nested FK field '
```

### in `apply_related_field_selection`

```
' for deep expansion of '
```

### in `apply_related_field_selection`

```
Could not add nested FK for '
```

### in `apply_related_field_selection`

```
Applied related field selection: only(
```

### in `apply_prefetch_field_selection`

```
' for prefetch model '
```

### in `apply_prefetch_field_selection`

```
Created Prefetch for '
```

### in `apply_prefetch_field_selection`

```
Could not find related model for prefetch field '
```

### in `apply_prefetch_field_selection`

```
Could not optimize prefetch for 
```

### in `apply_prefetch_field_selection`

```
Applied prefetch field selection with 
```

