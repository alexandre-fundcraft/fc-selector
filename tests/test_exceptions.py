"""
Tests for exception classes in fc_selector.

Covers:
- fc_selector/core/exceptions.py
- fc_selector/exceptions.py
- fc_selector/protocols/odata/parsers/filter/exceptions.py
"""

from fc_selector.core.exceptions import (
    FieldNotFoundError,
    InvalidFieldError,
    InvalidValueError,
    QueryError,
    SelectorError,
    TypeMismatchError,
    UnsupportedFunctionError,
)
from fc_selector.exceptions import (
    ODataFieldNotFoundError,
    ODataFilterError,
    ODataInvalidPaginationError,
    ODataInvalidValueError,
)
from fc_selector.protocols.odata.parsers.filter.exceptions import (
    ArgumentCountException,
    ArgumentTypeException,
    ODataException,
    ODataSyntaxError,
    ParsingException,
    TokenizingException,
    UnknownFunctionException,
)


class TestCoreExceptions:
    """Tests for core exceptions module."""

    def test_selector_error_inheritance(self):
        """SelectorError should be base exception."""
        error = SelectorError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_query_error_inheritance(self):
        """QueryError should inherit from SelectorError."""
        error = QueryError("query error")
        assert isinstance(error, SelectorError)
        assert str(error) == "query error"

    def test_invalid_value_error_basic(self):
        """InvalidValueError with just value."""
        error = InvalidValueError("bad_value")
        assert error.value == "bad_value"
        assert error.expected_type is None
        assert error.context is None
        assert "Invalid value: bad_value" in str(error)

    def test_invalid_value_error_with_type(self):
        """InvalidValueError with expected type."""
        error = InvalidValueError("bad", expected_type="int")
        assert error.expected_type == "int"
        assert "Expected int" in str(error)

    def test_invalid_value_error_with_context(self):
        """InvalidValueError with context."""
        error = InvalidValueError("bad", expected_type="int", context="field_name")
        assert error.context == "field_name"
        assert "in field_name" in str(error)

    def test_type_mismatch_error_basic(self):
        """TypeMismatchError with expected and actual."""
        error = TypeMismatchError("int", "str")
        assert error.expected == "int"
        assert error.actual == "str"
        assert "Expected int, got str" in str(error)

    def test_type_mismatch_error_with_context(self):
        """TypeMismatchError with context."""
        error = TypeMismatchError("int", "str", context="comparison")
        assert error.context == "comparison"
        assert "in comparison" in str(error)

    def test_unsupported_function_error(self):
        """UnsupportedFunctionError stores function name."""
        error = UnsupportedFunctionError("custom_func")
        assert error.func_name == "custom_func"
        assert "custom_func" in str(error)
        assert "not supported" in str(error)

    def test_field_not_found_error_basic(self):
        """FieldNotFoundError with just field name."""
        error = FieldNotFoundError("missing_field")
        assert error.field_name == "missing_field"
        assert error.model_name is None
        assert "missing_field" in str(error)
        assert "not found" in str(error)

    def test_field_not_found_error_with_model(self):
        """FieldNotFoundError with model name."""
        error = FieldNotFoundError("missing_field", model_name="MyModel")
        assert error.model_name == "MyModel"
        assert "on MyModel" in str(error)

    def test_invalid_field_error_basic(self):
        """InvalidFieldError with field and model."""
        error = InvalidFieldError("bad_field", "TestModel")
        assert error.field_name == "bad_field"
        assert error.model_name == "TestModel"
        assert error.reason is None
        assert "bad_field" in str(error)
        assert "TestModel" in str(error)

    def test_invalid_field_error_with_reason(self):
        """InvalidFieldError with reason."""
        error = InvalidFieldError("password", "User", reason="access denied")
        assert error.reason == "access denied"
        assert "access denied" in str(error)


