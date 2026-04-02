"""
Code Completion Agent.

Generates code completions at cursor position using context extraction
and LLM generation.

Dependency: agents.base, tools (context_extractor, ast_parser).
"""
from typing import Any, Optional

from src.agents.base import BaseAgent, AgentResult
from src.tools.context_extractor import get_current_context, get_function_context
from src.tools.ast_parser import get_function_by_line, get_class_by_line


class CompletionAgent(BaseAgent):
    """
    Generates code completions at cursor position.

    Uses context extraction to understand surrounding code
    and generates appropriate completions via LLM.
    """

    @property
    def role(self) -> str:
        return "Code Completion Specialist"

    @property
    def goal(self) -> str:
        return "Generate accurate and contextual code completions"

    def execute(
        self,
        code: str,
        line_number: int = 1,
        max_tokens: int = 150,
        temperature: float = 0.5,
        memory_context: Optional[Any] = None,
        **kwargs,
    ) -> AgentResult:
        """
        Generate code completion at specified line.

        Args:
            code: Full source code.
            line_number: Line where completion is needed.
            max_tokens: Maximum completion length.
            temperature: Generation temperature.
            memory_context: Optional MemoryContext for historical context.

        Returns:
            AgentResult with generated completion.
        """
        try:
            context = get_current_context(code, line_number, context_lines=10)
            if not context:
                return AgentResult(
                    success=False,
                    output="",
                    error="Could not extract context at given line.",
                )

            scope_info = self._get_scope_info(code, line_number)
            prompt = self._build_completion_prompt(
                context=context,
                scope_info=scope_info,
                line_number=line_number,
            )

            # Enrich with memory if available
            if memory_context:
                recent = memory_context.get_recent_responses(
                    agent_name="CompletionAgent", limit=2,
                )
                if recent:
                    history = "\n".join(
                        f"# Previous: {r['content'][:60]}..." for r in recent
                    )
                    prompt = f"{history}\n\n{prompt}"

            completion = self.llm.generate(
                prompt, max_tokens=max_tokens, temperature=temperature,
            )

            return AgentResult(
                success=True,
                output=completion.strip(),
                metadata={
                    "line": line_number,
                    "scope": scope_info,
                    "tokens": max_tokens,
                    "used_memory": memory_context is not None,
                },
            )

        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                error=f"Completion generation failed: {e}",
            )

    def _get_scope_info(self, code: str, line_number: int) -> str:
        """Get human-readable scope information."""
        func = get_function_by_line(code, line_number)
        if func:
            return f"in function '{func.name}'"
        cls = get_class_by_line(code, line_number)
        if cls:
            return f"in class '{cls.name}'"
        return "at module level"

    def _build_completion_prompt(
        self, context: Any, scope_info: str, line_number: int,
    ) -> str:
        """Build optimized completion prompt."""
        return (
            f"You are an expert Python code completion engine.\n\n"
            f"Context Information:\n{context.surrounding_code}\n\n"
            f"Scope: {scope_info}\nLine: {line_number}\n\n"
            f"Complete the code at the cursor position. "
            f"Generate only the completion, not the entire function.\n"
            f"Maintain code style and indentation."
        )
