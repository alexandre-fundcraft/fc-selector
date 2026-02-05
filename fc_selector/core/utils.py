"""
Core utility functions for FC Selector.

These are framework-agnostic utilities for common operations like
field name validation and parsing.
"""


def is_private_field(field_name: str) -> bool:
    """
    Check if a field name refers to a private/internal field.

    Private fields start with an underscore and should not be
    accessible through public query APIs.

    Args:
        field_name: The field name to check.

    Returns:
        True if the field is private (starts with '_'), False otherwise.
    """
    return field_name.startswith("_")


def get_base_field(field_path: str, separator: str = "__") -> str:
    """
    Extract the base field name from a field path.

    Field paths can contain separators (like '__' in Django) to indicate
    relationships or lookups. This function returns just the first part.

    Args:
        field_path: The full field path (e.g., 'author__name', 'created_at__year').
        separator: The separator used in field paths. Defaults to '__'.

    Returns:
        The base field name (e.g., 'author' from 'author__name').

    Examples:
        >>> get_base_field("author__name")
        'author'
        >>> get_base_field("simple_field")
        'simple_field'
        >>> get_base_field("path.to.field", separator=".")
        'path'
    """
    return field_path.split(separator)[0]


def odata_path_to_django(odata_path: str) -> str:
    """
    Convert an OData-style path to Django ORM notation.

    OData uses '/' for path navigation, but internally this library
    may also use '.' in some contexts. Both are converted to Django's '__'.

    Args:
        odata_path: OData field path (e.g., 'author/name', 'author.name').

    Returns:
        Django-style field path (e.g., 'author__name').

    Examples:
        >>> odata_path_to_django("author/name")
        'author__name'
        >>> odata_path_to_django("author.name")
        'author__name'
        >>> odata_path_to_django("simple_field")
        'simple_field'
    """
    return odata_path.replace("/", "__").replace(".", "__")
