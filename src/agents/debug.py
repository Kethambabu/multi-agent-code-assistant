"""
Debug Agent — Detects and helps fix bugs in code.

Uses bug_detector tools for static analysis and LLM for fix suggestions.

Dependency: agents.base, tools (bug_detector).
"""
import logging
from typing import Optional, Any, List

from src.agents.base import BaseAgent, AgentResult
from src.tools.bug_detector import detect_all_issues, BugReport
from src.utils.response_parsers import (
    extract_json_from_response,
    parse_issue_list_from_response,
)
from src.llm.prompts import build_code_analysis_prompt, OUTPUT_RULES


logger = logging.getLogger(__name__)

class DebugAgent(BaseAgent):
    """
    Analyzes code for bugs and provides fixes.
    Detects syntax, logic bugs (using LLM), and edge cases (manual rules).
    """

    @property
    def role(self) -> str:
        return "Debug Specialist"

    @property
    def goal(self) -> str:
        return "Identify and fix bugs in code"

    def execute(
        self,
        code: str,
        line_number: Optional[int] = None,
        memory_context: Optional[Any] = None,
        **kwargs,
    ) -> AgentResult:
        """Analyze code for bugs, edge cases, and suggest fixes."""
        try:
            # 1. Rule-based static checks (Syntax / Undefined)
            static_issues = detect_all_issues(code)
            
            # 2. Rule-based manual logic checks
            manual_issues = self._manual_logic_checks(code)
            
            # 3. LLM Logic & Edge Case Analysis
            llm_analysis = self._llm_logic_analysis(code)

            bugs_found = len(static_issues) > 0 or len(manual_issues) > 0 or llm_analysis.get("bugs_found", False)
            
            if not bugs_found:
                return AgentResult(
                    success=True,
                    output="No bugs detected. Code has been verified for syntax and logic.",
                    metadata={"issues_found": 0}
                )

            # Compile issues
            all_issues = []
            for issue in static_issues:
                all_issues.append(f"Line {issue.line_number} [{issue.severity.upper()}]: {issue.message}")
            all_issues.extend(manual_issues)
            all_issues.extend(llm_analysis.get("issues", []))

            # Suggested Fix logic
            fix_description = llm_analysis.get("fix", "No specific fix provided by LLM. See issues.")
            corrected_code = llm_analysis.get("corrected_code", "")

            # If there's a syntax error and LLM didn't provide corrected code, use the old _suggest_fix fallback
            if not corrected_code and static_issues:
                for issue in static_issues:
                    if issue.severity == "error":
                        corrected_code = self._suggest_fix(code, issue)
                        break
            
            # Build the UI friendly output
            ui_output = "### ⚠️ Issues Found\n"
            for iss in all_issues:
                ui_output += f"- {iss}\n"
            
            ui_output += f"\n### 🔧 Suggested Fix\n{fix_description}\n"
            
            if corrected_code:
                ui_output += f"\n```python\n{corrected_code}\n```"

            return AgentResult(
                success=True,
                output=ui_output,
                metadata={
                    "issues_found": len(all_issues),
                    "bugs_found": bugs_found,
                }
            )

        except Exception as e:
            logger.error(f"Debug analysis failed", exc_info=True)
            return AgentResult(
                success=False,
                output="",
                error=f"Debug analysis failed: {e}"
            )

    def _manual_logic_checks(self, code: str) -> List[str]:
        """Manual rule-based checks for common logical bugs."""
        issues = []
        code_lower = code.lower()
        if "max" in code_lower and "= 0" in code_lower:
            issues.append("Incorrect max initialization for negative values. (e.g. max = 0 fails if all inputs are negative)")
        if "min" in code_lower and "= 0" in code_lower:
            issues.append("Incorrect min initialization. (e.g. min = 0 fails if all inputs are positive)")
        if "/" in code and "if" not in code_lower and "try" not in code_lower and "except" not in code_lower:
            issues.append("Potential division by zero detected without guards.")
        if "len(" in code and "== 0" not in code and "if not " not in code:
            issues.append("Possible unhandled empty list case. Check len(list) == 0 before proceeding.")
        return issues

    def _llm_logic_analysis(self, code: str) -> dict:
        """Send code to LLM for logical bug and edge case checking."""
        prompt = (
            f"Analyze the following Python code to find logical bugs and edge case failures.\n"
            f"Specifically check for: negative numbers, empty lists, division by zero, incorrect initializations.\n\n"
            f"```python\n{code}\n```\n\n"
            f"Return ONLY valid JSON with this format:\n"
            f'{{"bugs_found": true, "issues": ["Issue 1"], "fix": "explanation", "corrected_code": "code"}}\n'
            f"{OUTPUT_RULES['return_only_json']}"
        )
        try:
            response = self.llm.generate(prompt, max_tokens=600, temperature=0.2)
            parsed = extract_json_from_response(response)
            return parsed if parsed else {}
        except Exception as e:
            logger.debug(f"LLM logic analysis failed: {e}")
            return {}

    def _suggest_fix(self, code: str, issue: BugReport) -> str:
        """Generate fix suggestion using LLM."""
        try:
            lines = code.split("\n")
            start_idx = max(0, issue.line_number - 3 - 1)
            end_idx = min(len(lines), issue.line_number + 3)
            surrounding = "\n".join(lines[start_idx:end_idx])

            prompt = (
                f"Given this code snippet with an error:\n\n{surrounding}\n\n"
                f"The issue is: {issue.message}\n\n"
                f"Provide only the fixed code line without explanation."
            )
            fix = self.llm.generate(prompt, max_tokens=50, temperature=0.3)
            return fix.strip() if fix else ""
        except Exception as e:
            logger.debug(f"Failed to suggest fix: {e}")
            return ""
