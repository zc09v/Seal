"""Unit tests for error classes in parser module."""

from seal.codes.parser import JsonParseError


class TestJsonParseError:
    """Test cases for JsonParseError class."""

    def test_init_with_message_only(self):
        """Test initialization with only message."""
        error = JsonParseError("Test error", "original text")
        
        assert error.message == "Test error"
        assert error.original_text == "original text"
        assert error.error_details is None

    def test_init_with_error_details(self):
        """Test initialization with error details."""
        error = JsonParseError("Test error", "original text", "line 1, column 5")
        
        assert error.message == "Test error"
        assert error.original_text == "original text"
        assert error.error_details == "line 1, column 5"

    def test_str_representation_no_details(self):
        """Test string representation without error details."""
        error = JsonParseError("JSON parsing failed", "{\"name\": \"John\"}")
        
        result = str(error)
        
        assert "JSON parsing error: JSON parsing failed" in result
        assert "Original text: {\"name\": \"John\"}" in result
        assert "Details:" not in result

    def test_str_representation_with_details(self):
        """Test string representation with error details."""
        error = JsonParseError("JSON parsing failed", "{\"name\": \"John\"}", "line 1, column 10")
        
        result = str(error)
        
        assert "JSON parsing error: JSON parsing failed" in result
        assert "Details: line 1, column 10" in result
        assert "Original text: {\"name\": \"John\"}" in result

    def test_str_representation_long_text_truncation(self):
        """Test string representation with long text truncation."""
        long_text = "a" * 300  # 300 characters
        error = JsonParseError("Test error", long_text)
        
        result = str(error)
        
        # Should truncate to 200 characters and add "..."
        assert "Original text: " + "a" * 200 + "..." in result

    def test_str_representation_short_text_no_truncation(self):
        """Test string representation with short text (no truncation)."""
        short_text = "{\"name\": \"John\"}"
        error = JsonParseError("Test error", short_text)
        
        result = str(error)
        
        # Should not truncate short text
        assert "Original text: {\"name\": \"John\"}" in result
        assert "..." not in result

    def test_inheritance_from_exception(self):
        """Test that JsonParseError inherits from Exception."""
        error = JsonParseError("Test error", "text")
        
        assert isinstance(error, Exception)

    def test_exception_message(self):
        """Test that the exception message is set correctly."""
        error = JsonParseError("Custom error message", "text")
        
        # The base Exception message should be the same as our custom message
        assert str(error) == "JSON parsing error: Custom error message\nOriginal text: text"