# `core`

## Module docstring

```
OData Core Functions

Main entry point for applying OData queries to Django QuerySets.
Combines odata-query library with optimization functions.
```

## API surface

- `apply_odata_to_queryset(queryset, query_string, query_params)`
  > Apply OData query to a Django QuerySet with automatic optimizations. This is the main entry point for using OData queries anywhere in your code. It leverages the existing odata-query library for parsing and filtering, combined with custom optimization logic for field selection and eager loading. Arg
- `_apply_optimizations(queryset, query_params)`
  > Apply QuerySet optimizations based on OData parameters. Args: queryset: Base queryset query_params: Parsed OData parameters Returns: Optimized queryset

## String constants

Templates and messages, in definition order.

### in `apply_odata_to_queryset`

```
Unexpected error applying OData query: 
```

