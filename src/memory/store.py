"""
Memory Store — Core state management.

Tracks code changes, agent responses, errors, and conversation context.
Independent from agents — agents receive memory as input.

Dependency: None (leaf module).
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import deque


@dataclass
class MemoryEntry:
    """Single entry in memory."""
    timestamp: datetime
    entry_type: str      # 'code', 'response', 'error', 'context'
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeSnapshot:
    """Snapshot of code at a point in time."""
    code: str
    timestamp: datetime
    version: int
    description: Optional[str] = None


class MemoryStore:
    """
    Lightweight memory management for developer assistance.

    Tracks:
        - Code changes and snapshots
        - Agent responses
        - Conversation context
        - Error/issue history

    Independent from agents — agents receive a read-only MemoryContext.
    """

    def __init__(
        self,
        max_history: int = 100,
        max_snapshots: int = 10,
    ) -> None:
        """
        Initialize memory store.

        Args:
            max_history: Maximum memory entries to keep (FIFO).
            max_snapshots: Maximum code snapshots to keep.
        """
        self.max_history = max_history
        self.max_snapshots = max_snapshots

        self._memory: deque = deque(maxlen=max_history)
        self._code_snapshots: deque = deque(maxlen=max_snapshots)
        self._code_version = 0

        self._current_code: Optional[str] = None
        self._current_line: int = 0
        self._context_metadata: Dict[str, Any] = {}

        self._stats: Dict[str, int] = {
            "total_entries": 0,
            "responses_generated": 0,
            "errors_encountered": 0,
            "code_changes": 0,
        }

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def update_code(
        self,
        code: str,
        line_number: int = 0,
        description: Optional[str] = None,
    ) -> None:
        """Update current code and optionally create a snapshot."""
        if code != self._current_code:
            self._code_version += 1
            self._code_snapshots.append(
                CodeSnapshot(
                    code=self._current_code or code,
                    timestamp=datetime.now(),
                    version=self._code_version - 1,
                    description=description,
                )
            )
            self._stats["code_changes"] += 1

        self._current_code = code
        self._current_line = line_number

    def store_response(
        self,
        agent_name: str,
        response: str,
        task_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store an agent response in memory."""
        meta = {
            "agent": agent_name,
            "task_type": task_type,
            "line": self._current_line,
            **(metadata or {}),
        }
        self._memory.append(
            MemoryEntry(
                timestamp=datetime.now(),
                entry_type="response",
                content=response,
                metadata=meta,
            )
        )
        self._stats["responses_generated"] += 1
        self._stats["total_entries"] += 1

    def store_error(
        self,
        error_message: str,
        agent_name: str,
        error_type: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store an error for reference."""
        meta = {
            "agent": agent_name,
            "error_type": error_type,
            "line": self._current_line,
            **(metadata or {}),
        }
        self._memory.append(
            MemoryEntry(
                timestamp=datetime.now(),
                entry_type="error",
                content=error_message,
                metadata=meta,
            )
        )
        self._stats["errors_encountered"] += 1
        self._stats["total_entries"] += 1

    def store_context(
        self,
        context_data: Dict[str, Any],
        description: Optional[str] = None,
    ) -> None:
        """Store contextual information."""
        self._memory.append(
            MemoryEntry(
                timestamp=datetime.now(),
                entry_type="context",
                content=str(context_data),
                metadata={"description": description, "line": self._current_line},
            )
        )
        self._context_metadata.update(context_data)
        self._stats["total_entries"] += 1

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_context(
        self,
        include_code: bool = True,
        include_history: int = 5,
        include_recent_errors: bool = True,
    ) -> Dict[str, Any]:
        """Get current context for agents."""
        context: Dict[str, Any] = {
            "timestamp": datetime.now(),
            "current_line": self._current_line,
            "metadata": self._context_metadata.copy(),
            "code_version": self._code_version,
        }

        if include_code:
            context["current_code"] = self._current_code

        if include_history > 0:
            history = list(self._memory)[-include_history:]
            context["recent_history"] = [
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "type": entry.entry_type,
                    "content": (
                        entry.content[:100] + "..."
                        if len(entry.content) > 100
                        else entry.content
                    ),
                    "metadata": entry.metadata,
                }
                for entry in history
            ]

        if include_recent_errors:
            errors = [e for e in self._memory if e.entry_type == "error"]
            if errors:
                recent_error = errors[-1]
                context["last_error"] = {
                    "message": recent_error.content,
                    "agent": recent_error.metadata.get("agent"),
                    "timestamp": recent_error.timestamp.isoformat(),
                }

        return context

    def get_recent_responses(
        self,
        agent_name: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get recent responses, optionally filtered by agent."""
        responses = [e for e in self._memory if e.entry_type == "response"]
        if agent_name:
            responses = [r for r in responses if r.metadata.get("agent") == agent_name]

        return [
            {
                "timestamp": entry.timestamp.isoformat(),
                "agent": entry.metadata.get("agent"),
                "task": entry.metadata.get("task_type"),
                "content": entry.content,
            }
            for entry in responses[-limit:]
        ]

    def get_code_history(self) -> List[Dict[str, Any]]:
        """Get code change history."""
        return [
            {
                "version": snap.version,
                "timestamp": snap.timestamp.isoformat(),
                "code_length": len(snap.code),
                "description": snap.description,
            }
            for snap in self._code_snapshots
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            **self._stats,
            "current_memory_size": len(self._memory),
            "current_snapshots": len(self._code_snapshots),
            "timestamp": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Reset operations
    # ------------------------------------------------------------------

    def clear_memory(self) -> None:
        """Clear all memory entries (keep snapshots and current code)."""
        self._memory.clear()
        self._stats = {
            "total_entries": 0,
            "responses_generated": 0,
            "errors_encountered": 0,
            "code_changes": 0,
        }

    def clear_all(self) -> None:
        """Clear everything including code and snapshots."""
        self.clear_memory()
        self._code_snapshots.clear()
        self._current_code = None
        self._current_line = 0
        self._context_metadata.clear()
        self._code_version = 0

    def export_memory(self) -> Dict[str, Any]:
        """Export entire memory state as a dictionary."""
        return {
            "current_code": self._current_code,
            "current_line": self._current_line,
            "code_version": self._code_version,
            "context_metadata": self._context_metadata.copy(),
            "entries": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "type": e.entry_type,
                    "content": e.content,
                    "metadata": e.metadata,
                }
                for e in self._memory
            ],
            "snapshots": [
                {
                    "version": s.version,
                    "timestamp": s.timestamp.isoformat(),
                    "description": s.description,
                    "code_length": len(s.code),
                }
                for s in self._code_snapshots
            ],
            "statistics": self.get_statistics(),
        }

    def __repr__(self) -> str:
        return (
            f"MemoryStore(entries={len(self._memory)}, "
            f"snapshots={len(self._code_snapshots)}, "
            f"version={self._code_version})"
        )
