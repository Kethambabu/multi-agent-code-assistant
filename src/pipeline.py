"""
Assistant Pipeline — End-to-end orchestration of the code assistant.

Wires together all components:
    workspace + file_manager + agents + file_selector + runner

Flow:
    prompt → file selection → modification → save → run → output

Dependency: All Phase 1-6 modules + existing agents.
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from src.config import SystemConfig, load_config
from src.file_manager import FileManager
from src.project_handler import ProjectHandler
from src.file_selector import FileSelector
from src.runner import ProjectRunner, RunResult
from src.llm.huggingface import HuggingFaceLLM
from src.agents.base import AgentRegistry, AgentResult
from src.agents.editor import EditorAgent
from src.agents.creator import CreatorAgent
from src.agents.debug import DebugAgent
from src.agents.explain import ExplainAgent
from src.agents.test import TestAgent
from src.memory.store import MemoryStore
from src.memory.context import MemoryContext


logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result from a full pipeline execution."""

    success: bool
    message: str
    modified_files: List[str] = field(default_factory=list)
    created_files: List[str] = field(default_factory=list)
    agent_results: List[AgentResult] = field(default_factory=list)
    run_result: Optional[RunResult] = None
    error: Optional[str] = None


class AssistantPipeline:
    """
    End-to-end pipeline: prompt → files → edit → save → run.

    This is the main entry point for the transformed assistant.
    Replaces DeveloperAssistantSystem as the primary coordinator.

    Capabilities:
        - Upload zip projects or create new ones
        - Modify existing files based on natural language prompts
        - Create entire projects from scratch
        - Execute projects and return output
        - Retain backward-compatible analysis agents (debug, explain, test)
    """

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        """
        Initialize the full assistant pipeline via dependency injection.

        Args:
            config: System configuration. If None, loads from environment.
        """
        if config is None:
            config = load_config()

        self.config = config
        logger.info("Initializing Assistant Pipeline...")

        # 1. Core infrastructure
        self.file_manager = FileManager(config.workspace.root_dir)
        self.llm = HuggingFaceLLM(config.hf)
        logger.info(f"✓ LLM initialized ({config.hf.model})")

        # 2. Project handling
        self.project_handler = ProjectHandler(self.file_manager)

        # 3. File selection
        self.file_selector = FileSelector(self.file_manager, self.llm)

        # 4. Execution engine
        self.runner = ProjectRunner(
            self.file_manager,
            timeout=config.runner.timeout_seconds,
        )

        # 5. Agents (new + existing)
        self.editor = EditorAgent(self.llm, self.file_manager)
        self.creator = CreatorAgent(self.llm, self.file_manager)

        self.registry = AgentRegistry()
        self.registry.register("editor", self.editor)
        self.registry.register("creator", self.creator)
        self.registry.register("debug", DebugAgent(self.llm))
        self.registry.register("explain", ExplainAgent(self.llm))
        self.registry.register("test", TestAgent(self.llm))
        logger.info(f"✓ Agents initialized ({len(self.registry.list_agents())} agents)")

        # 6. Memory (retained for analysis agents)
        self.memory = MemoryStore(
            max_history=config.memory.max_history,
            max_snapshots=config.memory.max_snapshots,
        )
        logger.info("✓ Memory store initialized")

        logger.info("✓ Assistant Pipeline fully initialized\n")

    # ------------------------------------------------------------------
    # Primary API: Process user prompt
    # ------------------------------------------------------------------

    def process_prompt(self, prompt: str) -> PipelineResult:
        """
        Process a user prompt through the full pipeline.

        Decision flow:
            1. Is workspace empty? → Create project (CreatorAgent)
            2. Has project files?  → Select files → Edit each (EditorAgent)

        Args:
            prompt: User's natural language instruction.

        Returns:
            PipelineResult with all changes and metadata.
        """
        if not prompt or not prompt.strip():
            return PipelineResult(
                success=False,
                message="",
                error="No prompt provided.",
            )

        logger.info(f"Processing prompt: {prompt[:80]}...")

        # Decision: create vs. edit
        if self.file_manager.is_empty():
            return self._create_project(prompt)
        else:
            return self._edit_project(prompt)

    def _create_project(self, prompt: str) -> PipelineResult:
        """Create a new project from prompt (workspace is empty)."""
        logger.info("Workspace is empty — creating new project.")

        result = self.creator.execute(prompt=prompt)

        if result.success:
            created = result.metadata.get("files_created", []) if result.metadata else []
            return PipelineResult(
                success=True,
                message=result.output,
                created_files=created,
                agent_results=[result],
            )
        else:
            return PipelineResult(
                success=False,
                message="",
                error=result.error or "Project creation failed.",
                agent_results=[result],
            )

    def _edit_project(self, prompt: str) -> PipelineResult:
        """Edit existing project files based on prompt."""
        # 1. Select files to modify
        target_files = self.file_selector.select_files(prompt)
        logger.info(f"Selected {len(target_files)} file(s) to modify: {target_files}")

        if not target_files:
            return PipelineResult(
                success=False,
                message="",
                error="Could not determine which files to modify.",
            )

        # 2. Edit each file
        modified_files: List[str] = []
        agent_results: List[AgentResult] = []

        for file_path in target_files:
            logger.info(f"Editing: {file_path}")
            result = self.editor.execute(
                file_path=file_path,
                prompt=prompt,
            )
            agent_results.append(result)

            if result.success:
                modified_files.append(file_path)
            else:
                logger.warning(
                    f"Failed to edit {file_path}: {result.error}"
                )

        # 3. Build summary
        if modified_files:
            file_list = "\n".join(f"  ✅ {f}" for f in modified_files)
            failed = [f for f in target_files if f not in modified_files]
            message = f"**Modified {len(modified_files)} file(s):**\n{file_list}"
            if failed:
                fail_list = "\n".join(f"  ❌ {f}" for f in failed)
                message += f"\n\n**Failed:**\n{fail_list}"

            return PipelineResult(
                success=True,
                message=message,
                modified_files=modified_files,
                agent_results=agent_results,
            )
        else:
            return PipelineResult(
                success=False,
                message="",
                error="Failed to modify any files.",
                agent_results=agent_results,
            )

    # ------------------------------------------------------------------
    # Project management
    # ------------------------------------------------------------------

    def upload_project(self, zip_bytes: bytes) -> Dict[str, Any]:
        """
        Upload and extract a zip project into the workspace.

        Args:
            zip_bytes: Raw bytes of the zip file.

        Returns:
            Dict with file list and project info.
        """
        return self.project_handler.upload_project(zip_bytes)

    def clear_workspace(self) -> None:
        """Clear all project files from workspace."""
        self.project_handler.clear_workspace()

    def get_project_info(self) -> Dict[str, Any]:
        """Get current project information."""
        return self.project_handler.get_project_info()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run_project(self, entry_point: Optional[str] = None) -> RunResult:
        """
        Execute the project and return results.

        Args:
            entry_point: Python file to run. Auto-detects if None.

        Returns:
            RunResult with stdout, stderr, timing, etc.
        """
        return self.runner.run(entry_point)

    # ------------------------------------------------------------------
    # File operations (direct access)
    # ------------------------------------------------------------------

    def read_file(self, relative_path: str) -> str:
        """Read a project file."""
        return self.file_manager.read_file(relative_path)

    def list_files(self) -> List[str]:
        """List all project files."""
        return self.file_manager.list_files()

    # ------------------------------------------------------------------
    # Legacy analysis API (backward compatible)
    # ------------------------------------------------------------------

    def analyze_code(self, code: str) -> AgentResult:
        """Run debug agent on code string (backward compatible)."""
        return self.registry.execute("debug", code)

    def explain_code(self, code: str) -> AgentResult:
        """Run explain agent on code string (backward compatible)."""
        return self.registry.execute("explain", code)

    def generate_tests(self, code: str) -> AgentResult:
        """Run test agent on code string (backward compatible)."""
        return self.registry.execute("test", code)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status and configuration summary."""
        return {
            "agents": self.registry.list_agents(),
            "model": self.config.hf.model,
            "workspace": self.get_project_info(),
            "entry_point": self.runner.detect_entry_point(),
            "memory": self.memory.get_statistics(),
        }

    def __repr__(self) -> str:
        info = self.get_project_info()
        return (
            f"AssistantPipeline("
            f"model={self.config.hf.model}, "
            f"files={info['total_files']}, "
            f"agents={len(self.registry.list_agents())})"
        )
