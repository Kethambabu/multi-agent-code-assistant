"""
Explain Agent — Provides detailed code explanations.

Uses AST parser and context extraction for analysis, LLM for explanations.

Dependency: agents.base, tools (ast_parser, context_extractor).
"""
import logging
from typing import Optional, Any

from src.agents.base import BaseAgent, AgentResult
from src.tools.ast_parser import (
    extract_functions,
    extract_classes,
    get_function_by_line,
    get_class_by_line,
)
from src.tools.context_extractor import (
    get_current_context,
    get_function_context,
    get_imports_context,
)


logger = logging.getLogger(__name__)


class ExplainAgent(BaseAgent):
    """
    Explains code structure and functionality.

    Provides detailed explanations of functions, classes,
    and overall code structure using LLM.
    """

    @property
    def role(self) -> str:
        return "Code Explanation Expert"

    @property
    def goal(self) -> str:
        return "Provide clear and comprehensive code explanations"

    def execute(
        self,
        code: str,
        line_number: Optional[int] = None,
        detail_level: str = "medium",
        memory_context: Optional[Any] = None,
        **kwargs,
    ) -> AgentResult:
        """
        Explain code at given line or entire structure.

        Args:
            code: Full source code.
            line_number: Specific line to explain (optional).
            detail_level: 'brief', 'medium', 'detailed'.
            memory_context: Optional MemoryContext.

        Returns:
            AgentResult with code explanation.
        """
        try:
            if line_number:
                explanation = self._explain_at_line(code, line_number, detail_level)
            else:
                explanation = self._explain_structure(code, detail_level)

            if memory_context:
                recent = memory_context.get_recent_responses(
                    agent_name="ExplainAgent", limit=1,
                )
                if recent:
                    explanation += "\n\n[Note: Previous explanation context available in memory]"

            return AgentResult(
                success=True,
                output=explanation,
                metadata={
                    "detail_level": detail_level,
                    "line": line_number,
                    "used_memory": memory_context is not None,
                },
            )

        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                error=f"Explanation generation failed: {e}",
            )

    def _explain_at_line(self, code: str, line_number: int, detail_level: str) -> str:
        """Explain specific function or class at line."""
        func = get_function_by_line(code, line_number)
        if func:
            context = get_function_context(code, line_number)
            return self._generate_explanation(context, f"Function: {func.name}", detail_level)

        cls = get_class_by_line(code, line_number)
        if cls:
            context = get_current_context(code, line_number, context_lines=20)
            if context:
                return self._generate_explanation(
                    context.surrounding_code, f"Class: {cls.name}", detail_level,
                )

        context = get_current_context(code, line_number, context_lines=5)
        if context:
            return self._generate_explanation(
                context.surrounding_code, f"Code around line {line_number}", detail_level,
            )

        return "Could not extract context to explain."

    def _explain_structure(self, code: str, detail_level: str) -> str:
        """Explain overall code structure."""
        functions = extract_functions(code)
        classes = extract_classes(code)
        imports = get_imports_context(code)

        class_lines = "\n".join(
            f"  - {c.name} (methods: {', '.join(c.methods)})" for c in classes
        )
        func_lines = "\n".join(
            f"  - {f.name}({', '.join(f.args)})" for f in functions
        )

        structure = (
            f"Code Structure Overview:\n"
            f"- Imports: {len(imports.split(chr(10)))} modules\n"
            f"- Classes: {len(classes)}\n"
            f"- Functions: {len(functions)}\n\n"
            f"Imports:\n{imports}\n\n"
            f"Classes:\n{class_lines}\n\n"
            f"Functions:\n{func_lines}"
        )

        return self._generate_explanation(structure, "Code Structure", detail_level)

    def _generate_explanation(
        self, code_context: str, subject: str, detail_level: str,
    ) -> str:
        """Generate LLM-based explanation."""
        detail_instructions = {
            "brief": "in 2-3 sentences",
            "medium": "in 5-10 sentences",
            "detailed": "comprehensively with multiple paragraphs",
        }
        instruction = detail_instructions.get(detail_level, detail_instructions["medium"])

        prompt = (
            f"Explain the following {subject} code {instruction}.\n\n"
            f"Focus on:\n"
            f"- What the code does\n"
            f"- Key logic and flow\n"
            f"- Important variables and their purposes\n"
            f"- Edge cases or special handling\n\n"
            f"Code:\n{code_context}\n\n"
            f"Explanation:\n"
        )

        try:
            explanation = self.llm.generate(
                prompt,
                max_tokens=300 if detail_level == "detailed" else 200,
                temperature=0.3,
            )
            return f"{subject} Explanation:\n\n{explanation.strip()}"
        except Exception as e:
            logger.debug(f"Could not generate explanation for {subject}: {e}")
            return f"Could not generate explanation for {subject}"