class TestODataAPIExceptions:
    """Tests for OData API exceptions (DRF exceptions)."""

    def test_odata_filter_error_basic(self):
        """ODataFilterError basic initialization."""
        error = ODataFilterError("Filter failed")
        assert error.message == "Filter failed"
        assert error.error_code == "BadRequest"
        assert error.target == "$filter"
        assert error.details == {}
        assert error.original_exception is None

    def test_odata_filter_error_with_details(self):
        """ODataFilterError with all parameters."""
        original = ValueError("original")
        error = ODataFilterError(
            message="Custom error",
            code="CustomCode",
            target="$custom",
            details={"key": "value"},
            original_exception=original,
        )
        assert error.error_code == "CustomCode"
        assert error.target == "$custom"
        assert error.details == {"key": "value"}
        assert error.original_exception is original

    def test_odata_filter_error_detail_structure(self):
        """ODataFilterError produces OData-compliant error structure."""
        error = ODataFilterError("Test message", code="TestCode")
        detail = error.detail
        assert "error" in detail
        assert detail["error"]["code"] == "BadRequest"
        assert detail["error"]["message"] == "Test message"
        assert "details" in detail["error"]
        assert detail["error"]["details"][0]["code"] == "TestCode"

    def test_odata_field_not_found_error(self):
        """ODataFieldNotFoundError creates proper message."""
        error = ODataFieldNotFoundError("bad_field", "MyModel")
        assert "bad_field" in error.message
        assert "MyModel" in error.message
        assert error.error_code == "FieldNotFound"
        assert error.details["field"] == "bad_field"
        assert error.details["entity"] == "MyModel"

    def test_odata_field_not_found_error_with_original(self):
        """ODataFieldNotFoundError with original exception."""
        original = KeyError("key")
        error = ODataFieldNotFoundError("field", "Model", original_exception=original)
        assert error.original_exception is original

    def test_odata_invalid_value_error(self):
        """ODataInvalidValueError with type info."""
        error = ODataInvalidValueError("abc", "integer", "age")
        assert "abc" in error.message
        assert "integer" in error.message
        assert "age" in error.message
        assert error.error_code == "InvalidValue"
        assert error.details["value"] == "abc"
        assert error.details["expected_type"] == "integer"
        assert error.details["field"] == "age"

    def test_odata_invalid_pagination_error_basic(self):
        """ODataInvalidPaginationError basic."""
        error = ODataInvalidPaginationError("$top", "abc")
        assert "$top" in error.message
        assert "abc" in error.message
        assert "positive integer" in error.message
        assert error.error_code == "InvalidPaginationValue"
        assert error.target == "$top"

    def test_odata_invalid_pagination_error_with_suggestion(self):
        """ODataInvalidPaginationError detects missing & separator."""
        error = ODataInvalidPaginationError("$top", "10$skip=5")
        assert "&" in error.message
        assert "forgot" in error.message.lower() or "Did you" in error.message


class TestParserExceptions:
    """Tests for parser-level exceptions."""

    def test_odata_exception_base(self):
        """ODataException is base for parser exceptions."""
        error = ODataException("base error")
        assert isinstance(error, Exception)

    def test_odata_syntax_error_inheritance(self):
        """ODataSyntaxError inherits from ODataException."""
        error = ODataSyntaxError("syntax")
        assert isinstance(error, ODataException)

    def test_tokenizing_exception(self):
        """TokenizingException stores token."""

        class MockToken:
            def __str__(self):
                return "bad_token"

        token = MockToken()
        error = TokenizingException(token)
        assert error.token is token
        assert "bad_token" in str(error)

    def test_parsing_exception_with_token(self):
        """ParsingException with token."""

        class MockToken:
            def __str__(self):
                return "unexpected"

        token = MockToken()
        error = ParsingException(token)
        assert error.token is token
        assert error.eof is False
        assert "unexpected" in str(error)

    def test_parsing_exception_eof(self):
        """ParsingException at end of input."""
        error = ParsingException(None, eof=True)
        assert error.eof is True

    def test_unknown_function_exception(self):
        """UnknownFunctionException stores function name."""
        error = UnknownFunctionException("myfunc")
        assert error.function_name == "myfunc"
        assert "myfunc" in str(error)
        assert "Unknown" in str(error)

    def test_argument_count_exception_exact(self):
        """ArgumentCountException with exact argument count."""
        error = ArgumentCountException("func", 2, 2, 3)
        assert error.function_name == "func"
        assert error.exp_min_args == 2
        assert error.exp_max_args == 2
        assert error.n_args_given == 3
        assert "takes 2 arguments" in str(error)
        assert "3 given" in str(error)

    def test_argument_count_exception_range(self):
        """ArgumentCountException with argument range."""
        error = ArgumentCountException("func", 1, 3, 5)
        assert "between 1 and 3" in str(error)
        assert "5 given" in str(error)

    def test_argument_type_exception_basic(self):
        """ArgumentTypeException basic."""
        error = ArgumentTypeException()
        assert "Invalid argument type" in str(error)

    def test_argument_type_exception_with_function(self):
        """ArgumentTypeException with function name."""
        error = ArgumentTypeException(function_name="contains")
        assert "contains" in str(error)

    def test_argument_type_exception_with_types(self):
        """ArgumentTypeException with expected/actual types."""
        error = ArgumentTypeException(function_name="length", expected_type="string", actual_type="integer")
        assert "Expected string" in str(error)
        assert "got integer" in str(error)
