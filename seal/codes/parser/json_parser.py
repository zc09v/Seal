"""JSON parser implementation for Seal library."""

import json
import re
from typing import Any, Dict, Optional

from .errors import JsonParseError


class JsonParser:
    """Robust JSON parser with support for Markdown code block extraction and error tolerance."""
    
    def __init__(self, *, need_try_auto_repair: bool = True):
        """
        Initialize JSON parser.
        
        Args:
            need_try_auto_repair: Whether to attempt automatic repair of common JSON format errors
        """
        self.need_try_auto_repair = need_try_auto_repair
        
        # Regular expressions for Markdown code block extraction
        self._markdown_patterns = [
            # Triple backtick with json language specifier
            re.compile(r'```json\s*([\s\S]*?)```', re.IGNORECASE),
            # Triple backtick without language specifier
            re.compile(r'```\s*([\s\S]*?)```', re.IGNORECASE),
            # Single backtick inline code
            re.compile(r'`([^`]+)`', re.IGNORECASE)
        ]
    
    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse JSON data from text.
        
        Args:
            text: Text containing JSON (can be pure JSON or Markdown code block)
            
        Returns:
            Parsed dictionary data
            
        Raises:
            JsonParseError: When JSON cannot be parsed
        """
        if not text or not text.strip():
            raise JsonParseError("Input text is empty", text)
        
        # Step 1: Check if text is already valid JSON
        trimmed_text = text.strip()
        if self._looks_like_json(trimmed_text):
            json_str = trimmed_text
        else:
            # Step 2: Extract JSON from Markdown if present
            extracted_json = self.extract_json_from_markdown(text)
            json_str = extracted_json if extracted_json is not None else trimmed_text
        
        # Step 2: Try standard JSON parsing
        try:
            return self._parse_json(json_str)
        except JsonParseError as e:
            # If auto repair is disabled, re-raise the error
            if not self.need_try_auto_repair:
                raise
            
            # Step 3: Try to repair and re-parse
            try:
                repaired_json = self.try_repair_json(json_str)
                return self._parse_json(repaired_json)
            except JsonParseError:
                # If repair also fails, raise the original error
                raise e
    
    def extract_json_from_markdown(self, text: str) -> Optional[str]:
        """
        Extract JSON code block from Markdown text.
        
        Args:
            text: Markdown formatted text
            
        Returns:
            Extracted JSON string, or None if not found
        """
        for pattern in self._markdown_patterns:
            match = pattern.search(text)
            if match:
                extracted = match.group(1).strip()
                # Validate that this looks like JSON
                if self._looks_like_json(extracted):
                    return extracted
        
        return None
    
    def try_repair_json(self, json_str: str) -> str:
        """
        Attempt to repair common JSON format errors.
        
        Args:
            json_str: Potentially malformed JSON string
            
        Returns:
            Repaired JSON string
            
        Raises:
            JsonParseError: When JSON cannot be repaired
        """
        if not json_str:
            raise JsonParseError("JSON string is empty", json_str)
        
        # Make a copy to work with
        repaired = json_str.strip()
        
        # Repair 1: Remove trailing commas
        repaired = self._remove_trailing_commas(repaired)
        
        # Repair 2: Convert single quotes to double quotes
        repaired = self._convert_single_quotes(repaired)
        
        # Repair 3: Remove comments
        repaired = self._remove_comments(repaired)
        
        # Repair 4: Fix unescaped quotes
        repaired = self._fix_unescaped_quotes(repaired)
        
        # Repair 5: Remove trailing content after JSON
        repaired = self._remove_trailing_content(repaired)
        
        # Validate that the repaired string is different and looks like JSON
        if repaired == json_str:
            raise JsonParseError("No repairs were applied", json_str)
        
        if not self._looks_like_json(repaired):
            raise JsonParseError("Repaired string does not look like JSON", json_str)
        
        return repaired
    
    def _parse_json(self, json_str: str) -> Dict[str, Any]:
        """Internal method to parse JSON string."""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise JsonParseError(
                f"JSON decoding failed: {str(e)}",
                json_str,
                f"Error at line {e.lineno}, column {e.colno}"
            )
    
    def _looks_like_json(self, text: str) -> bool:
        """Check if text looks like JSON (starts with { or [)."""
        trimmed = text.strip()
        # More robust check: should start with { or [ and end with } or ]
        return (trimmed.startswith('{') and trimmed.endswith('}')) or \
               (trimmed.startswith('[') and trimmed.endswith(']'))
    
    def _remove_trailing_commas(self, text: str) -> str:
        """Remove trailing commas in objects and arrays."""
        # Remove trailing commas before closing braces/brackets
        pattern = r',\s*([}\]])'
        return re.sub(pattern, r'\1', text)
    
    def _convert_single_quotes(self, text: str) -> str:
        """Convert single quotes to double quotes."""
        # Simple approach: replace single quotes with double quotes, but avoid replacing
        # single quotes that are already inside double-quoted strings
        result = []
        in_double_quoted_string = False
        escape_next = False
        
        for char in text:
            if escape_next:
                result.append(char)
                escape_next = False
            elif char == '\\':
                result.append(char)
                escape_next = True
            elif char == '"':
                result.append(char)
                in_double_quoted_string = not in_double_quoted_string
            elif char == "'" and not in_double_quoted_string:
                # Only convert single quotes that are not inside double-quoted strings
                result.append('"')
            else:
                result.append(char)
        
        return ''.join(result)
    
    def _remove_comments(self, text: str) -> str:
        """Remove JavaScript-style comments."""
        # Remove single-line comments
        text = re.sub(r'//.*?$', '', text, flags=re.MULTILINE)
        # Remove multi-line comments
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        return text
    
    def _fix_unescaped_quotes(self, text: str) -> str:
        """Fix unescaped quotes within strings."""
        # This method should only escape quotes that appear within strings but are not properly escaped
        # For now, we'll implement a simple heuristic: if we see a quote that's not at a string boundary,
        # it might need escaping. But this is complex, so we'll skip this repair for now.
        # TODO: Implement proper unescaped quote detection
        return text
    
    def _remove_trailing_content(self, text: str) -> str:
        """Remove trailing content after valid JSON."""
        # Find the position where valid JSON ends
        # This is a simplified approach - proper implementation would require parsing
        stack = []
        last_valid_pos = 0
        
        for i, char in enumerate(text):
            if char in '{[':
                stack.append(char)
            elif char in '}]':
                if stack:
                    stack.pop()
                else:
                    # Unmatched closing bracket
                    break
            
            if not stack:
                last_valid_pos = i + 1
        
        return text[:last_valid_pos] if last_valid_pos > 0 else text