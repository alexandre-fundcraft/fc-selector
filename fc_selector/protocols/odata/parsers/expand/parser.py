"""
OData $expand Parser.

Parses $expand parameter which specifies related entities to include.
Example: "posts,comments($select=text)" → {'posts': {}, 'comments': {'$select': 'text'}}
"""

from typing import Any


def parse_expand(value: str) -> dict[str, dict[str, Any]]:
    """
    Parse OData $expand parameter.

    Args:
        value: The $expand value string (e.g., "posts,comments($select=text)")

    Returns:
        Dictionary mapping field names to their nested options

    Examples:
        >>> parse_expand("posts")
        {'posts': {}}

        >>> parse_expand("posts,comments")
        {'posts': {}, 'comments': {}}

        >>> parse_expand("posts($select=title,author)")
        {'posts': {'$select': 'title,author'}}

        >>> parse_expand("posts($select=title;$top=5)")
        {'posts': {'$select': 'title', '$top': '5'}}
    """
    if not value or not value.strip():
        return {}

    result = {}
    current_field = ""
    paren_depth = 0

    # Add trailing separator to ensure last field is processed
    for char in value + ",":
        if char == "(":
            paren_depth += 1
            current_field += char
        elif char == ")":
            paren_depth -= 1
            current_field += char
        elif (char in {",", ";"}) and paren_depth == 0:
            # Both comma and semicolon are valid separators
            if current_field.strip():
                field_name, options = _parse_single_expand_field(current_field.strip())
                result[field_name] = options
            current_field = ""
        else:
            current_field += char

    return result


def _parse_single_expand_field(field: str) -> tuple[str, dict[str, Any]]:
    """
    Parse a single expand field expression.

    Args:
        field: Single expand field (e.g., "posts" or "posts($select=title)")

    Returns:
        Tuple of (field_name, options_dict)
    """
    field = field.strip()

    if "(" not in field:
        return field, {}

    field_name = field.split("(")[0].strip()
    start_paren = field.find("(")
    end_paren = field.rfind(")")

    if start_paren == -1 or end_paren == -1:
        return field, {}

    inner_content = field[start_paren + 1 : end_paren]
    options = _parse_query_options(inner_content)

    return field_name, options


def _parse_query_options(options_string: str) -> dict[str, Any]:
    """
    Parse query options from parentheses content.

    Args:
        options_string: Content inside parentheses (e.g., "$select=title;$top=5")

    Returns:
        Dictionary of parsed options
    """
    if not options_string or not options_string.strip():
        return {}

    options = {}
    current_option = ""
    paren_depth = 0

    for char in options_string + ";":
        if char == "(":
            paren_depth += 1
            current_option += char
        elif char == ")":
            paren_depth -= 1
            current_option += char
        elif char == ";" and paren_depth == 0:
            if current_option.strip():
                key, value = _parse_single_query_option(current_option.strip())
                if key:
                    options[key] = value
            current_option = ""
        else:
            current_option += char

    return options


def _parse_single_query_option(option: str) -> tuple[str, str]:
    """
    Parse a single query option.

    Args:
        option: Single option string (e.g., "$select=title,author")

    Returns:
        Tuple of (key, value)
    """
    if "=" not in option:
        return "", ""

    key, value = option.split("=", 1)
    key = key.strip()
    value = value.strip()

    if not key.startswith("$"):
        return "", ""

    return key, value
