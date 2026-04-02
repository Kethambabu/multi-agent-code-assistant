"""
Base agent interface and registry.

All agents inherit from BaseAgent to ensure a consistent interface.
AgentRegistry provides dynamic agent discovery and invocation.

Dependency: llm.provider (LLMProvider protocol only — no concrete class).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass

from src.llm.provider import LLMProvider


@dataclass
class AgentResult:
    """Standard result format for all agent operations."""
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseAgent(ABC):
    """
    Abstract base class for all developer assistant agents.

    Provides:
        - Common interface (role, goal, execute)
        - Dependency injection of LLM provider
        - Prompt-building helper
        - Standardized AgentResult output
    """

    def __init__(self, llm: LLMProvider) -> None:
        """
        Initialize agent with LLM instance.

        Args:
            llm: Any object satisfying the LLMProvider protocol.
        """
        self.llm = llm

    @property
    @abstractmethod
    def role(self) -> str:
        """Agent's role in the system."""
        ...

    @property
    @abstractmethod
    def goal(self) -> str:
        """Agent's primary goal."""
        ...

    @abstractmethod
    def execute(self, context: str, **kwargs) -> AgentResult:
        """
        Execute agent's task.

        Args:
            context: Code context or task description.
            **kwargs: Task-specific arguments.

        Returns:
            AgentResult with output and metadata.
        """
        ...

    def _build_prompt(self, template: str, **kwargs) -> str:
        """Build LLM prompt with template substitution."""
        return template.format(**kwargs)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(role='{self.role}')"


class AgentRegistry:
    """
    Registry for managing multiple agents.

    Enables easy addition, removal, and discovery of agents.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, name: str, agent: BaseAgent) -> None:
        """Register an agent."""
        self._agents[name] = agent

    def unregister(self, name: str) -> bool:
        """Unregister an agent. Returns True if removed."""
        if name in self._agents:
            del self._agents[name]
            return True
        return False

    def get(self, name: str) -> Optional[BaseAgent]:
        """Get agent by name."""
        return self._agents.get(name)

    def list_agents(self) -> Dict[str, str]:
        """List all registered agents with their roles."""
        return {name: agent.role for name, agent in self._agents.items()}

    def execute(self, agent_name: str, context: str, **kwargs) -> AgentResult:
        """Execute a specific agent by name."""
        agent = self.get(agent_name)
        if not agent:
            return AgentResult(
                success=False,
                output="",
                error=f"Agent '{agent_name}' not found.",
            )
        try:
            return agent.execute(context, **kwargs)
        except Exception as e:
            return AgentResult(success=False, output="", error=str(e))

    def __repr__(self) -> str:
        return f"AgentRegistry({', '.join(self._agents.keys())})"
