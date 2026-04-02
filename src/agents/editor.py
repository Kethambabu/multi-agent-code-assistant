"""
Editor Agent — Modifies real project files based on user instructions.

Reads a file from disk, sends it to LLM with edit instructions,
receives the modified code, and writes it back to disk.

Dependency: agents.base (BaseAgent), file_manager, response_parsers.
"""
import logging
from typing import Optional, Any

from src.agents.base import BaseAgent, AgentResult
from src.file_manager import FileManager, FileManagerError
from src.utils.response_parsers import extract_code_from_markdown
from src.llm.prompts import build_code_modification_prompt


logger = logging.getLogger(__name__)


class EditorAgent(BaseAgent):
    """
    Modifies project files based on natural language instructions.

    Pipeline:
        1. Read file from workspace via FileManager
        2. Build LLM prompt with file contents + user instruction
        3. Send to LLM → receive modified code
        4. Strip markdown fences and extract clean code
        5. Write modified code back to disk
        6. Return AgentResult with change summary
    """

    def __init__(self, llm, file_manager: FileManager) -> None:
        """
        Initialize with LLM provider and FileManager.

        Args:
            llm: Any object satisfying LLMProvider protocol.
            file_manager: FileManager instance for workspace I/O.
        """
        super().__init__(llm)
        self.file_manager = file_manager

    @property
    def role(self) -> str:
        return "Code Editor"

    @property
    def goal(self) -> str:
        return "Modify project files based on user instructions"

    def execute(
        self,
        context: str = "",
        file_path: str = "",
        prompt: str = "",
        memory_context: Optional[Any] = None,
        **kwargs,
    ) -> AgentResult:
        """
        Edit a file based on user instruction.

        Args:
            context: Unused (kept for BaseAgent compatibility).
            file_path: Relative path to the file to edit.
            prompt: User's natural-language edit instruction.
            memory_context: Optional memory context.
            **kwargs: Additional arguments.

        Returns:
            AgentResult with the change summary and metadata.
        """
        if not file_path:
            return AgentResult(
                success=False,
                output="",
                error="No file_path specified for editing.",
            )

        if not prompt:
            return AgentResult(
                success=False,
                output="",
                error="No edit instruction (prompt) provided.",
            )

        try:
            # 1. Read existing file
            original_code = self.file_manager.read_file(file_path)
            logger.info(f"Read file: {file_path} ({len(original_code)} chars)")

            # 2. Determine file extension for language hint
            ext = file_path.rsplit(".", 1)[-1] if "." in file_path else "txt"
            lang = self._extension_to_language(ext)

            # 3. Build LLM prompt
            llm_prompt = self._build_edit_prompt(
                original_code=original_code,
                instruction=prompt,
                file_path=file_path,
                language=lang,
            )

            # 4. Call LLM
            llm_response = self.llm.generate(
                llm_prompt,
                max_tokens=2000,
                temperature=0.2,
            )

            if not llm_response or llm_response.startswith("Error:"):
                return AgentResult(
                    success=False,
                    output="",
                    error=f"LLM failed: {llm_response}",
                )

            # 5. Extract clean code from response
            modified_code = self._extract_code(llm_response, lang)

            if not modified_code.strip():
                return AgentResult(
                    success=False,
                    output="",
                    error="LLM returned empty code. File was not modified.",
                )

            # 6. Write modified code back to disk
            self.file_manager.write_file(file_path, modified_code)
            logger.info(f"Wrote modified file: {file_path} ({len(modified_code)} chars)")

            # 7. Build change summary
            diff_summary = self._build_diff_summary(original_code, modified_code)

            return AgentResult(
                success=True,
                output=f"✅ Modified `{file_path}`\n\n{diff_summary}",
                metadata={
                    "file_path": file_path,
                    "original_length": len(original_code),
                    "modified_length": len(modified_code),
                    "instruction": prompt[:100],
                },
            )

        except FileManagerError as e:
            return AgentResult(
                success=False,
                output="",
                error=f"File error: {e}",
            )
        except Exception as e:
            logger.error(f"EditorAgent failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output="",
                error=f"Edit failed: {e}",
            )

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def _build_edit_prompt(
        self,
        original_code: str,
        instruction: str,
        file_path: str,
        language: str,
    ) -> str:
        """Build the LLM prompt for file editing using template."""
        # Use the new prompt template builder
        template_prompt = build_code_modification_prompt(
            code=original_code,
            instruction=instruction,
            role="code_editor",
            file_ext=language,
        )
        
        # Add additional context about file path
        return f"FILE: {file_path}\n\n{template_prompt}"

    # ------------------------------------------------------------------
    # Code extraction
    # ------------------------------------------------------------------

    def _extract_code(self, llm_response: str, language: str) -> str:
        """
        Extract clean code from LLM response using utility parser.
        
        Handles: ```language code```, ``` code ```, and raw code.
        """
        # Use the new response parser
        code = extract_code_from_markdown(llm_response, language=language)
        if code:
            return code
        
        # Fallback: return as-is if no fences found
        return llm_response.strip()

    # ------------------------------------------------------------------
    # Diff summary
    # ------------------------------------------------------------------

    def _build_diff_summary(self, original: str, modified: str) -> str:
        """Build a human-readable summary of changes."""
        orig_lines = original.split("\n")
        mod_lines = modified.split("\n")

        added = len(mod_lines) - len(orig_lines)
        if added > 0:
            summary = f"📊 **Changes**: +{added} lines (total: {len(mod_lines)} lines)\n"
        elif added < 0:
            summary = f"📊 **Changes**: {added} lines (total: {len(mod_lines)} lines)\n"
        else:
            summary = f"📊 **Changes**: modified in-place ({len(mod_lines)} lines)\n"

        # Show first few added/changed lines
        new_lines = []
        for line in mod_lines:
            if line.strip() and line not in orig_lines:
                new_lines.append(line)
        if new_lines:
            preview = "\n".join(f"  + {l}" for l in new_lines[:5])
            if len(new_lines) > 5:
                preview += f"\n  ... and {len(new_lines) - 5} more new lines"
            summary += f"\n**New/Changed lines:**\n```\n{preview}\n```"

        return summary

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _extension_to_language(ext: str) -> str:
        """Map file extension to language name."""
        mapping = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "html": "html",
            "css": "css",
            "json": "json",
            "yaml": "yaml",
            "yml": "yaml",
            "md": "markdown",
            "txt": "text",
            "toml": "toml",
            "sh": "bash",
            "bat": "batch",
        }
        return mapping.get(ext.lower(), ext)
