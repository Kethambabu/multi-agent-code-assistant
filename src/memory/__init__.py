"""
Memory Layer — State management and history tracking.

Independent module with zero dependencies on agents, LLM, or tools.
Agents receive a read-only MemoryContext; only the orchestration layer
writes to MemoryStore.

Dependency: None (leaf module).
"""
from src.memory.store import MemoryStore, MemoryEntry, CodeSnapshot
from src.memory.context import MemoryContext

__all__ = [
    "MemoryStore",
    "MemoryEntry",
    "CodeSnapshot",
    "MemoryContext",
]
