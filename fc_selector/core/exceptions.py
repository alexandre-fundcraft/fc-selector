"""
Core exceptions for FC Selector.

These exceptions are framework-agnostic and should not depend on external libraries
like Django or DRF. They represent domain-level errors.
"""


class SelectorError(Exception):
    """Base class for all selector exceptions."""

    pass


class QueryError(SelectorError):
    """Base class for query processing errors."""

    pass


class InvalidValueError(QueryError):
    """Raised when a value is invalid for a given type or operation."""

    def __init__(self, value, expected_type=None, context=None):
        self.value = value
        self.expected_type = expected_type
        self.context = context
        msg = f"Invalid value: {value}"
        if expected_type:
            msg += f". Expected {expected_type}"
        if context:
            msg += f" in {context}"
        super().__init__(msg)


class TypeMismatchError(QueryError):
    """Raised when an operation receives an operand of incorrect type."""

    def __init__(self, expected, actual, context=None):
        self.expected = expected
        self.actual = actual
        self.context = context
        msg = f"Type mismatch: Expected {expected}, got {actual}"
        if context:
            msg += f" in {context}"
        super().__init__(msg)


class UnsupportedFunctionError(QueryError):
    """Raised when a requested function is not supported by the backend."""

    def __init__(self, func_name):
        self.func_name = func_name
        super().__init__(f"Function '{func_name}' is not supported")


class FieldNotFoundError(QueryError):
    """Raised when a requested field does not exist."""

    def __init__(self, field_name, model_name=None):
        self.field_name = field_name
        self.model_name = model_name
        msg = f"Field '{field_name}' not found"
        if model_name:
            msg += f" on {model_name}"
        super().__init__(msg)


class InvalidFieldError(QueryError):
    """Raised when an invalid or disallowed field is accessed."""

    def __init__(self, field_name: str, model_name: str, reason: str | None = None):
        self.field_name = field_name
        self.model_name = model_name
        self.reason = reason
        msg = f"Field '{field_name}' is not valid for model '{model_name}'"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)
