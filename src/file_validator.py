"""
File Validation Layer — Ensures file modifications are safe and appropriate.

Validates file types, content integrity, and prevents inappropriate modifications.

Dependency: file_manager, re (built-in).
"""
import re
import logging
from typing import Dict, Any, Optional, Tuple

from src.file_manager import FileManager


logger = logging.getLogger(__name__)


class FileValidationError(Exception):
    """Raised when file validation fails."""
    pass


class FileValidator:
    """
    Validates file modifications before they are applied.

    Checks:
        - File type appropriateness
        - Content validity
        - Syntax correctness (basic)
        - Size limits
    """

    # File type restrictions - what content types are allowed in each file type
    FILE_TYPE_RULES = {
        '.py': {
            'allowed_content': ['python', 'code', 'import', 'def', 'class'],
            'forbidden_content': ['<html>', '<script>', '<?php', 'CREATE TABLE'],
            'max_size': 1000000,  # 1MB
        },
        '.txt': {
            'allowed_content': ['text', 'plain'],
            'forbidden_content': ['import ', 'def ', 'class ', '<html>', '<?php'],
            'max_size': 100000,  # 100KB
        },
        '.md': {
            'allowed_content': ['markdown', 'text', '#', '##', '```'],
            'forbidden_content': ['import ', 'def ', 'CREATE TABLE'],
            'max_size': 500000,  # 500KB
        },
        '.json': {
            'allowed_content': ['{', '}', '[', ']', '"'],
            'forbidden_content': ['import ', 'def ', 'class ', '<html>'],
            'max_size': 100000,  # 100KB
        },
        '.html': {
            'allowed_content': ['<html>', '<head>', '<body>', '<div>'],
            'forbidden_content': ['import ', 'def ', 'CREATE TABLE'],
            'max_size': 500000,  # 500KB
        },
        '.css': {
            'allowed_content': ['{', '}', '.', '#', '@'],
            'forbidden_content': ['import ', 'def ', 'CREATE TABLE', '<html>'],
            'max_size': 200000,  # 200KB
        },
        '.js': {
            'allowed_content': ['function', 'var ', 'const ', 'let ', 'import '],
            'forbidden_content': ['CREATE TABLE', '<?php'],
            'max_size': 500000,  # 500KB
        },
        '.csv': {
            'allowed_content': [',', '\"'],
            'forbidden_content': ['import ', 'def ', 'class ', '<html>', 'CREATE TABLE'],
            'max_size': 1000000,  # 1MB for CSV files
        },
        'requirements.txt': {
            'allowed_content': ['==', '>=', '<=', '~=', '-'],
            'forbidden_content': ['def ', 'class ', '<html>', 'CREATE TABLE'],
            'max_size': 10000,  # 10KB
        }
    }

    def __init__(self, file_manager: FileManager) -> None:
        """
        Initialize with FileManager.

        Args:
            file_manager: FileManager for workspace access.
        """
        self.file_manager = file_manager

    def validate_modification(self, file_path: str, new_content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a file modification is safe and appropriate.

        Args:
            file_path: Path to the file being modified.
            new_content: New content to be written.

        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            # Basic validation
            if not file_path or not new_content:
                return False, "File path and content cannot be empty"

            # Check file exists
            if not self.file_manager.file_exists(file_path):
                return False, f"File does not exist: {file_path}"

            # Get file extension
            file_ext = self._get_file_extension(file_path)

            # Validate file type rules
            type_valid, type_error = self._validate_file_type(file_path, file_ext, new_content)
            if not type_valid:
                return False, type_error

            # Validate content integrity
            content_valid, content_error = self._validate_content_integrity(file_ext, new_content)
            if not content_valid:
                return False, content_error

            # Validate size limits
            size_valid, size_error = self._validate_size_limits(file_ext, new_content)
            if not size_valid:
                return False, size_error

            return True, None

        except Exception as e:
            logger.error(f"Validation error for {file_path}: {e}")
            return False, f"Validation failed: {e}"

    def _strip_markdown_fences(self, content: str) -> str:
        """
        Strip markdown code fences from content.

        Removes ```language ... ``` blocks and returns clean code.

        Args:
            content: Content that may contain markdown fences.

        Returns:
            Content with markdown fences removed.
        """
        # Remove markdown code fences (```language ... ```)
        pattern = r'^\s*```[^\n]*\n(.*?)\n\s*```\s*$'
        match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
        if match:
            return match.group(1).strip()

        # Also handle case where there's just triple backticks on lines
        lines = content.split('\n')
        cleaned_lines = []
        in_fence = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('```'):
                in_fence = not in_fence
                continue
            if not in_fence:
                cleaned_lines.append(line)

        result = '\n'.join(cleaned_lines).strip()
        # Return original if cleaning resulted in empty content
        return result if result else content.strip()

    def _get_file_extension(self, file_path: str) -> str:
        """
        Get file extension, handling special cases like requirements.txt.

        Args:
            file_path: File path to analyze.

        Returns:
            File extension or filename if special case.
        """
        filename = file_path.lower()

        # Special cases
        if filename == 'requirements.txt':
            return 'requirements.txt'

        # Normal extension
        if '.' in filename:
            return '.' + filename.split('.')[-1]

        return '.txt'  # Default

    def _validate_file_type(self, file_path: str, file_ext: str, content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that content is appropriate for the file type.

        Args:
            file_path: File path.
            file_ext: File extension.
            content: Content to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if file_ext not in self.FILE_TYPE_RULES:
            # Unknown file type - allow but log warning
            logger.warning(f"Unknown file type {file_ext} for {file_path}")
            return True, None

        rules = self.FILE_TYPE_RULES[file_ext]
        content_lower = content.lower()

        # Check forbidden content
        for forbidden in rules['forbidden_content']:
            if forbidden.lower() in content_lower:
                return False, f"File {file_path} ({file_ext}) cannot contain '{forbidden.strip()}' content"

        # Check that some allowed content is present (basic validation) - skip for CSV and data files
        if file_ext not in ['.csv', '.txt']:
            has_allowed = False
            for allowed in rules['allowed_content']:
                if allowed.lower() in content_lower:
                    has_allowed = True
                    break

            if not has_allowed and len(content.strip()) > 10:  # Only check for substantial content
                logger.warning(f"File {file_path} may not contain expected content for type {file_ext}")

        return True, None

    def _validate_content_integrity(self, file_ext: str, content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate content integrity and basic syntax.

        Args:
            file_ext: File extension.
            content: Content to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        try:
            if file_ext == '.py':
                return self._validate_python_syntax(content)
            elif file_ext == '.json':
                return self._validate_json_syntax(content)
            elif file_ext == '.html':
                return self._validate_html_structure(content)
            elif file_ext == 'requirements.txt':
                return self._validate_requirements_format(content)

            # For other file types, basic checks
            return self._validate_basic_integrity(content)

        except Exception as e:
            return False, f"Content validation failed: {e}"

    def _validate_python_syntax(self, content: str) -> Tuple[bool, Optional[str]]:
        """Basic Python syntax validation."""
        try:
            # Strip markdown code fences if present
            clean_code = self._strip_markdown_fences(content)
            compile(clean_code, '<string>', 'exec')
            return True, None
        except SyntaxError as e:
            return False, f"Python syntax error: {e}"
        except Exception as e:
            return False, f"Python validation error: {e}"

    def _validate_json_syntax(self, content: str) -> Tuple[bool, Optional[str]]:
        """JSON syntax validation."""
        try:
            import json
            json.loads(content)
            return True, None
        except json.JSONDecodeError as e:
            return False, f"JSON syntax error: {e}"
        except Exception as e:
            return False, f"JSON validation error: {e}"

    def _validate_html_structure(self, content: str) -> Tuple[bool, Optional[str]]:
        """Basic HTML structure validation."""
        content_lower = content.lower()
        if '<html>' in content_lower and '</html>' in content_lower:
            return True, None
        elif len(content.strip()) < 100:  # Small files might be fragments
            return True, None
        else:
            return False, "HTML files should contain <html> tags or be small fragments"

    def _validate_requirements_format(self, content: str) -> Tuple[bool, Optional[str]]:
        """Requirements.txt format validation."""
        # Strip any markdown code fences from requirements
        content = self._strip_markdown_fences(content)
        
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            # Skip empty lines, comments, and markdown artifacts
            if not line or line.startswith('#') or line.startswith('```'):
                continue

            # Should contain package name and optional version specifiers
            # Allow: package_name, package-name==1.0, package>=2.0, etc.
            if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*[\s=<>~]*', line):
                return False, f"Invalid package name in requirements: {line}"

        return True, None

    def _validate_basic_integrity(self, content: str) -> Tuple[bool, Optional[str]]:
        """Basic content integrity checks."""
        # Check for null bytes (binary content in text file)
        if '\x00' in content:
            return False, "Content contains null bytes (binary data)"

        # Check for extremely long lines (possible data corruption)
        lines = content.split('\n')
        max_line_length = max(len(line) for line in lines) if lines else 0
        if max_line_length > 10000:
            return False, f"Line too long ({max_line_length} chars) - possible corruption"

        return True, None

    def _validate_size_limits(self, file_ext: str, content: str) -> Tuple[bool, Optional[str]]:
        """
        Validate file size limits.

        Args:
            file_ext: File extension.
            content: Content to check size of.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if file_ext in self.FILE_TYPE_RULES:
            max_size = self.FILE_TYPE_RULES[file_ext]['max_size']
            content_size = len(content.encode('utf-8'))

            if content_size > max_size:
                return False, f"File too large ({content_size} bytes > {max_size} byte limit)"

        return True, None