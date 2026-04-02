"""
Orchestration Layer — CrewAI workflow setup.

Coordinates agents, tasks, and routing.
This is the composition root that wires everything together.

Dependency: agents, llm, memory, tasks.
"""
from src.orchestration.tasks import TaskType, TaskDefinition, TaskRegistry, TaskFactory, TaskValidator
from src.orchestration.crew import CrewWorkflow, TaskRouter, RoutingStrategy, WorkflowConfig

__all__ = [
    "TaskType",
    "TaskDefinition",
    "TaskRegistry",
    "TaskFactory",
    "TaskValidator",
    "CrewWorkflow",
    "TaskRouter",
    "RoutingStrategy",
    "WorkflowConfig",
]
