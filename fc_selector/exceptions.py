"""
OData-specific exceptions for django-odata.

This module defines custom exceptions that provide OData v4.0 compliant
error responses for various error conditions.
"""

from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException


class ODataFilterError(APIException):
    """
    Exception raised when OData filter parsing or execution fails.

    This exception provides OData v4.0 compliant error formatting
    with detailed information about filter errors.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid filter expression"
    default_code = "BadRequest"

    def __init__(
        self,
        message: str,
        code: str = "BadRequest",
        target: str = "$filter",
        details: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        """
        Initialize OData filter error.

        Args:
            message: Human-readable error message
            code: Error code (e.g., "FieldNotFound", "InvalidFilterSyntax")
            target: The query parameter that caused the error (usually "$filter")
            details: Additional error context
            original_exception: The underlying exception that caused this error
        """
        self.message = message
        self.error_code = code
        self.target = target
        self.details = details or {}
        self.original_exception = original_exception

        # Create OData-compliant error structure with limited message size
        safe_message = message[:512]
        error_details = [
            {
                "code": self.error_code,
                "message": safe_message,
                "target": self.target,
            }
        ]

        # Add additional details if provided, truncate potentially sensitive fields
        if self.details:
            if "expression" in self.details:
                self.details["expression"] = str(self.details["expression"])[:256]
            error_details[0].update(self.details)

        super().__init__(
            detail={
                "error": {
                    "code": self.default_code,
                    "message": safe_message,
                    "details": error_details,
                }
            },
            code=self.default_code,
        )


class ODataFieldNotFoundError(ODataFilterError):
    """
    Exception raised when a referenced field does not exist on the model.
    """

    def __init__(
        self,
        field_name: str,
        model_name: str,
        original_exception: Exception | None = None,
    ):
        message = f"Field '{field_name}' does not exist on entity '{model_name}'"
        super().__init__(
            message=message,
            code="FieldNotFound",
            target="$filter",
            details={"field": field_name, "entity": model_name},
            original_exception=original_exception,
        )


class ODataInvalidFilterSyntaxError(ODataFilterError):
    """
    Exception raised when filter expression has invalid syntax.
    """

    def __init__(
        self,
        filter_expression: str,
        details: str = "",
        original_exception: Exception | None = None,
    ):
        message = f"Invalid filter expression: {filter_expression}"
        if details:
            message += f" - {details}"

        super().__init__(
            message=message,
            code="InvalidFilterSyntax",
            target="$filter",
            details={"expression": filter_expression, "syntax_error": details},
            original_exception=original_exception,
        )


class ODataInvalidOperatorError(ODataFilterError):
    """
    Exception raised when an invalid operator is used in filter expression.
    """

    def __init__(
        self,
        operator: str,
        filter_expression: str,
        original_exception: Exception | None = None,
    ):
        valid_operators = [
            "eq",
            "ne",
            "gt",
            "ge",
            "lt",
            "le",
            "and",
            "or",
            "not",
            "contains",
            "startswith",
            "endswith",
        ]
        message = f"Unknown operator '{operator}'. Valid operators: {', '.join(valid_operators)}"

        super().__init__(
            message=message,
            code="InvalidOperator",
            target="$filter",
            details={
                "operator": operator,
                "expression": filter_expression,
                "valid_operators": valid_operators,
            },
            original_exception=original_exception,
        )


class ODataInvalidValueError(ODataFilterError):
    """
    Exception raised when a filter value doesn't match the expected type.
    """

    def __init__(
        self,
        value: str,
        expected_type: str,
        field: str,
        original_exception: Exception | None = None,
    ):
        message = f"Invalid value '{value}' for field '{field}'. Expected type: {expected_type}"

        super().__init__(
            message=message,
            code="InvalidValue",
            target="$filter",
            details={"value": value, "expected_type": expected_type, "field": field},
            original_exception=original_exception,
        )


class ODataExpandError(ODataFilterError):
    """
    Exception raised when $expand parameter contains invalid field references.
    """

    def __init__(
        self,
        field_name: str,
        model_name: str,
        valid_fields: list | None = None,
        original_exception: Exception | None = None,
    ):
        if valid_fields:
            choices_str = ", ".join(f"'{f}'" for f in valid_fields)
            message = f"Invalid $expand field '{field_name}'. Valid expandable fields are: {choices_str}"
        else:
            message = f"Invalid $expand field '{field_name}'"

        super().__init__(
            message=message,
            code="InvalidExpandField",
            target="$expand",
            details={
                "field": field_name,
                "entity": model_name,
                "valid_choices": valid_fields or [],
            },
            original_exception=original_exception,
        )


class ODataInvalidPaginationError(ODataFilterError):
    """
    Exception raised when $top or $skip parameters have invalid values.
    """

    def __init__(
        self,
        parameter: str,
        value: str,
        original_exception: Exception | None = None,
    ):
        # Check if the value contains another query parameter (common mistake)
        if "$" in str(value) and parameter in ["$top", "$skip"]:
            suggestion = "\n\nDid you forget to use '&' between query parameters?\n"
            suggestion += "Example: ?$top=10&$skip=5 (not ?$top=10$skip=5)"
            message = f"Invalid value '{value}' for {parameter}. Expected a positive integer.{suggestion}"
        else:
            message = f"Invalid value '{value}' for {parameter}. Expected a positive integer."

        super().__init__(
            message=message,
            code="InvalidPaginationValue",
            target=parameter,
            details={"parameter": parameter, "invalid_value": value},
            original_exception=original_exception,
        )
