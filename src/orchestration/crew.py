"""
CrewAI workflow orchestrator.

Coordinates agents, tasks, routing, and memory into a unified workflow.
This is the composition root that wires all dependencies together.

Dependency: agents, llm, memory, orchestration.tasks.
"""
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from src.config import HuggingFaceConfig
from src.llm.huggingface import HuggingFaceLLM
from src.agents.base import AgentResult, AgentRegistry
from src.agents.completion import CompletionAgent
from src.agents.debug import DebugAgent
from src.agents.explain import ExplainAgent
from src.agents.test import TestAgent
from src.memory.store import MemoryStore
from src.memory.context import MemoryContext
from src.orchestration.tasks import (
    TaskType,
    TaskDefinition,
    TaskRegistry,
    TaskValidator,
)


@dataclass
class RoutingRule:
    """Rule for routing tasks to agents."""
    task_type: TaskType
    target_agent: str
    condition: Optional[Callable] = None


class RoutingStrategy(Enum):
    """Task routing strategies."""
    DIRECT = "direct"
    CONDITIONAL = "conditional"
    CUSTOM = "custom"


class TaskRouter:
    """Dynamic router for mapping tasks to agents."""

    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.DIRECT) -> None:
        self.strategy = strategy
        self._rules: Dict[TaskType, RoutingRule] = {}
        self._custom_router: Optional[Callable] = None
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        for task_type, agent in [
            (TaskType.COMPLETION, "completion"),
            (TaskType.DEBUG, "debug"),
            (TaskType.EXPLAIN, "explain"),
            (TaskType.TEST, "test"),
        ]:
            self._rules[task_type] = RoutingRule(
                task_type=task_type, target_agent=agent,
            )

    def add_rule(
        self,
        task_type: TaskType,
        target_agent: str,
        condition: Optional[Callable] = None,
    ) -> None:
        self._rules[task_type] = RoutingRule(
            task_type=task_type, target_agent=target_agent, condition=condition,
        )

    def set_custom_router(self, router_fn: Callable) -> None:
        self._custom_router = router_fn

    def route(self, task_def: TaskDefinition, params: Dict[str, Any]) -> str:
        """Route task to appropriate agent name."""
        if self.strategy == RoutingStrategy.CUSTOM and self._custom_router:
            return self._custom_router(task_def, params)

        agent = task_def.default_agent
        if task_def.task_type in self._rules:
            rule = self._rules[task_def.task_type]
            if rule.condition:
                if rule.condition(params):
                    agent = rule.target_agent
            else:
                agent = rule.target_agent
        return agent


class CrewWorkflow:
    """
    Main CrewAI workflow orchestrator.

    Coordinates agents, tasks, routing, and memory into a
    unified pipeline.
    """

    def __init__(
        self,
        llm: HuggingFaceLLM,
        routing_strategy: RoutingStrategy = RoutingStrategy.DIRECT,
        max_memory_entries: int = 100,
    ) -> None:
        """
        Initialize CrewAI workflow.

        Args:
            llm: Injected HuggingFaceLLM instance.
            routing_strategy: Task routing strategy.
            max_memory_entries: Maximum memory entries to keep.
        """
        self.llm = llm
        self.agent_registry = AgentRegistry()
        self.task_registry = TaskRegistry()
        self.router = TaskRouter(strategy=routing_strategy)
        self.memory = MemoryStore(max_history=max_memory_entries)

        self._register_agents()

    def _register_agents(self) -> None:
        """Register all default agents with the shared LLM."""
        self.agent_registry.register("completion", CompletionAgent(self.llm))
        self.agent_registry.register("debug", DebugAgent(self.llm))
        self.agent_registry.register("explain", ExplainAgent(self.llm))
        self.agent_registry.register("test", TestAgent(self.llm))

    def execute_task(
        self,
        task_type: TaskType,
        params: Dict[str, Any],
    ) -> AgentResult:
        """
        Execute a task by type through the full pipeline.

        Pipeline: validate → enrich → route → execute → store
        """
        task_def = self.task_registry.get(task_type)
        if not task_def:
            return AgentResult(success=False, output="", error=f"Unknown task type: {task_type}")

        return self._execute_task_def(task_def, params)

    def execute_custom_task(
        self,
        task_id: str,
        params: Dict[str, Any],
    ) -> AgentResult:
        """Execute a custom task by ID."""
        task_def = self.task_registry.get_custom(task_id)
        if not task_def:
            return AgentResult(success=False, output="", error=f"Unknown task ID: {task_id}")
        return self._execute_task_def(task_def, params)

    def _execute_task_def(
        self,
        task_def: TaskDefinition,
        params: Dict[str, Any],
    ) -> AgentResult:
        """Internal: execute a task definition through the full pipeline."""
        # Validate
        is_valid, error = TaskValidator.validate(task_def, params)
        if not is_valid:
            return AgentResult(success=False, output="", error=error)

        # Update memory
        if "code" in params:
            self.memory.update_code(
                params["code"], line_number=params.get("line_number", 0),
            )

        # Enrich params with defaults + memory context
        enriched = TaskValidator.enrich_params(task_def, params)
        enriched["memory_context"] = MemoryContext(self.memory)

        # Preprocess hook
        if task_def.preprocess:
            enriched = task_def.preprocess(enriched)

        # Route to agent
        agent_name = self.router.route(task_def, enriched)
        agent = self.agent_registry.get(agent_name)
        if not agent:
            error_msg = f"Agent '{agent_name}' not found"
            self.memory.store_error(error_msg, agent_name="router", error_type="agent_not_found")
            return AgentResult(success=False, output="", error=error_msg)

        # Execute
        result = agent.execute("", **enriched)

        # Store result in memory
        if result.success:
            self.memory.store_response(
                agent_name=agent_name,
                response=result.output,
                task_type=task_def.task_type.value,
                metadata=result.metadata,
            )
        else:
            self.memory.store_error(
                error_message=result.error or "Unknown error",
                agent_name=agent_name,
                error_type=task_def.task_type.value,
            )

        # Postprocess hook
        if task_def.postprocess and result.success:
            result.output = task_def.postprocess(result.output)

        return result

    def get_available_tasks(self) -> Dict[str, str]:
        result = {}
        for _, task_def in self.task_registry.list_tasks().items():
            if isinstance(task_def, TaskDefinition):
                result[task_def.name] = task_def.description
        return result

    def get_available_agents(self) -> Dict[str, str]:
        return self.agent_registry.list_agents()

    def __repr__(self) -> str:
        agents = list(self.get_available_agents().keys())
        return f"CrewWorkflow(agents={agents}, strategy={self.router.strategy})"


class WorkflowConfig:
    """Configuration builder for CrewAI workflow."""

    def __init__(
        self,
        hf_config: Optional[HuggingFaceConfig] = None,
        routing_strategy: RoutingStrategy = RoutingStrategy.DIRECT,
    ) -> None:
        self.hf_config = hf_config
        self.routing_strategy = routing_strategy

    def create_workflow(self) -> CrewWorkflow:
        """Create a configured workflow instance."""
        if not self.hf_config:
            raise ValueError("HuggingFaceConfig must be provided.")

        llm = HuggingFaceLLM(self.hf_config)
        return CrewWorkflow(llm=llm, routing_strategy=self.routing_strategy)
