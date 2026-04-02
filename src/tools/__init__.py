"""
Tools Layer — Pure static-analysis utilities.

All tools are pure functions operating on source code strings.
They have ZERO dependency on LLM, agents, or any other layer.

Modules:
    ast_parser:        AST-based structural extraction
    bug_detector:      Static bug detection (syntax, undefined vars, unused imports)
    context_extractor: Cursor-context extraction for code completion and analysis
"""
from src.tools.ast_parser import (
    FunctionInfo,
    ClassInfo,
    ImportInfo,
    ParseError,
    get_ast,
    extract_functions,
    extract_classes,
    extract_imports,
    get_function_by_line,
    get_class_by_line,
)
from src.tools.bug_detector import (
    BugReport,
    detect_syntax_errors,
    detect_undefined_variables,
    detect_unused_imports,
    detect_all_issues,
)
from src.tools.context_extractor import (
    CodeContext,
    get_current_context,
    get_function_context,
    get_imports_context,
    get_code_before_cursor,
    get_code_after_cursor,
    get_line_content,
    get_context_summary,
)

__all__ = [
    # AST Parser
    "FunctionInfo", "ClassInfo", "ImportInfo", "ParseError",
    "get_ast", "extract_functions", "extract_classes", "extract_imports",
    "get_function_by_line", "get_class_by_line",
    # Bug Detector
    "BugReport",
    "detect_syntax_errors", "detect_undefined_variables",
    "detect_unused_imports", "detect_all_issues",
    # Context Extractor
    "CodeContext",
    "get_current_context", "get_function_context", "get_imports_context",
    "get_code_before_cursor", "get_code_after_cursor",
    "get_line_content", "get_context_summary",
]
