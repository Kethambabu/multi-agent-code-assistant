"""
File Selector — Intelligent file targeting based on user prompts.

Given a user prompt like "Fix the login bug", determines which file(s)
in the workspace should be modified. Uses a two-tier strategy:
  1. Fast keyword heuristic (no LLM call)
  2. LLM-based selection (accurate, 1 LLM call)

Dependency: file_manager, response_parsers, llm.
"""
import logging
from typing import List, Dict

from src.file_manager import FileManager
from src.utils.response_parsers import parse_file_list_from_response
from src.llm.prompts import build_file_selection_prompt


logger = logging.getLogger(__name__)


class FileSelector:
    """
    Selects which files to modify based on a user prompt.

    Two-tier strategy:
        Tier 1 (fast):  Keyword matching on filenames + file content
        Tier 2 (smart): LLM picks files from a summary list
    """

    # Common keyword → file content associations
    KEYWORD_MAP = {
        "login": ["login", "auth", "user", "session", "jwt", "token"],
        "database": ["db", "database", "model", "sql", "query", "orm"],
        "api": ["api", "route", "endpoint", "rest", "handler", "view"],
        "test": ["test_", "_test", "test", "spec", "fixture"],
        "config": ["config", "settings", "env", "setup"],
        "ui": ["template", "html", "render", "view", "page", "component"],
        "error": ["error", "exception", "handler", "middleware", "logging"],
        "deploy": ["docker", "deploy", "ci", "cd", "build", "makefile"],
    }

    def __init__(self, file_manager: FileManager, llm) -> None:
        """
        Initialize with FileManager and LLM provider.

        Args:
            file_manager: FileManager for workspace access.
            llm: LLM provider for smart file selection.
        """
        self.file_manager = file_manager
        self.llm = llm

    def select_files(self, prompt: str) -> List[str]:
        """
        Select files to modify based on user prompt.

        Strategy:
            1. Run keyword heuristic first (fast, cheap)
            2. If no results or too many (>5), use LLM selection
            3. If workspace has ≤3 files, return all of them

        Args:
            prompt: User's instruction (e.g. "Add login system").

        Returns:
            List of relative file paths to modify.
        """
        all_files = self.file_manager.list_files()

        if not all_files:
            logger.info("No files in workspace — nothing to select.")
            return []

        # Small project: return all files
        if len(all_files) <= 3:
            logger.info(f"Small project ({len(all_files)} files) — selecting all.")
            return all_files

        # Tier 1: Keyword search
        keyword_results = self._keyword_search(prompt, all_files)
        logger.info(f"Keyword search returned {len(keyword_results)} files.")

        if 1 <= len(keyword_results) <= 5:
            return keyword_results

        # Tier 2: LLM-based selection
        llm_results = self._llm_select(prompt, all_files)
        if llm_results:
            logger.info(f"LLM selection returned {len(llm_results)} files.")
            return llm_results

        # Fallback: return keyword results if any, otherwise first Python file
        if keyword_results:
            return keyword_results[:5]

        # Last resort: return main entry points
        for candidate in ["main.py", "app.py", "run.py"]:
            if candidate in all_files:
                return [candidate]

        return all_files[:1]

    # ------------------------------------------------------------------
    # Tier 1: Keyword heuristic
    # ------------------------------------------------------------------

    def _keyword_search(self, prompt: str, files: List[str]) -> List[str]:
        """
        Search files by keyword matching on names + content.

        Args:
            prompt: User's instruction.
            files: List of file paths.

        Returns:
            Matching file paths, ranked by relevance.
        """
        prompt_lower = prompt.lower()
        scores: Dict[str, int] = {}

        # Expand prompt keywords using the keyword map
        search_terms = set(prompt_lower.split())
        for keyword, associations in self.KEYWORD_MAP.items():
            if keyword in prompt_lower:
                search_terms.update(associations)

        for file_path in files:
            score = 0
            file_lower = file_path.lower()

            # Score based on filename match
            for term in search_terms:
                if term in file_lower:
                    score += 3  # Filename match is strong

            # Score based on file content match (if file is readable)
            try:
                content = self.file_manager.read_file(file_path).lower()
                for term in search_terms:
                    if term in content:
                        score += 1  # Content match is weaker
            except Exception:
                pass

            if score > 0:
                scores[file_path] = score

        # Sort by score descending
        ranked = sorted(scores.keys(), key=lambda f: scores[f], reverse=True)
        return ranked

    # ------------------------------------------------------------------
    # Tier 2: LLM-based selection
    # ------------------------------------------------------------------

    def _llm_select(self, prompt: str, files: List[str]) -> List[str]:
        """
        Ask LLM to select which files to modify using template.

        Shows LLM a summary of each file and asks it to pick.

        Args:
            prompt: User's instruction.
            files: List of file paths.

        Returns:
            List of selected file paths.
        """
        # Build file summaries
        summaries: Dict[str, str] = {}
        for file_path in files[:20]:  # Limit to 20 files for context window
            try:
                summary = self.file_manager.get_file_summary(file_path, max_lines=5)
                summaries[file_path] = summary
            except Exception:
                summaries[file_path] = "(could not read file)"

        # Format summaries for the LLM
        file_list = "\n\n".join(
            f"FILE: {path}\n{preview}..."
            for path, preview in summaries.items()
        )

        # Use the prompt template
        llm_prompt = build_file_selection_prompt(file_list, prompt)

        try:
            response = self.llm.generate(llm_prompt, max_tokens=200, temperature=0.1)
            selected = parse_file_list_from_response(response)
            # Filter to only valid files that exist
            return [f for f in selected if f in files] if selected else []
        except Exception as e:
            logger.warning(f"LLM file selection failed: {e}")
            return []

    def __repr__(self) -> str:
        files = self.file_manager.list_files()
        return f"FileSelector(workspace_files={len(files)})"
