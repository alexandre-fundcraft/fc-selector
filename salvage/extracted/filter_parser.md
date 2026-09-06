# `filter_parser`

## Module docstring

```
Custom OData filter parser using Django Q objects.

This module provides a replacement for the odata-query library's filtering functionality.
It parses OData $filter expressions and converts them to Django Q objects.
```

## API surface

- `ODataFilterParser()`
  > ODataFilterParser
  - `__init__(self)`
  - `parse_filter(self, filter_string, queryset)`
    > Parse an OData filter string and return a Django Q object. Args: filter_string: The OData filter expression queryset: Django QuerySet to validate field names against Returns: Django Q object representing the filter Raises: ODataInvalidFilterSyntaxError: If the filter syntax is invalid ODataInvalidOp
  - `_tokenize(self, filter_string)`
    > Tokenize the filter string into individual tokens.
    - `replace_quoted(match)`
  - `_parse_expression(self, queryset)`
    > Parse a logical expression (handles AND/OR/NOT).
  - `_parse_term(self, queryset)`
    > Parse a term (handles NOT and parentheses).
  - `_parse_comparison(self, queryset)`
    > Parse a comparison expression (field operator value or function(field) operator value).
  - `_parse_function_comparison(self, queryset)`
    > Parse function comparison like contains(name,'Python') or tolower(name) eq 'value'.
  - `_parse_value(self, value_token)`
    > Parse a value token into the appropriate Python type.
  - `_validate_field(self, model, field_name)`
    > Validate that a field exists on the model.
- `apply_odata_filter(queryset, filter_string)`
  > Apply an OData filter expression to a Django QuerySet. This is a drop-in replacement for odata_query.django.apply_odata_query. Args: queryset: Django QuerySet to filter filter_string: OData filter expression Returns: Filtered QuerySet Raises: ODataInvalidFilterSyntaxError: If the filter syntax is in

## String constants

Templates and messages, in definition order.

### in `ODataFilterParser`

```

    Parser for OData $filter expressions using Django Q objects.

    Supports basic OData filter operations:
    - Comparison operators: eq, ne, gt, ge, lt, le
    - Logical operators: and, or, not
    - String functions: contains, startswith, endswith
    - Parentheses for grouping
    
```

### in `parse_filter`

```
Unexpected tokens after expression: 
```

### in `_parse_term`

```
Missing closing parenthesis
```

### in `_parse_comparison`

```
Incomplete comparison expression
```

### in `_parse_function_comparison`

```
Expected '(' after function 
```

### in `_parse_function_comparison`

```
Incomplete function comparison expression
```

### in `_parse_function_comparison`

```
Expected ')' after value 
```

### in `_parse_function_comparison`

```
Unexpected token after field 
```

### in `_validate_field`

```
' does not exist on model '
```

