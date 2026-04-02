"""
Bug detection utilities for Python code.

Identifies syntax errors, undefined variables, and unused imports.
Pure functions — no dependency on LLM or external services.

Dependency: tools.ast_parser (internal tool only).
"""
import ast
from typing import List, Set
from dataclasses import dataclass

from src.tools.ast_parser import get_ast, extract_imports, ParseError


@dataclass
class BugReport:
    """Report for a detected code issue."""
    type: str           # 'syntax_error', 'undefined_variable', 'unused_import'
    line_number: int
    message: str
    severity: str       # 'error', 'warning', 'info'


def detect_syntax_errors(code: str) -> List[BugReport]:
    """
    Detect syntax errors in Python code.

    Args:
        code: Python source code.

    Returns:
        List of syntax-error BugReports (empty if code is valid).
    """
    try:
        get_ast(code)
        return []
    except ParseError as e:
        error_msg = str(e)
        line_number = 1
        if "line" in error_msg.lower():
            parts = error_msg.split()
            for i, part in enumerate(parts):
                if part.lower() == "line" and i + 1 < len(parts):
                    try:
                        line_number = int(parts[i + 1].rstrip(":"))
                    except ValueError:
                        pass

        return [
            BugReport(
                type="syntax_error",
                line_number=line_number,
                message=error_msg,
                severity="error",
            )
        ]


def detect_undefined_variables(code: str) -> List[BugReport]:
    """
    Detect potentially undefined variables.

    Args:
        code: Python source code.

    Returns:
        List of undefined-variable BugReports.
    """
    bugs: List[BugReport] = []

    try:
        tree = get_ast(code)
    except ParseError:
        return bugs

    # Collect defined names (builtins + code definitions)
    defined_names: Set[str] = {
        "print", "len", "range", "str", "int", "float", "list", "dict",
        "set", "tuple", "bool", "True", "False", "None", "type", "object",
        "Exception", "ValueError", "TypeError", "AttributeError", "__name__",
        "enumerate", "zip", "map", "filter", "sum", "min", "max", "sorted",
        "all", "any", "open", "input", "abs", "round", "pow", "divmod",
        "super", "isinstance", "issubclass", "hasattr", "getattr", "setattr",
        "property", "staticmethod", "classmethod", "repr", "hash", "id",
        "globals", "locals", "vars", "dir", "help", "iter", "next",
        "reversed", "slice", "chr", "ord", "hex", "oct", "bin",
        "format", "callable", "breakpoint", "compile", "exec", "eval",
        "complex", "bytes", "bytearray", "memoryview", "frozenset",
        "KeyError", "IndexError", "RuntimeError", "StopIteration",
        "FileNotFoundError", "IOError", "OSError", "NameError",
        "NotImplementedError", "ZeroDivisionError", "OverflowError",
    }

    # First pass: collect all definitions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            defined_names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            defined_names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defined_names.add(target.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                defined_names.add(name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                defined_names.add(name)
        elif isinstance(node, ast.For):
            if isinstance(node.target, ast.Name):
                defined_names.add(node.target.id)
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                defined_names.add(node.name)
        elif isinstance(node, ast.arg):
            defined_names.add(node.arg)

    # Second pass: check for undefined references
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in defined_names:
                bugs.append(
                    BugReport(
                        type="undefined_variable",
                        line_number=node.lineno,
                        message=f"Undefined variable: '{node.id}'",
                        severity="warning",
                    )
                )

    return bugs


def detect_unused_imports(code: str) -> List[BugReport]:
    """
    Detect unused imports in code.

    Args:
        code: Python source code.

    Returns:
        List of unused-import BugReports.
    """
    bugs: List[BugReport] = []

    try:
        tree = get_ast(code)
    except ParseError:
        return bugs

    imports = extract_imports(code)

    # Collect all names used in the code
    used_names: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                used_names.add(node.value.id)

    for imp in imports:
        for name in imp.names:
            if name == "*":
                continue
            if name not in used_names:
                bugs.append(
                    BugReport(
                        type="unused_import",
                        line_number=imp.line_number,
                        message=f"Unused import: '{name}'",
                        severity="warning",
                    )
                )

    return bugs


def detect_all_issues(code: str) -> List[BugReport]:
    """
    Run all bug detection checks on code.

    Syntax errors halt further analysis since the AST is unavailable.

    Args:
        code: Python source code.

    Returns:
        Combined list of all detected issues, sorted by line number.
    """
    syntax_errors = detect_syntax_errors(code)
    if syntax_errors:
        return syntax_errors

    issues: List[BugReport] = []
    issues.extend(detect_undefined_variables(code))
    issues.extend(detect_unused_imports(code))
    return sorted(issues, key=lambda x: x.line_number)
