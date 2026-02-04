"""Field alias resolution utilities for fc_selector."""


def resolve_field_alias(field_name: str, field_aliases: dict[str, str] | None) -> str:
    """Resolve field alias to actual model field name.

    Args:
        field_name: The field name (possibly an alias) to resolve.
                    Can include nested fields separated by "__".
        field_aliases: Dict mapping alias names to actual model field names.
                       If None or empty, returns the original field name.

    Returns:
        The resolved field name with any alias in the first part replaced.

    Examples:
        >>> resolve_field_alias("client_uuid", {"client_uuid": "client_id"})
        'client_id'
        >>> resolve_field_alias("client_uuid__name", {"client_uuid": "client_id"})
        'client_id__name'
        >>> resolve_field_alias("name", {"client_uuid": "client_id"})
        'name'
        >>> resolve_field_alias("name", None)
        'name'
    """
    if not field_aliases:
        return field_name
    # Handle nested fields (e.g., "relation__field")
    parts = field_name.split("__")
    parts[0] = field_aliases.get(parts[0], parts[0])
    return "__".join(parts)
