"""
Agents Layer — Business logic for developer assistance.

Each agent:
    - Receives LLM + Tools via dependency injection
    - Has a single responsibility
    - Returns standardized AgentResult

Dependency: llm (LLMProvider), tools, memory.context.
"""
from src.agents.base import BaseAgent, AgentResult, AgentRegistry
from src.agents.completion import CompletionAgent
from src.agents.debug import DebugAgent
from src.agents.explain import ExplainAgent
from src.agents.test import TestAgent
from src.agents.editor import EditorAgent
from src.agents.creator import CreatorAgent

__all__ = [
    "BaseAgent",
    "AgentResult",
    "AgentRegistry",
    "CompletionAgent",
    "DebugAgent",
    "ExplainAgent",
    "TestAgent",
    "EditorAgent",
    "CreatorAgent",
]
