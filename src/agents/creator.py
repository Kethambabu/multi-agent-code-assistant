"""
Creator Agent — Generates new projects from natural language descriptions.

When the workspace is empty, this agent generates a complete project
structure (multiple files) using the LLM and writes them to disk.

Dependency: agents.base (BaseAgent), file_manager, response_parsers.
"""
import logging
from typing import Optional, Any, Dict

from src.agents.base import BaseAgent, AgentResult
from src.file_manager import FileManager, FileManagerError
from src.utils.response_parsers import parse_file_map_from_response
from src.llm.prompts import build_project_creation_prompt


logger = logging.getLogger(__name__)


class CreatorAgent(BaseAgent):
    """
    Creates new project structures from natural language prompts.

    Pipeline:
        1. Receive user description (e.g. "Create a Flask REST API")
        2. Send to LLM → receive JSON with file map
        3. Parse JSON: {"files": {"main.py": "code...", ...}}
        4. Create each file via FileManager
        5. Return AgentResult with list of created files
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
        return "Project Creator"

    @property
    def goal(self) -> str:
        return "Generate complete project structures from descriptions"

    def execute(
        self,
        context: str = "",
        prompt: str = "",
        memory_context: Optional[Any] = None,
        **kwargs,
    ) -> AgentResult:
        """
        Create a new project from a natural language description.

        Args:
            context: Unused (kept for BaseAgent compatibility).
            prompt: User's project description.
            memory_context: Optional memory context.
            **kwargs: Additional arguments.

        Returns:
            AgentResult with list of created files.
        """
        if not prompt:
            return AgentResult(
                success=False,
                output="",
                error="No project description provided.",
            )

        try:
            # 1. Build LLM prompt
            llm_prompt = self._build_creation_prompt(prompt)

            # 2. Call LLM
            llm_response = self.llm.generate(
                llm_prompt,
                max_tokens=3000,
                temperature=0.3,
            )

            if not llm_response or llm_response.startswith("Error:"):
                return AgentResult(
                    success=False,
                    output="",
                    error=f"LLM failed: {llm_response}",
                )

            # 3. Parse file map from response
            file_map = self._parse_file_map(llm_response)

            if not file_map:
                return AgentResult(
                    success=False,
                    output="",
                    error="Could not parse project structure from LLM response.",
                )

            # 4. Create files
            created_files = []
            for file_path, content in file_map.items():
                # Safety: skip absolute paths and traversal attempts
                if file_path.startswith("/") or ".." in file_path:
                    logger.warning(f"Skipping unsafe path: {file_path}")
                    continue

                self.file_manager.write_file(file_path, content)
                created_files.append(file_path)
                logger.info(f"Created: {file_path}")

            if not created_files:
                return AgentResult(
                    success=False,
                    output="",
                    error="No valid files were created.",
                )

            # 5. Build output summary
            file_list = "\n".join(f"  📄 {f}" for f in sorted(created_files))
            output = (
                f"✅ **Project created** — {len(created_files)} files\n\n"
                f"**Files:**\n{file_list}\n\n"
                f"📁 Location: `{self.file_manager.get_workspace_root()}`"
            )

            return AgentResult(
                success=True,
                output=output,
                metadata={
                    "files_created": created_files,
                    "total_files": len(created_files),
                    "prompt": prompt[:100],
                },
            )

        except FileManagerError as e:
            return AgentResult(
                success=False,
                output="",
                error=f"File error during project creation: {e}",
            )
        except Exception as e:
            logger.error(f"CreatorAgent failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output="",
                error=f"Project creation failed: {e}",
            )

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def _build_creation_prompt(self, description: str) -> str:
        """Build the LLM prompt for project generation using template."""
        return build_project_creation_prompt(description)

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_file_map(self, llm_response: str) -> Dict[str, str]:
        """Parse the file map from LLM response using utility parser."""
        file_map = parse_file_map_from_response(llm_response)
        return file_map if file_map else {}
