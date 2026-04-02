"""
Task definitions for the orchestration workflow.

Tasks are defined separately from agents for modularity.
Each task represents a specific development assistance workflow.

Dependency: None (pure data definitions).
"""
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Callable
from enum import Enum


class TaskType(Enum):
    """Types of development tasks."""
    COMPLETION = "completion"
    DEBUG = "debug"
    EXPLAIN = "explain"
    TEST = "test"
    CUSTOM = "custom"


@dataclass
class TaskDefinition:
    """
    Definition of a development task.

    Separates task specification from agent implementation,
    enabling flexible routing and composition.
    """
    task_type: TaskType
    name: str
    description: str
    required_params: List[str]
    default_params: Dict[str, Any]
    expected_output: str
    default_agent: str
    preprocess: Optional[Callable] = None
    postprocess: Optional[Callable] = None


class TaskFactory:
    """Factory for creating standardized task definitions."""

    @staticmethod
    def create_completion_task() -> TaskDefinition:
        return TaskDefinition(
            task_type=TaskType.COMPLETION,
            name="Complete Code",
            description="Generate code completion at cursor position",
            required_params=["code", "line_number"],
            default_params={"max_tokens": 150, "temperature": 0.5},
            expected_output="Generated code completion string",
            default_agent="completion",
        )

    @staticmethod
    def create_debug_task() -> TaskDefinition:
        return TaskDefinition(
            task_type=TaskType.DEBUG,
            name="Debug Code",
            description="Detect and analyze bugs in code",
            required_params=["code"],
            default_params={"line_number": None},
            expected_output="Bug analysis with fixes and severity levels",
            default_agent="debug",
        )

    @staticmethod
    def create_explain_task() -> TaskDefinition:
        return TaskDefinition(
            task_type=TaskType.EXPLAIN,
            name="Explain Code",
            description="Provide detailed code explanation",
            required_params=["code"],
            default_params={"line_number": None, "detail_level": "medium"},
            expected_output="Comprehensive code explanation",
            default_agent="explain",
        )

    @staticmethod
    def create_test_task() -> TaskDefinition:
        return TaskDefinition(
            task_type=TaskType.TEST,
            name="Generate Tests",
            description="Generate comprehensive test cases",
            required_params=["code"],
            default_params={
                "line_number": None,
                "test_framework": "pytest",
                "coverage": "basic",
            },
            expected_output="Generated test code with test cases",
            default_agent="test",
        )

    @staticmethod
    def create_custom_task(
        name: str,
        description: str,
        required_params: List[str],
        default_params: Dict[str, Any],
        expected_output: str,
        target_agent: str,
    ) -> TaskDefinition:
        return TaskDefinition(
            task_type=TaskType.CUSTOM,
            name=name,
            description=description,
            required_params=required_params,
            default_params=default_params,
            expected_output=expected_output,
            default_agent=target_agent,
        )


class TaskValidator:
    """Validates tasks against their definitions."""

    @staticmethod
    def validate(
        task_def: TaskDefinition,
        params: Dict[str, Any],
    ) -> tuple:
        """
        Validate task parameters.

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str]).
        """
        missing = [p for p in task_def.required_params if p not in params]
        if missing:
            return False, f"Missing required parameters: {', '.join(missing)}"
        return True, None

    @staticmethod
    def enrich_params(
        task_def: TaskDefinition,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Merge provided params with defaults."""
        enriched = task_def.default_params.copy()
        enriched.update(params)
        return enriched


class TaskRegistry:
    """Registry of all available task definitions."""

    def __init__(self) -> None:
        self._tasks: Dict[TaskType, TaskDefinition] = {}
        self._custom_tasks: Dict[str, TaskDefinition] = {}
        self._register_default_tasks()

    def _register_default_tasks(self) -> None:
        self._tasks[TaskType.COMPLETION] = TaskFactory.create_completion_task()
        self._tasks[TaskType.DEBUG] = TaskFactory.create_debug_task()
        self._tasks[TaskType.EXPLAIN] = TaskFactory.create_explain_task()
        self._tasks[TaskType.TEST] = TaskFactory.create_test_task()

    def register_custom(self, task_id: str, task_def: TaskDefinition) -> None:
        self._custom_tasks[task_id] = task_def

    def get(self, task_type: TaskType) -> Optional[TaskDefinition]:
        return self._tasks.get(task_type)

    def get_custom(self, task_id: str) -> Optional[TaskDefinition]:
        return self._custom_tasks.get(task_id)

    def list_tasks(self) -> Dict[str, TaskDefinition]:
        result: Dict[str, TaskDefinition] = {}
        for task_type, task_def in self._tasks.items():
            result[task_type.value] = task_def
        for task_id, task_def in self._custom_tasks.items():
            result[task_id] = task_def
        return result

    def get_by_agent(self, agent_name: str) -> List[TaskDefinition]:
        tasks = [t for t in self._tasks.values() if t.default_agent == agent_name]
        tasks += [t for t in self._custom_tasks.values() if t.default_agent == agent_name]
        return tasks
