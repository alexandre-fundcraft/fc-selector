"""
Query validation logic for OData queries.

Validates OData query syntax and parameters.
"""


from .models import ODataQuery


class QueryValidator:
    """Validates OData queries."""

    @staticmethod
    def validate_filter_syntax(filter_expr: str) -> bool:
        """Validate filter expression syntax."""
        if not filter_expr:
            return False

        # Basic validation - can be extended
        operators = [
            " eq ",
            " ne ",
            " gt ",
            " ge ",
            " lt ",
            " le ",
            " and ",
            " or ",
            " not ",
        ]
        return any(op in filter_expr for op in operators) or "'" in filter_expr

    @staticmethod
    def validate_select_fields(fields: list) -> bool:
        """Validate select fields."""
        return all(isinstance(f, str) and f.strip() for f in fields)

    @staticmethod
    def validate_orderby_fields(fields: list) -> bool:
        """Validate orderby fields."""
        return all(
            isinstance(f, tuple)
            and len(f) == 2
            and isinstance(f[0], str)
            and f[1] in ("asc", "desc")
            for f in fields
        )

    @staticmethod
    def validate_pagination(top: int = None, skip: int = None) -> bool:
        """Validate pagination parameters."""
        if top is not None and (not isinstance(top, int) or top < 0):
            return False
        if skip is not None and (not isinstance(skip, int) or skip < 0):
            return False
        return True

    @classmethod
    def validate_query(cls, query: ODataQuery) -> tuple[bool, list[str]]:
        """
        Validate complete OData query.

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if query.filter and not cls.validate_filter_syntax(query.filter.value):
            errors.append("Invalid filter syntax")

        if query.select and not cls.validate_select_fields(query.select.fields):
            errors.append("Invalid select fields")

        if query.orderby and not cls.validate_orderby_fields(query.orderby.fields):
            errors.append("Invalid orderby fields")

        if query.top:
            try:
                top_val = int(query.top.value)
                if not cls.validate_pagination(top=top_val):
                    errors.append("Invalid $top value")
            except (ValueError, TypeError):
                errors.append("$top must be an integer")

        if query.skip:
            try:
                skip_val = int(query.skip.value)
                if not cls.validate_pagination(skip=skip_val):
                    errors.append("Invalid $skip value")
            except (ValueError, TypeError):
                errors.append("$skip must be an integer")

        return len(errors) == 0, errors
