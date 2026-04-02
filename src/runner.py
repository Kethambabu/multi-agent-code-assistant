"""
Project Runner — Executes projects and captures output.

Runs Python files via subprocess and returns structured results
with stdout, stderr, return code, and execution time.

Dependency: file_manager (FileManager).
"""
import os
import subprocess
import sys
import time
import logging
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

from src.file_manager import FileManager


logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    """Structured result from executing a project."""

    stdout: str
    stderr: str
    return_code: int
    execution_time_ms: float
    entry_point: str
    success: bool

    def to_display(self) -> str:
        """Format result for UI display."""
        status = "✅ SUCCESS" if self.success else "❌ FAILED"
        header = (
            f"**{status}** — `{sys.executable} {self.entry_point}`\n"
            f"⏱️ {self.execution_time_ms:.0f}ms | "
            f"Exit code: {self.return_code}\n"
        )

        output_parts = [header]

        if self.stdout.strip():
            output_parts.append(
                f"\n**stdout:**\n```\n{self.stdout.strip()}\n```"
            )

        if self.stderr.strip():
            output_parts.append(
                f"\n**stderr:**\n```\n{self.stderr.strip()}\n```"
            )

        if not self.stdout.strip() and not self.stderr.strip():
            output_parts.append("\n_(no output)_")

        return "\n".join(output_parts)


class RunnerError(Exception):
    """Raised when project execution fails."""
    pass


class ProjectRunner:
    """
    Executes Python projects in the workspace and captures output.

    Safety features:
        - Configurable timeout (default 30s)
        - Working directory set to workspace root
        - Captures both stdout and stderr
        - Returns structured RunResult
    """

    # Default entry points to search for (in priority order)
    DEFAULT_ENTRY_POINTS = ("main.py", "app.py", "run.py", "manage.py")

    def __init__(
        self,
        file_manager: FileManager,
        timeout: int = 30,
    ) -> None:
        """
        Initialize with FileManager and timeout.

        Args:
            file_manager: FileManager for workspace access.
            timeout: Maximum execution time in seconds.
        """
        self.file_manager = file_manager
        self.timeout = timeout

    def _install_dependencies(self, workspace_root: str) -> Optional[str]:
        """Install dependencies from requirements.txt if it exists."""
        req_path = Path(workspace_root) / "requirements.txt"
        if not req_path.is_file():
            return None
        
        logger.info("Installing dependencies from requirements.txt...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                capture_output=True,
                text=True,
                cwd=workspace_root,
                timeout=120,
            )
            if result.returncode != 0:
                logger.error(f"Failed to install dependencies: {result.stderr}")
                return f"Dependency installation failed:\n{result.stderr}"
            return None
        except subprocess.TimeoutExpired:
            logger.warning("Dependency installation timed out.")
            return "Dependency installation timed out after 120s."
        except Exception as e:
            logger.error(f"Error installing dependencies: {e}", exc_info=True)
            return f"Error installing dependencies: {e}"

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(self, entry_point: Optional[str] = None) -> RunResult:
        """
        Run a Python file and capture output.

        Args:
            entry_point: Relative path to the Python file to run.
                         If None, auto-detects entry point.

        Returns:
            RunResult with stdout, stderr, return code, etc.

        Raises:
            RunnerError: If file not found or execution setup fails.
        """
        # Auto-detect entry point if not specified
        if not entry_point:
            entry_point = self.detect_entry_point()
            if not entry_point:
                return RunResult(
                    stdout="",
                    stderr="No entry point found. Create main.py, app.py, or run.py.",
                    return_code=-1,
                    execution_time_ms=0,
                    entry_point="(none)",
                    success=False,
                )

        # Verify file exists
        if not self.file_manager.file_exists(entry_point):
            return RunResult(
                stdout="",
                stderr=f"Entry point not found: {entry_point}",
                return_code=-1,
                execution_time_ms=0,
                entry_point=entry_point,
                success=False,
            )

        # Build full path
        workspace_root = self.file_manager.get_workspace_root()
        full_path = str(Path(workspace_root) / entry_point)

        # Install dependencies if present
        dep_error = self._install_dependencies(workspace_root)
        if dep_error:
            return RunResult(
                stdout="",
                stderr=dep_error,
                return_code=-1,
                execution_time_ms=0,
                entry_point=entry_point,
                success=False,
            )

        logger.info(f"Running: {sys.executable} {entry_point} (timeout: {self.timeout}s)")

        # Execute
        start_time = time.time()
        try:
            # Set runner mode environment variable so apps know they're running in test mode
            env = os.environ.copy()
            env['RUNNER_MODE'] = '1'
            
            result = subprocess.run(
                [sys.executable, full_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=workspace_root,
                env=env,
            )

            elapsed_ms = (time.time() - start_time) * 1000

            run_result = RunResult(
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                execution_time_ms=elapsed_ms,
                entry_point=entry_point,
                success=result.returncode == 0,
            )

            logger.info(
                f"Execution complete: code={result.returncode}, "
                f"time={elapsed_ms:.0f}ms"
            )
            return run_result

        except subprocess.TimeoutExpired:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.warning(f"Execution timed out after {self.timeout}s")
            return RunResult(
                stdout="",
                stderr=f"⏰ Execution timed out after {self.timeout} seconds.",
                return_code=-1,
                execution_time_ms=elapsed_ms,
                entry_point=entry_point,
                success=False,
            )

        except FileNotFoundError:
            return RunResult(
                stdout="",
                stderr="Python interpreter not found. Is Python installed and in PATH?",
                return_code=-1,
                execution_time_ms=0,
                entry_point=entry_point,
                success=False,
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"Execution error: {e}", exc_info=True)
            return RunResult(
                stdout="",
                stderr=f"Execution error: {e}",
                return_code=-1,
                execution_time_ms=elapsed_ms,
                entry_point=entry_point,
                success=False,
            )

    # ------------------------------------------------------------------
    # Entry point detection
    # ------------------------------------------------------------------

    def detect_entry_point(self) -> Optional[str]:
        """
        Auto-detect the project's entry point.

        Checks for common entry points in priority order:
            main.py → app.py → run.py → manage.py → first .py file

        Returns:
            Relative path to the entry point, or None.
        """
        # Check default entry points
        for candidate in self.DEFAULT_ENTRY_POINTS:
            if self.file_manager.file_exists(candidate):
                logger.info(f"Auto-detected entry point: {candidate}")
                return candidate

        # Fallback: find any .py file at the root level
        all_files = self.file_manager.list_files(extension_filter=".py")
        root_py_files = [f for f in all_files if "/" not in f]

        if root_py_files:
            entry = root_py_files[0]
            logger.info(f"Fallback entry point: {entry}")
            return entry

        # Last resort: any .py file
        if all_files:
            entry = all_files[0]
            logger.info(f"Last-resort entry point: {entry}")
            return entry

        return None

    def __repr__(self) -> str:
        entry = self.detect_entry_point() or "(none)"
        return f"ProjectRunner(entry_point='{entry}', timeout={self.timeout}s)"
