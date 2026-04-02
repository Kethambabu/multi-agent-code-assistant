"""
AST parser for Python code structural analysis.

Extracts functions, classes, imports, and scope information from source code.
Pure functions — no external dependencies beyond the Python standard library.

Dependency: None (leaf module).
"""
import ast
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class FunctionInfo:
    """Metadata for a function definition."""
    name: str
    line_start: int
    line_end: int
    args: List[str]
    decorators: List[str]
    docstring: Optional[str] = None


@dataclass
class ClassInfo:
    """Metadata for a class definition."""
    name: str
    line_start: int
    line_end: int
    methods: List[str]
    decorators: List[str]
    docstring: Optional[str] = None


@dataclass
class ImportInfo:
    """Metadata for an import statement."""
    module: str
    names: List[str]
    line_number: int
    is_relative: bool


class ParseError(Exception):
    """Raised when Python code parsing fails."""
    pass


def get_ast(code: str) -> ast.AST:
    """
    Parse Python code into an AST.

    Args:
        code: Python source code string.

    Returns:
        Parsed AST object.

    Raises:
        ParseError: If the code has syntax errors.
    """
    try:
        return ast.parse(code)
    except SyntaxError as e:
        raise ParseError(f"Syntax error at line {e.lineno}: {e.msg}") from e
    except Exception as e:
        raise ParseError(f"Failed to parse code: {e}") from e


def extract_functions(code: str) -> List[FunctionInfo]:
    """
    Extract all function definitions from code.

    Args:
        code: Python source code.

    Returns:
        Sorted list of FunctionInfo ordered by line number.

    Raises:
        ParseError: If code is invalid Python.
    """
    tree = get_ast(code)
    functions: List[FunctionInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            decorators = [
                ast.unparse(dec) if hasattr(ast, "unparse") else "@decorator"
                for dec in node.decorator_list
            ]
            docstring = ast.get_docstring(node)
            args = [arg.arg for arg in node.args.args]
            line_end = node.end_lineno if hasattr(node, "end_lineno") else node.lineno

            functions.append(
                FunctionInfo(
                    name=node.name,
                    line_start=node.lineno,
                    line_end=line_end,
                    args=args,
                    decorators=decorators,
                    docstring=docstring,
                )
            )

    return sorted(functions, key=lambda f: f.line_start)


def extract_classes(code: str) -> List[ClassInfo]:
    """
    Extract all class definitions from code.

    Args:
        code: Python source code.

    Returns:
        Sorted list of ClassInfo ordered by line number.

    Raises:
        ParseError: If code is invalid Python.
    """
    tree = get_ast(code)
    classes: List[ClassInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            decorators = [
                ast.unparse(dec) if hasattr(ast, "unparse") else "@decorator"
                for dec in node.decorator_list
            ]
            docstring = ast.get_docstring(node)
            methods = [
                item.name
                for item in node.body
                if isinstance(item, ast.FunctionDef)
            ]
            line_end = node.end_lineno if hasattr(node, "end_lineno") else node.lineno

            classes.append(
                ClassInfo(
                    name=node.name,
                    line_start=node.lineno,
                    line_end=line_end,
                    methods=methods,
                    decorators=decorators,
                    docstring=docstring,
                )
            )

    return sorted(classes, key=lambda c: c.line_start)


def extract_imports(code: str) -> List[ImportInfo]:
    """
    Extract all import statements from code.

    Args:
        code: Python source code.

    Returns:
        Sorted list of ImportInfo ordered by line number.

    Raises:
        ParseError: If code is invalid Python.
    """
    tree = get_ast(code)
    imports: List[ImportInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    ImportInfo(
                        module=alias.name,
                        names=[alias.name],
                        line_number=node.lineno,
                        is_relative=False,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            names = [alias.name for alias in node.names]
            imports.append(
                ImportInfo(
                    module=node.module or "",
                    names=names,
                    line_number=node.lineno,
                    is_relative=node.level > 0,
                )
            )

    return sorted(imports, key=lambda i: i.line_number)


def get_function_by_line(code: str, line_number: int) -> Optional[FunctionInfo]:
    """
    Get the function containing a given line number.

    Args:
        code: Python source code.
        line_number: 1-indexed line number.

    Returns:
        FunctionInfo or None if the line is not inside a function.
    """
    functions = extract_functions(code)
    for func in functions:
        if func.line_start <= line_number <= func.line_end:
            return func
    return None


def get_class_by_line(code: str, line_number: int) -> Optional[ClassInfo]:
    """
    Get the class containing a given line number.

    Args:
        code: Python source code.
        line_number: 1-indexed line number.

    Returns:
        ClassInfo or None if the line is not inside a class.
    """
    classes = extract_classes(code)
    for cls in classes:
        if cls.line_start <= line_number <= cls.line_end:
            return cls
    return None
