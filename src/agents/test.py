"""
Test Agent — Generates test cases and unit tests.

Uses function analysis to create comprehensive test suites via LLM.

Dependency: agents.base, tools (ast_parser, context_extractor).
"""
from typing import Optional, Any

from src.agents.base import BaseAgent, AgentResult
from src.tools.ast_parser import extract_functions, get_function_by_line
from src.tools.context_extractor import get_function_context, get_imports_context


class TestAgent(BaseAgent):
    """
    Generates test cases and unit tests for code.

    Analyzes functions and creates comprehensive test suites
    using LLM-generated test cases.
    """

    @property
    def role(self) -> str:
        return "Test Case Generator"

    @property
    def goal(self) -> str:
        return "Generate comprehensive test cases and unit tests"

    def execute(
        self,
        code: str,
        line_number: Optional[int] = None,
        test_framework: str = "pytest",
        coverage: str = "basic",
        memory_context: Optional[Any] = None,
        **kwargs,
    ) -> AgentResult:
        """
        Generate test cases for code.

        Args:
            code: Full source code.
            line_number: Specific function to test (optional).
            test_framework: 'pytest' or 'unittest'.
            coverage: 'basic', 'standard', 'comprehensive'.
            memory_context: Optional MemoryContext.

        Returns:
            AgentResult with generated tests.
        """
        try:
            if test_framework not in ("pytest", "unittest"):
                return AgentResult(
                    success=False,
                    output="",
                    error="test_framework must be 'pytest' or 'unittest'",
                )

            if line_number:
                tests = self._generate_function_tests(
                    code, line_number, test_framework, coverage,
                )
            else:
                tests = self._generate_suite_tests(code, test_framework, coverage)

            if not tests:
                return AgentResult(
                    success=False,
                    output="",
                    error="Could not generate tests",
                )

            if memory_context:
                stats = memory_context.get_details()
                changes = stats.get("metadata", {}).get("code_changes", 0)
                tests += f"\n\n# Memory Note: {changes} code changes tracked in session"

            return AgentResult(
                success=True,
                output=tests,
                metadata={
                    "framework": test_framework,
                    "coverage": coverage,
                    "line": line_number,
                    "used_memory": memory_context is not None,
                },
            )

        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                error=f"Test generation failed: {e}",
            )

    def _generate_function_tests(
        self, code: str, line_number: int, framework: str, coverage: str,
    ) -> str:
        """Generate tests for specific function."""
        func = get_function_by_line(code, line_number)
        if not func:
            return ""
        func_code = get_function_context(code, line_number)
        if not func_code:
            return ""
        return self._generate_tests_for_function(
            func_code, func.name, func.args, framework, coverage,
        )

    def _generate_suite_tests(
        self, code: str, framework: str, coverage: str,
    ) -> str:
        """Generate tests for all functions."""
        functions = extract_functions(code)
        imports = get_imports_context(code)

        if not functions:
            return ""

        test_suite = self._build_test_file_header(framework, imports)
        for func in functions:
            test_code = self._generate_tests_for_function(
                "", func.name, func.args, framework, coverage,
            )
            if test_code:
                test_suite += f"\n\n{test_code}"
        return test_suite

    def _generate_tests_for_function(
        self,
        func_code: str,
        func_name: str,
        func_args: list,
        framework: str,
        coverage: str,
    ) -> str:
        """Generate tests using LLM."""
        coverage_instructions = {
            "basic": "at least 2-3 basic test cases",
            "standard": "normal cases, edge cases, and error cases",
            "comprehensive": (
                "happy path, edge cases, boundary conditions, "
                "error cases, and integration scenarios"
            ),
        }
        coverage_detail = coverage_instructions.get(
            coverage, coverage_instructions["standard"]
        )

        prompt = (
            f"Generate {framework} test cases for the following function.\n\n"
            f"Function: {func_name}\n"
            f"Args: {', '.join(func_args) if func_args else 'none'}\n\n"
            f"Generate {coverage_detail}.\n\n"
            f"Framework: {framework}\n"
            f"Code style: Professional, well-commented\n"
            f"Use meaningful test names and assertions\n\n"
            f"Function code (if available):\n{func_code}\n\n"
            f"Generate only the test code, no explanations.\n"
        )

        try:
            tests = self.llm.generate(prompt, max_tokens=400, temperature=0.4)
            return self._format_tests(tests, func_name, framework)
        except Exception:
            return ""

    @staticmethod
    def _build_test_file_header(framework: str, imports: str) -> str:
        """Build test file header with imports."""
        if framework == "pytest":
            header = "import pytest\nfrom unittest.mock import Mock, patch\n\n"
        else:
            header = "import unittest\nfrom unittest.mock import Mock, patch\n\n"

        if imports:
            header += f"# Original imports\n{imports}\n\n"
        return header

    @staticmethod
    def _format_tests(test_code: str, func_name: str, framework: str) -> str:
        """Format generated tests."""
        test_code = test_code.strip()

        if framework == "unittest" and not test_code.startswith("class"):
            indented = "\n".join("    " + line for line in test_code.split("\n"))
            test_code = (
                f"class Test{func_name.title()}(unittest.TestCase):\n{indented}\n"
            )

        return test_code
