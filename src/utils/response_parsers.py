"""
Response parsing utilities for LLM outputs.

Consolidates JSON extraction, code fence parsing, and other
common response processing patterns used across agents.

Dependency: None (leaf module).
"""
import json
import re
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# Code Fence Extraction
# ============================================================================

def extract_code_from_markdown(response: str, language: str = "python") -> Optional[str]:
    """
    Extract code from markdown code fences.
    
    Handles multiple formats:
    - ```python\ncode\n```
    - ```\ncode\n```
    - Just plain code if no fences found
    
    Args:
        response: LLM response text
        language: Expected language (python, json, etc.)
    
    Returns:
        Extracted code or None if parsing fails
    """
    if not response or not isinstance(response, str):
        return None
    
    response = response.strip()
    
    # Try language-specific code fences first
    pattern = rf"```{language}?\s*\n(.*?)\n```"
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Try generic code fences
    pattern = r"```\s*\n(.*?)\n```"
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # If no fences, return as-is (might be raw code)
    if response and not response.startswith("{") and not response.startswith("["):
        return response
    
    return None


# ============================================================================
# JSON Extraction
# ============================================================================

def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract and parse JSON from LLM response.
    
    Handles:
    - JSON in markdown code blocks (```json\n...\n```)
    - Bare JSON in response
    - Multiple JSON objects (returns first one)
    
    Args:
        response: LLM response text
    
    Returns:
        Parsed JSON dict or None if parsing fails
    """
    if not response or not isinstance(response, str):
        return None
    
    response = response.strip()
    
    # Try to extract from code blocks first
    json_code = extract_code_from_markdown(response, language="json")
    if json_code:
        try:
            return json.loads(json_code)
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object in response
    json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    match = re.search(json_pattern, response, re.DOTALL)
    
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            logger.debug(f"Failed to parse JSON from match: {match.group(0)[:100]}")
    
    # Try entire response as JSON
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.debug(f"Could not extract JSON from response: {response[:100]}")
        return None


def extract_json_array_from_response(response: str) -> Optional[list]:
    """
    Extract JSON array from response.
    
    Similar to extract_json_from_response but for arrays.
    
    Args:
        response: LLM response text
    
    Returns:
        Parsed JSON array or None if parsing fails
    """
    if not response or not isinstance(response, str):
        return None
    
    response = response.strip()
    
    # Try to extract from code blocks
    json_code = extract_code_from_markdown(response, language="json")
    if json_code:
        try:
            result = json.loads(json_code)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON array in response
    array_pattern = r"\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]"
    match = re.search(array_pattern, response, re.DOTALL)
    
    if match:
        try:
            result = json.loads(match.group(0))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            logger.debug(f"Failed to parse JSON array: {match.group(0)[:100]}")
    
    # Try entire response as JSON
    try:
        result = json.loads(response)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        logger.debug(f"Could not extract JSON array: {response[:100]}")
    
    return None


# ============================================================================
# Structured Data Parsing
# ============================================================================

def parse_file_map_from_response(response: str) -> Optional[Dict[str, str]]:
    """
    Parse file map ({"filename": "content", ...}) from LLM response.
    
    Expects JSON with expected structure:
    {
        "files": {
            "main.py": "python code...",
            "utils.py": "python code..."
        }
    }
    
    Args:
        response: LLM response text
    
    Returns:
        Dict {filename: content} or None if parsing fails
    """
    json_obj = extract_json_from_response(response)
    
    if not json_obj:
        return None
    
    # Check for "files" key
    if "files" in json_obj and isinstance(json_obj["files"], dict):
        return json_obj["files"]
    
    # Fall back to checking if top-level has filenames
    if all(isinstance(v, str) for v in json_obj.values()):
        return json_obj
    
    logger.warning(f"File map structure not recognized in response")
    return None


def parse_file_list_from_response(response: str) -> Optional[list]:
    """
    Parse file paths from response.
    
    Handles formats like:
    - ["file1.py", "file2.py"]
    - {"files": ["file1.py", "file2.py"]}
    - Plain text with \n-separated files
    
    Args:
        response: LLM response text
    
    Returns:
        List of file paths or None
    """
    # Try JSON first
    json_obj = extract_json_from_response(response)
    if json_obj:
        if isinstance(json_obj, list):
            return json_obj
        if isinstance(json_obj, dict) and "files" in json_obj:
            files = json_obj["files"]
            if isinstance(files, list):
                return files
    
    json_arr = extract_json_array_from_response(response)
    if json_arr:
        return json_arr
    
    # Fall back to text parsing
    lines = response.strip().split("\n")
    files = [line.strip().lstrip("- ").strip() 
             for line in lines if line.strip() and not line.strip().startswith("#")]
    return files if files else None


# ============================================================================
# Issue/Bug List Parsing
# ============================================================================

def parse_issue_list_from_response(response: str) -> Optional[list]:
    """
    Parse list of issues/bugs from response.
    
    Handles formats like:
    - JSON array
    - Markdown list items
    - Line-by-line text
    
    Args:
        response: LLM response text
    
    Returns:
        List of issue strings or None
    """
    # Try JSON first
    json_arr = extract_json_array_from_response(response)
    if json_arr:
        return [str(item) for item in json_arr]
    
    # Parse markdown or plain list
    lines = response.strip().split("\n")
    issues = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Remove markdown bullet points/numbering
        if line.startswith(("- ", "* ", "+ ")) or (line and line[0].isdigit() and ". " in line[:4]):
            line = re.sub(r"^[-*+]\s+|^\d+\.\s+", "", line)
        if line:
            issues.append(line)
    
    return issues if issues else None


# ============================================================================
# Validation
# ============================================================================

def validate_response_format(response: str, expected_format: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that response matches expected format.
    
    Args:
        response: LLM response text
        expected_format: One of: 'json', 'code', 'list', 'text'
    
    Returns:
        Tuple (is_valid, parsed_content)
    """
    if not response:
        return False, None
    
    if expected_format == "json":
        parsed = extract_json_from_response(response)
        return parsed is not None, parsed
    
    elif expected_format == "code":
        parsed = extract_code_from_markdown(response)
        return parsed is not None, parsed
    
    elif expected_format == "list":
        parsed = parse_file_list_from_response(response)
        return parsed is not None, parsed
    
    elif expected_format == "text":
        return bool(response.strip()), response.strip()
    
    return True, response  # Unknown format, assume valid


# ============================================================================
# Summary
# ============================================================================

"""
FUNCTIONS PROVIDED:

1. extract_code_from_markdown(response, language) -> code
   - Extract Python/JSON/other code from markdown fences
   
2. extract_json_from_response(response) -> dict
   - Parse single JSON object from response
   
3. extract_json_array_from_response(response) -> list
   - Parse JSON array from response
   
4. parse_file_map_from_response(response) -> dict
   - Parse {filename: content} mapping for project creation
   
5. parse_file_list_from_response(response) -> list
   - Parse list of file paths for file selection
   
6. parse_issue_list_from_response(response) -> list
   - Parse issues/bugs list for debugging
   
7. validate_response_format(response, format) -> (bool, content)
   - Validate response and return parsed content

USAGE EXAMPLE:
    from src.utils.response_parsers import (
        extract_code_from_markdown,
        parse_file_map_from_response,
    )
    
    # For code extraction
    code = extract_code_from_markdown(llm_response)
    file_manager.write_file("main.py", code)
    
    # For file map
    files = parse_file_map_from_response(llm_response)
    for name, content in files.items():
        file_manager.create_file(name, content)
"""
