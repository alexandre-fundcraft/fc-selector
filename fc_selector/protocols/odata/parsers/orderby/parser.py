"""
OData $orderby Parser.

Parses $orderby parameter which specifies sorting order.
Example: "name desc,age" → [('name', 'desc'), ('age', 'asc')]
"""

from typing import Literal

OrderDirection = Literal["asc", "desc"]


def parse_orderby(value: str) -> list[tuple[str, OrderDirection]]:
    """
    Parse OData $orderby parameter.

    Args:
        value: The $orderby value string (e.g., "name desc,age asc")

    Returns:
        List of tuples (field_name, direction) where direction is 'asc' or 'desc'

    Examples:
        >>> parse_orderby("name desc")
        [('name', 'desc')]

        >>> parse_orderby("name desc,age")
        [('name', 'desc'), ('age', 'asc')]

        >>> parse_orderby("title, author desc, published_date asc")
        [('title', 'asc'), ('author', 'desc'), ('published_date', 'asc')]
    """
    if not value or not value.strip():
        return []

    fields: list[tuple[str, OrderDirection]] = []
    for field in value.split(","):
        field = field.strip()
        if field.endswith(" desc"):
            fields.append((field[:-5].strip(), "desc"))
        elif field.endswith(" asc"):
            fields.append((field[:-4].strip(), "asc"))
        else:
            fields.append((field, "asc"))

    return fields
