"""Django lookup-path translation."""

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
