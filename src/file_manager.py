"""
File Manager — CRUD operations on workspace files.

Provides safe, sandboxed file I/O for the assistant pipeline.
All paths are relative to the workspace root to prevent path traversal.

Dependency: None (leaf module).
"""
import os
import shutil
from pathlib import Path
from typing import List, Optional


class FileManagerError(Exception):
    """Raised when a file operation fails."""
    pass


class FileManager:
    """
    Safe file operations scoped to a workspace directory.

    All paths passed to methods are relative to workspace_root.
    Absolute paths, '..' traversal, and paths outside the workspace
    are rejected to prevent security issues.
    """

    # Directories to skip when listing files
    EXCLUDED_DIRS = {"__pycache__", ".git", "venv", ".venv", "node_modules", ".idea", ".vscode", "myvenv"}

    def __init__(self, workspace_root: str) -> None:
        """
        Initialize FileManager with workspace root directory.

        Args:
            workspace_root: Absolute or relative path to workspace directory.
                            Created automatically if it doesn't exist.
        """
        self._root = Path(workspace_root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Path validation
    # ------------------------------------------------------------------

    def _resolve_safe(self, relative_path: str) -> Path:
        """
        Resolve a relative path safely within the workspace.

        Raises:
            FileManagerError: If path escapes the workspace.
        """
        if not relative_path or not relative_path.strip():
            raise FileManagerError("Path cannot be empty.")

        # Reject absolute paths
        if os.path.isabs(relative_path):
            raise FileManagerError(
                f"Absolute paths are not allowed: '{relative_path}'. "
                "Use paths relative to the workspace root."
            )

        # Reject path traversal
        if ".." in relative_path.split(os.sep) or ".." in relative_path.split("/"):
            raise FileManagerError(
                f"Path traversal ('..') is not allowed: '{relative_path}'."
            )

        resolved = (self._root / relative_path).resolve()

        # Final check: ensure resolved path is inside workspace
        try:
            resolved.relative_to(self._root)
        except ValueError:
            raise FileManagerError(
                f"Path '{relative_path}' resolves outside workspace."
            )

        return resolved

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def read_file(self, relative_path: str) -> str:
        """
        Read file contents as a string.

        Args:
            relative_path: Path relative to workspace root.

        Returns:
            File contents as string.

        Raises:
            FileManagerError: If file doesn't exist or can't be read.
        """
        path = self._resolve_safe(relative_path)
        if not path.is_file():
            raise FileManagerError(f"File not found: '{relative_path}'")
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            raise FileManagerError(f"Failed to read '{relative_path}': {e}")

    def file_exists(self, relative_path: str) -> bool:
        """Check if a file exists in the workspace."""
        try:
            path = self._resolve_safe(relative_path)
            return path.is_file()
        except FileManagerError:
            return False

    def list_files(self, extension_filter: Optional[str] = None) -> List[str]:
        """
        List all files in workspace recursively.

        Args:
            extension_filter: Optional file extension filter (e.g. '.py').
                              Include the dot.

        Returns:
            Sorted list of relative file paths.
        """
        files: List[str] = []
        for dirpath, dirnames, filenames in os.walk(self._root):
            # Skip excluded directories (modifies dirnames in-place)
            dirnames[:] = [d for d in dirnames if d not in self.EXCLUDED_DIRS]

            for filename in filenames:
                if filename == ".gitkeep":
                    continue
                if extension_filter and not filename.endswith(extension_filter):
                    continue

                full_path = Path(dirpath) / filename
                rel_path = full_path.relative_to(self._root)
                files.append(str(rel_path).replace("\\", "/"))

        return sorted(files)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def write_file(self, relative_path: str, content: str) -> None:
        """
        Write content to a file. Creates parent directories if needed.
        Overwrites if file exists.

        Args:
            relative_path: Path relative to workspace root.
            content: File content to write.
        """
        path = self._resolve_safe(relative_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except Exception as e:
            raise FileManagerError(f"Failed to write '{relative_path}': {e}")

    def create_file(self, relative_path: str, content: str = "") -> None:
        """
        Create a new file. Raises error if file already exists.

        Args:
            relative_path: Path relative to workspace root.
            content: Initial file content (default empty).

        Raises:
            FileManagerError: If file already exists.
        """
        path = self._resolve_safe(relative_path)
        if path.is_file():
            raise FileManagerError(f"File already exists: '{relative_path}'")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except Exception as e:
            raise FileManagerError(f"Failed to create '{relative_path}': {e}")

    def delete_file(self, relative_path: str) -> None:
        """
        Delete a file from workspace.

        Args:
            relative_path: Path relative to workspace root.

        Raises:
            FileManagerError: If file doesn't exist.
        """
        path = self._resolve_safe(relative_path)
        if not path.is_file():
            raise FileManagerError(f"File not found: '{relative_path}'")
        try:
            path.unlink()
        except Exception as e:
            raise FileManagerError(f"Failed to delete '{relative_path}': {e}")

    # ------------------------------------------------------------------
    # Workspace operations
    # ------------------------------------------------------------------

    def clear_workspace(self) -> None:
        """Remove all files and directories from the workspace."""
        for item in self._root.iterdir():
            if item.name == ".gitkeep":
                continue
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            except Exception as e:
                raise FileManagerError(f"Failed to clear workspace: {e}")

    def get_workspace_root(self) -> str:
        """Return the absolute path of the workspace root."""
        return str(self._root)

    def is_empty(self) -> bool:
        """Check if workspace has no project files."""
        return len(self.list_files()) == 0

    def get_file_summary(self, relative_path: str, max_lines: int = 10) -> str:
        """
        Get first N lines of a file for preview/summary.

        Args:
            relative_path: Path relative to workspace root.
            max_lines: Maximum number of lines to return.

        Returns:
            First N lines of the file.
        """
        content = self.read_file(relative_path)
        lines = content.split("\n")[:max_lines]
        return "\n".join(lines)

    def __repr__(self) -> str:
        file_count = len(self.list_files())
        return f"FileManager(root='{self._root}', files={file_count})"
