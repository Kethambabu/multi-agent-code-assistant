"""
Error-Driven File Selector — Advanced file targeting based on error traces.

Parses stack traces, identifies root causes, and selects exact files/lines
for modification. Prioritizes precision over breadth.

Dependency: file_manager, re (built-in).
"""
import re
import logging
from typing import List, Dict, Optional, Tuple

from src.file_manager import FileManager


logger = logging.getLogger(__name__)


class ErrorDrivenFileSelector:
    """
    Advanced file selector that parses error traces and stack traces
    to identify exact files and lines that need modification.

    Strategy:
        1. Parse stack trace to extract file paths and line numbers
        2. Validate files exist in workspace
        3. Return prioritized list of files to modify
    """

    # Regex patterns for parsing different error formats
    STACK_TRACE_PATTERNS = [
        # Python traceback: File "/path/to/file.py", line 123, in function_name
        r'File\s+"([^"]+)",\s*line\s+(\d+)',

        # Python traceback: File '/path/to/file.py', line 123, in function_name
        r"File\s+'([^']+)',\s*line\s+(\d+)",

        # Generic file:line format
        r'(\S+\.\w+):(\d+)',

        # Windows path format
        r'([A-Za-z]:[^\s]+\.\w+):(\d+)',

        # Unix path format
        r'(/[^\s]+\.\w+):(\d+)',
    ]

    # Error keywords that indicate file modification is needed
    ERROR_KEYWORDS = [
        "NameError", "AttributeError", "ImportError", "ModuleNotFoundError",
        "SyntaxError", "IndentationError", "TypeError", "ValueError",
        "KeyError", "IndexError", "FileNotFoundError", "PermissionError",
        "OSError", "IOError", "ConnectionError", "TimeoutError",
        "AssertionError", "ZeroDivisionError", "OverflowError",
        "RecursionError", "NotImplementedError", "SystemError",
        "UnicodeError", "UnicodeDecodeError", "UnicodeEncodeError",
    ]

    def __init__(self, file_manager: FileManager) -> None:
        """
        Initialize with FileManager.

        Args:
            file_manager: FileManager for workspace access.
        """
        self.file_manager = file_manager

    def select_files_from_error(self, error_text: str) -> List[str]:
        """
        Parse error text and return files that need modification.

        Args:
            error_text: Error message, traceback, or stack trace.

        Returns:
            List of relative file paths that should be modified.
        """
        if not error_text or not error_text.strip():
            return []

        # Check if this looks like an error that needs file modification
        if not self._is_modification_error(error_text):
            logger.info("Error doesn't appear to require file modification")
            return []

        # Extract file paths from stack trace
        file_candidates = self._extract_files_from_trace(error_text)
        logger.info(f"Found {len(file_candidates)} file candidates from error trace")

        # Validate and filter files that exist in workspace
        valid_files = []
        for file_path in file_candidates:
            if self._is_valid_workspace_file(file_path):
                valid_files.append(file_path)
                logger.info(f"Validated workspace file: {file_path}")

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for file_path in valid_files:
            if file_path not in seen:
                seen.add(file_path)
                unique_files.append(file_path)

        logger.info(f"Selected {len(unique_files)} files for modification: {unique_files}")
        return unique_files

    def _is_modification_error(self, error_text: str) -> bool:
        """
        Determine if the error requires file modification.

        Args:
            error_text: Error text to analyze.

        Returns:
            True if this error likely requires code changes.
        """
        error_text = error_text.lower()

        # Check for error keywords
        for keyword in self.ERROR_KEYWORDS:
            if keyword.lower() in error_text:
                return True

        # Check for common error patterns
        error_patterns = [
            "no module named",
            "cannot import",
            "undefined name",
            "syntax error",
            "indentation error",
            "unexpected token",
            "invalid syntax",
            "name error",
            "attribute error",
            "type error",
            "value error",
            "key error",
            "index error",
            "file not found",
            "permission denied",
            "assertion failed",
            "division by zero",
        ]

        for pattern in error_patterns:
            if pattern in error_text:
                return True

        return False

    def _extract_files_from_trace(self, error_text: str) -> List[str]:
        """
        Extract file paths from error trace using regex patterns.

        Args:
            error_text: Error text containing stack trace.

        Returns:
            List of file paths found in the trace.
        """
        files_found = []

        for pattern in self.STACK_TRACE_PATTERNS:
            matches = re.findall(pattern, error_text)
            for match in matches:
                if isinstance(match, tuple):
                    file_path = match[0]
                else:
                    file_path = match

                # Clean up the file path
                file_path = self._clean_file_path(file_path)
                if file_path:
                    files_found.append(file_path)

        return files_found

    def _clean_file_path(self, file_path: str) -> Optional[str]:
        """
        Clean and normalize file path from error trace.

        Args:
            file_path: Raw file path from error trace.

        Returns:
            Cleaned relative path or None if invalid.
        """
        if not file_path:
            return None

        # Remove quotes if present
        file_path = file_path.strip('"\'')

        # Extract just the filename and extension if it's a full path
        # This handles cases where the error shows full system paths
        if '/' in file_path or '\\' in file_path:
            # Take the last component (filename)
            file_path = file_path.split('/')[-1].split('\\')[-1]

        # Basic validation - should have an extension
        if '.' not in file_path:
            return None

        # Should be a code file
        valid_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp',
                           '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala'}

        ext = '.' + file_path.split('.')[-1].lower()
        if ext not in valid_extensions:
            return None

        return file_path

    def _is_valid_workspace_file(self, file_path: str) -> bool:
        """
        Check if file exists in workspace and is accessible.

        Args:
            file_path: Relative file path to check.

        Returns:
            True if file exists and is readable.
        """
        try:
            # Check if file exists
            if not self.file_manager.file_exists(file_path):
                return False

            # Try to read it (ensure it's accessible)
            content = self.file_manager.read_file(file_path)
            return len(content) > 0  # Must have content

        except Exception as e:
            logger.warning(f"Could not access file {file_path}: {e}")
            return False

    def get_error_context(self, error_text: str, file_path: str) -> Optional[Dict]:
        """
        Extract line number and context from error for a specific file.

        Args:
            error_text: Full error text.
            file_path: File to find context for.

        Returns:
            Dict with 'line_number' and 'context' or None if not found.
        """
        # Find line number for this specific file
        for pattern in self.STACK_TRACE_PATTERNS:
            matches = re.findall(pattern, error_text)
            for match in matches:
                if isinstance(match, tuple):
                    trace_file, line_num = match
                else:
                    continue

                trace_file = self._clean_file_path(trace_file)
                if trace_file == file_path:
                    try:
                        line_number = int(line_num)
                        return {
                            'line_number': line_number,
                            'context': f"Error at line {line_number} in {file_path}"
                        }
                    except ValueError:
                        continue

        return None