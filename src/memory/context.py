"""
Memory Context — Read-only view for agents.

Provides a safe, read-only interface to MemoryStore so agents
cannot accidentally corrupt state.

Dependency: memory.store.
"""
from typing import Dict, List, Any, Optional

from src.memory.store import MemoryStore


class MemoryContext:
    """
    Read-only context wrapper that agents use to access memory safely.

    Agents receive this instead of the raw MemoryStore to enforce
    the principle of least privilege.
    """

    def __init__(self, memory_store: MemoryStore) -> None:
        self._store = memory_store

    def get_current_context(self) -> Dict[str, Any]:
        """Get current context (read-only)."""
        return self._store.get_context()

    def get_current_code(self) -> Optional[str]:
        """Get current code (read-only)."""
        return self._store._current_code

    def get_current_line(self) -> int:
        """Get current line number."""
        return self._store._current_line

    def get_recent_responses(
        self,
        agent_name: Optional[str] = None,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """Get recent responses."""
        return self._store.get_recent_responses(agent_name=agent_name, limit=limit)

    def get_last_error(self) -> Optional[str]:
        """Get last error message."""
        context = self._store.get_context(include_recent_errors=True)
        if "last_error" in context:
            return context["last_error"]["message"]
        return None

    def get_details(self) -> Dict[str, Any]:
        """Get detailed memory info (errors, metadata, stats)."""
        errors = [
            e.content
            for e in self._store._memory
            if e.entry_type == "error"
        ]
        return {
            "errors": errors,
            "metadata": self._store.get_statistics(),
        }
