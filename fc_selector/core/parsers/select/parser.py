"""
OData $select Parser.

Parses $select parameter which specifies field selection.
Example: "name,age,posts" → ['name', 'age', 'posts']
"""



def parse_select(value: str) -> list[str]:
    """
    Parse OData $select parameter.

    Args:
        value: The $select value string (e.g., "name,age,email")

    Returns:
        List of field names to select

    Examples:
        >>> parse_select("name,age")
        ['name', 'age']

        >>> parse_select("title, author, published_date")
        ['title', 'author', 'published_date']

        >>> parse_select("id")
        ['id']
    """
    if not value or not value.strip():
        return []

    # Split by comma and strip whitespace
    fields = [f.strip() for f in value.split(",") if f.strip()]
    return fields
