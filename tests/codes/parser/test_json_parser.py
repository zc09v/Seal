"""Unit tests for JsonParser class."""

import pytest
from seal.codes.parser import JsonParser, JsonParseError


class TestJsonParser:
    """Test cases for JsonParser class."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON string."""
        parser = JsonParser()
        json_str = '{"name": "John", "age": 30}'
        
        result = parser.parse(json_str)
        
        assert result == {"name": "John", "age": 30}

    def test_parse_json_with_trailing_comma(self):
        """Test parsing JSON with trailing comma (auto repair enabled)."""
        parser = JsonParser(need_try_auto_repair=True)
        json_str = '{"name": "John", "age": 30,}'
        
        result = parser.parse(json_str)
        
        assert result == {"name": "John", "age": 30}

    def test_parse_json_with_single_quotes(self):
        """Test parsing JSON with single quotes (auto repair enabled)."""
        parser = JsonParser(need_try_auto_repair=True)
        json_str = "{'name': 'John', 'age': 30}"
        
        result = parser.parse(json_str)
        
        assert result == {"name": "John", "age": 30}

    def test_parse_json_with_comments(self):
        """Test parsing JSON with comments (auto repair enabled)."""
        parser = JsonParser(need_try_auto_repair=True)
        json_str = '{"name": "John"} // comment'
        
        result = parser.parse(json_str)
        
        assert result == {"name": "John"}

    def test_parse_json_auto_repair_disabled(self):
        """Test parsing JSON with auto repair disabled."""
        parser = JsonParser(need_try_auto_repair=False)
        json_str = '{"name": "John", "age": 30,}'
        
        with pytest.raises(JsonParseError) as exc_info:
            parser.parse(json_str)
        
        assert "Illegal trailing comma" in str(exc_info.value)

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        parser = JsonParser()
        
        with pytest.raises(JsonParseError) as exc_info:
            parser.parse("")
        
        assert "Input text is empty" in str(exc_info.value)

    def test_parse_whitespace_only(self):
        """Test parsing whitespace-only string."""
        parser = JsonParser()
        
        with pytest.raises(JsonParseError) as exc_info:
            parser.parse("   ")
        
        assert "Input text is empty" in str(exc_info.value)

    def test_extract_json_from_markdown_json_block(self):
        """Test extracting JSON from Markdown with json code block."""
        parser = JsonParser()
        markdown_text = """
        Here is the data:
        
        ```json
        {"name": "John", "age": 30}
        ```
        
        Please use this format.
        """
        
        extracted = parser.extract_json_from_markdown(markdown_text)
        
        assert extracted == '{"name": "John", "age": 30}'

    def test_extract_json_from_markdown_generic_block(self):
        """Test extracting JSON from Markdown with generic code block."""
        parser = JsonParser()
        markdown_text = """
        Data:
        ```
        {"name": "Jane", "age": 25}
        ```
        """
        
        extracted = parser.extract_json_from_markdown(markdown_text)
        
        assert extracted == '{"name": "Jane", "age": 25}'

    def test_extract_json_from_markdown_inline_code(self):
        """Test extracting JSON from Markdown inline code."""
        parser = JsonParser()
        markdown_text = "The data is `{\"name\": \"John\"}`"
        
        extracted = parser.extract_json_from_markdown(markdown_text)
        
        assert extracted == '{"name": "John"}'

    def test_extract_json_from_markdown_no_json(self):
        """Test extracting JSON from Markdown without JSON."""
        parser = JsonParser()
        markdown_text = """
        Here is some text:
        
        ```python
        print("Hello")
        ```
        """
        
        extracted = parser.extract_json_from_markdown(markdown_text)
        
        assert extracted is None

    def test_try_repair_json_success(self):
        """Test successful JSON repair."""
        parser = JsonParser()
        json_str = '{"name": "John", "age": 30,}'
        
        repaired = parser.try_repair_json(json_str)
        
        assert repaired == '{"name": "John", "age": 30}'

    def test_try_repair_json_no_repair_needed(self):
        """Test JSON repair when no repair is needed."""
        parser = JsonParser()
        json_str = '{"name": "John", "age": 30}'
        
        with pytest.raises(JsonParseError) as exc_info:
            parser.try_repair_json(json_str)
        
        assert "No repairs were applied" in str(exc_info.value)

    def test_try_repair_json_empty_string(self):
        """Test JSON repair with empty string."""
        parser = JsonParser()
        
        with pytest.raises(JsonParseError) as exc_info:
            parser.try_repair_json("")
        
        assert "JSON string is empty" in str(exc_info.value)

    def test_looks_like_json_valid_object(self):
        """Test _looks_like_json with valid JSON object."""
        parser = JsonParser()
        
        assert parser._looks_like_json('{"name": "John"}') is True

    def test_looks_like_json_valid_array(self):
        """Test _looks_like_json with valid JSON array."""
        parser = JsonParser()
        
        assert parser._looks_like_json('[1, 2, 3]') is True

    def test_looks_like_json_invalid(self):
        """Test _looks_like_json with invalid JSON."""
        parser = JsonParser()
        
        assert parser._looks_like_json('Just some text') is False
        assert parser._looks_like_json('{"name": "John"') is False  # Missing closing brace
        assert parser._looks_like_json('"name": "John"}') is False  # Missing opening brace

    def test_remove_trailing_commas(self):
        """Test _remove_trailing_commas method."""
        parser = JsonParser()
        
        # Test object trailing comma
        result = parser._remove_trailing_commas('{"a": 1,}')
        assert result == '{"a": 1}'
        
        # Test array trailing comma
        result = parser._remove_trailing_commas('[1, 2, 3,]')
        assert result == '[1, 2, 3]'
        
        # Test multiple trailing commas
        result = parser._remove_trailing_commas('{"a": 1, "b": 2,}')
        assert result == '{"a": 1, "b": 2}'

    def test_convert_single_quotes(self):
        """Test _convert_single_quotes method."""
        parser = JsonParser()
        
        result = parser._convert_single_quotes("{'name': 'John'}")
        assert result == '{"name": "John"}'
        
        # Test that quotes inside double-quoted strings are not converted
        result = parser._convert_single_quotes('{"name": "John\'s car"}')
        assert result == '{"name": "John\'s car"}'

    def test_remove_comments(self):
        """Test _remove_comments method."""
        parser = JsonParser()
        
        # Test single-line comment
        result = parser._remove_comments('{"name": "John"} // comment')
        assert result == '{"name": "John"} '
        
        # Test multi-line comment
        result = parser._remove_comments('{"name": "John"} /* comment */')
        assert result == '{"name": "John"} '

    def test_parse_complex_json(self):
        """Test parsing complex JSON structure."""
        parser = JsonParser()
        json_str = '''
        {
            "users": [
                {"name": "John", "age": 30, "active": true},
                {"name": "Jane", "age": 25, "active": false}
            ],
            "count": 2
        }
        '''
        
        result = parser.parse(json_str)
        
        expected = {
            "users": [
                {"name": "John", "age": 30, "active": True},
                {"name": "Jane", "age": 25, "active": False}
            ],
            "count": 2
        }
        assert result == expected

    def test_parse_markdown_with_complex_json(self):
        """Test parsing Markdown with complex JSON."""
        parser = JsonParser()
        markdown_text = """
        API Response:
        
        ```json
        {
            "status": "success",
            "data": {
                "users": [
                    {"id": 1, "name": "John"},
                    {"id": 2, "name": "Jane"}
                ]
            }
        }
        ```
        """
        
        result = parser.parse(markdown_text)
        
        expected = {
            "status": "success",
            "data": {
                "users": [
                    {"id": 1, "name": "John"},
                    {"id": 2, "name": "Jane"}
                ]
            }
        }
        assert result == expected