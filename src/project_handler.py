"""
Project Handler — Upload and initialize projects in the workspace.

Handles zip upload/extraction and workspace lifecycle management.

Dependency: file_manager (FileManager).
"""
import io
import zipfile
import logging
from typing import Dict, Any, List

from src.file_manager import FileManager, FileManagerError


logger = logging.getLogger(__name__)


class ProjectHandlerError(Exception):
    """Raised when project handling fails."""
    pass


class ProjectHandler:
    """
    Manages project lifecycle in the workspace.

    Supports:
        - Uploading a project from a zip file
        - Initializing an empty workspace
        - Querying project structure
        - Clearing the workspace
    """

    # Skip these during zip extraction
    SKIP_PATTERNS = {
        "__pycache__", ".git", "venv", ".venv",
        "node_modules", ".idea", ".vscode", ".DS_Store",
        "myvenv",
    }

    def __init__(self, file_manager: FileManager) -> None:
        """
        Initialize with injected FileManager.

        Args:
            file_manager: FileManager instance for workspace I/O.
        """
        self.file_manager = file_manager

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def upload_project(self, zip_bytes: bytes) -> Dict[str, Any]:
        """
        Extract a zip archive into the workspace.

        Args:
            zip_bytes: Raw bytes of the zip file.

        Returns:
            Dict with keys: files (list), total_files (int), project_path (str).

        Raises:
            ProjectHandlerError: If zip is invalid or extraction fails.
        """
        # Clear workspace before uploading
        self.file_manager.clear_workspace()

        try:
            zip_buffer = io.BytesIO(zip_bytes)
            with zipfile.ZipFile(zip_buffer, "r") as zf:
                extracted_files: List[str] = []

                for zip_entry in zf.namelist():
                    # Skip directories
                    if zip_entry.endswith("/"):
                        continue

                    # Skip excluded patterns
                    if self._should_skip(zip_entry):
                        logger.debug(f"Skipping: {zip_entry}")
                        continue

                    # Strip top-level directory if all files share one
                    clean_path = self._clean_zip_path(zip_entry, zf.namelist())

                    if not clean_path:
                        continue

                    # Read and write file
                    content = zf.read(zip_entry)
                    try:
                        text_content = content.decode("utf-8")
                    except UnicodeDecodeError:
                        # Skip binary files
                        logger.debug(f"Skipping binary file: {zip_entry}")
                        continue

                    self.file_manager.write_file(clean_path, text_content)
                    extracted_files.append(clean_path)
                    logger.info(f"Extracted: {clean_path}")

                return {
                    "files": sorted(extracted_files),
                    "total_files": len(extracted_files),
                    "project_path": self.file_manager.get_workspace_root(),
                }

        except zipfile.BadZipFile:
            raise ProjectHandlerError("Invalid zip file.")
        except Exception as e:
            raise ProjectHandlerError(f"Failed to extract project: {e}")

    # ------------------------------------------------------------------
    # Workspace lifecycle
    # ------------------------------------------------------------------

    def init_empty_workspace(self) -> None:
        """Clear workspace and prepare for a new project."""
        self.file_manager.clear_workspace()
        logger.info("Workspace initialized (empty).")

    def clear_workspace(self) -> None:
        """Remove all files from workspace."""
        self.file_manager.clear_workspace()
        logger.info("Workspace cleared.")

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_project_info(self) -> Dict[str, Any]:
        """
        Get information about the current project.

        Returns:
            Dict with keys: files, total_files, has_project, project_path.
        """
        files = self.file_manager.list_files()
        return {
            "files": files,
            "total_files": len(files),
            "has_project": len(files) > 0,
            "project_path": self.file_manager.get_workspace_root(),
        }

    def has_project(self) -> bool:
        """Check if workspace contains any project files."""
        return not self.file_manager.is_empty()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _should_skip(self, path: str) -> bool:
        """Check if a zip entry should be skipped."""
        parts = path.replace("\\", "/").split("/")
        for part in parts:
            if part in self.SKIP_PATTERNS:
                return True
            # Skip hidden files/dirs (except .env and similar config)
            if part.startswith(".") and part not in (".env", ".gitignore", ".gitkeep"):
                return True
        return False

    def _clean_zip_path(self, entry: str, all_entries: list) -> str:
        """
        Clean a zip entry path.

        If all entries share a common top-level directory, strip it.
        This handles the common case where zips contain a single root folder.
        """
        entry = entry.replace("\\", "/")

        # Find common prefix among all non-directory entries
        file_entries = [e.replace("\\", "/") for e in all_entries if not e.endswith("/")]
        if not file_entries:
            return entry

        # Check if all entries share a top-level directory
        first_parts = [e.split("/")[0] for e in file_entries if "/" in e]
        if first_parts and all(p == first_parts[0] for p in first_parts):
            common_prefix = first_parts[0] + "/"
            if entry.startswith(common_prefix):
                entry = entry[len(common_prefix):]

        return entry if entry else ""

    def __repr__(self) -> str:
        info = self.get_project_info()
        return f"ProjectHandler(files={info['total_files']}, has_project={info['has_project']})"
