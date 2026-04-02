"""
Context extraction for code at cursor position.

Extracts relevant code context for completion and analysis prompts.
Pure functions — no dependency on LLM or external services.

Dependency: tools.ast_parser (internal tool only).
"""
from typing import Optional
from dataclasses import dataclass

from src.tools.ast_parser import (
    get_function_by_line,
    get_class_by_line,
    extract_imports,
    ParseError,
)


@dataclass
class CodeContext:
    """Extracted context around a cursor position."""
    imports: str
    parent_scope: str
    surrounding_code: str
    full_context: str


def get_current_context(
    code: str,
    cursor_position: int,
    context_lines: int = 5,
) -> Optional[CodeContext]:
    """
    Extract context around a cursor position (line number).

    Args:
        code: Full source code.
        cursor_position: Line number (1-indexed).
        context_lines: Number of lines before/after to include.

    Returns:
        CodeContext or None if position is invalid.
    """
    lines = code.split("\n")
    line_num = cursor_position

    if line_num < 1 or line_num > len(lines):
        return None

    try:
        imports_list = extract_imports(code)
        imports_section = "\n".join(
            f"import {imp.module}" if not imp.is_relative
            else f"from {imp.module} import {', '.join(imp.names)}"
            for imp in imports_list
        )

        parent_scope = ""
        func = get_function_by_line(code, line_num)
        cls = get_class_by_line(code, line_num)

        if func:
            parent_scope = f"def {func.name}({', '.join(func.args)}):"
        elif cls:
            parent_scope = f"class {cls.name}:"

        start_idx = max(0, line_num - context_lines - 1)
        end_idx = min(len(lines), line_num + context_lines)
        surrounding = "\n".join(lines[start_idx:end_idx])

        full_context = f"{imports_section}\n\n{surrounding}\n"

        return CodeContext(
            imports=imports_section,
            parent_scope=parent_scope,
            surrounding_code=surrounding,
            full_context=full_context,
        )

    except ParseError:
        return None


def get_function_context(code: str, line_number: int) -> Optional[str]:
    """
    Get the complete function definition containing a line.

    Args:
        code: Full source code.
        line_number: Target line number (1-indexed).

    Returns:
        Function source code or None.
    """
    lines = code.split("\n")
    try:
        func = get_function_by_line(code, line_number)
        if not func:
            return None
        func_lines = lines[func.line_start - 1:func.line_end]
        return "\n".join(func_lines)
    except ParseError:
        return None


def get_imports_context(code: str) -> str:
    """
    Get all import statements from code as a string.

    Args:
        code: Full source code.

    Returns:
        All import statements joined by newlines.
    """
    try:
        imports_list = extract_imports(code)
        if not imports_list:
            return ""

        import_lines = []
        for imp in imports_list:
            if imp.is_relative:
                import_lines.append(
                    f"from {imp.module} import {', '.join(imp.names)}"
                )
            elif imp.module:
                if len(imp.names) == 1 and imp.names[0] == imp.module:
                    import_lines.append(f"import {imp.module}")
                else:
                    import_lines.append(
                        f"from {imp.module} import {', '.join(imp.names)}"
                    )

        return "\n".join(import_lines)
    except ParseError:
        return ""


def get_code_before_cursor(code: str, line_number: int) -> str:
    """Get all code before and including the target line."""
    lines = code.split("\n")
    if line_number < 1 or line_number > len(lines):
        return ""
    return "\n".join(lines[:line_number])


def get_code_after_cursor(code: str, line_number: int) -> str:
    """Get all code from the target line onward."""
    lines = code.split("\n")
    if line_number < 1 or line_number > len(lines):
        return ""
    return "\n".join(lines[line_number - 1:])


def get_line_content(code: str, line_number: int) -> Optional[str]:
    """Get the content of a specific line (1-indexed)."""
    lines = code.split("\n")
    if line_number < 1 or line_number > len(lines):
        return None
    return lines[line_number - 1]


def get_context_summary(code: str, line_number: int) -> str:
    """
    Get a human-readable context summary for debugging/analysis.

    Args:
        code: Full source code.
        line_number: Target line number (1-indexed).

    Returns:
        Formatted context summary string.
    """
    context = get_current_context(code, line_number, context_lines=3)
    if not context:
        return "No context found"

    return (
        f"Context Summary:\n"
        f"================\n"
        f"Line: {line_number}\n"
        f"Parent Scope: {context.parent_scope or '(global)'}\n"
        f"Current Line: {get_line_content(code, line_number)}\n"
        f"\nSurrounding Code:\n"
        f"{context.surrounding_code}\n"
        f"================"
    )
