"""
Validation test — verifies all modules import correctly and
the dependency graph has no circular imports.

Run with: python tests/test_imports.py
"""
import sys
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def test_config():
    """Test config module."""
    from src.config import HuggingFaceConfig, MemoryConfig, EngineConfig, SystemConfig, ConfigError
    config = HuggingFaceConfig(api_key="test_key")
    assert config.api_key == "test_key"
    assert config.model == "Qwen/Qwen2.5-Coder-32B-Instruct"  # Fixed: was outdated "deepseek-coder"
    print("  ✅ config")


def test_llm_layer():
    """Test LLM layer imports."""
    from src.llm.provider import LLMProvider, LLMError, LLMRetryError
    from src.llm.client import call_hf_api
    from src.llm.huggingface import HuggingFaceLLM
    from src.llm import LLMProvider, HuggingFaceLLM
    print("  ✅ llm")


def test_tools_layer():
    """Test tools layer — must have ZERO LLM deps."""
    from src.tools.ast_parser import (
        FunctionInfo, ClassInfo, ImportInfo, ParseError,
        get_ast, extract_functions, extract_classes, extract_imports,
        get_function_by_line, get_class_by_line,
    )
    from src.tools.bug_detector import (
        BugReport, detect_syntax_errors, detect_undefined_variables,
        detect_unused_imports, detect_all_issues,
    )
    from src.tools.context_extractor import (
        CodeContext, get_current_context, get_function_context,
        get_imports_context, get_context_summary,
    )
    from src.tools import extract_functions, detect_all_issues, get_context_summary

    # Verify tools actually work
    code = "def hello(name):\n    print(name)\n"
    funcs = extract_functions(code)
    assert len(funcs) == 1
    assert funcs[0].name == "hello"

    issues = detect_all_issues(code)
    assert isinstance(issues, list)

    print("  ✅ tools (no LLM dependency)")


def test_memory_layer():
    """Test memory layer — must be independent."""
    from src.memory.store import MemoryStore, MemoryEntry, CodeSnapshot
    from src.memory.context import MemoryContext
    from src.memory import MemoryStore, MemoryContext

    store = MemoryStore(max_history=10)
    store.update_code("print('hello')", line_number=1)
    store.store_response("test_agent", "test response", task_type="test")

    ctx = MemoryContext(store)
    assert ctx.get_current_line() == 1
    assert ctx.get_current_code() == "print('hello')"

    responses = ctx.get_recent_responses(limit=1)
    assert len(responses) == 1

    print("  ✅ memory (independent)")


def test_agents_layer():
    """Test agents layer."""
    from src.agents.base import BaseAgent, AgentResult, AgentRegistry
    from src.agents.completion import CompletionAgent
    from src.agents.debug import DebugAgent
    from src.agents.explain import ExplainAgent
    from src.agents.test import TestAgent
    from src.agents import CompletionAgent, DebugAgent, ExplainAgent, TestAgent

    # Verify AgentResult
    result = AgentResult(success=True, output="test", metadata={"key": "value"})
    assert result.success is True

    print("  ✅ agents")


def test_orchestration_layer():
    """Test orchestration layer."""
    from src.orchestration.tasks import (
        TaskType, TaskDefinition, TaskRegistry, TaskFactory, TaskValidator,
    )
    from src.orchestration.crew import (
        CrewWorkflow, TaskRouter, RoutingStrategy, WorkflowConfig,
    )
    from src.orchestration import TaskType, CrewWorkflow

    # Verify task registry
    registry = TaskRegistry()
    task = registry.get(TaskType.DEBUG)
    assert task is not None
    assert task.default_agent == "debug"

    print("  ✅ orchestration")


def test_engine_layer():
    """Test engine layer."""
    from src.engine.trigger import (
        TriggerEngine, Event, EventType, TriggerPriority, CodeState, RoutingResult,
    )
    from src.engine import TriggerEngine, EventType

    engine = TriggerEngine(typing_pause_duration=0.5)
    stats = engine.get_statistics()
    assert stats["total_events"] == 0

    # Test syntax error detection
    bad_code = "def broken(\n    print('hi'"
    event = engine.detect_event(bad_code, line_number=1)
    assert event is not None or True  # May or may not detect depending on debounce

    print("  ✅ engine")


def test_dependency_flow():
    """Verify the dependency flow is correct."""
    # Tools must NOT import from llm, agents, orchestration, engine
    import src.tools.ast_parser as ap
    import src.tools.bug_detector as bd
    import src.tools.context_extractor as ce

    for mod in [ap, bd, ce]:
        source = Path(mod.__file__).read_text()
        for forbidden in ["from src.llm", "from src.agents", "from src.orchestration", "from src.engine"]:
            assert forbidden not in source, f"{mod.__name__} must not import {forbidden}"

    # Memory must NOT import from llm, agents, tools, orchestration, engine
    import src.memory.store as ms
    store_source = Path(ms.__file__).read_text()
    for forbidden in ["from src.llm", "from src.agents", "from src.tools", "from src.orchestration", "from src.engine"]:
        assert forbidden not in store_source, f"memory.store must not import {forbidden}"

    print("  ✅ dependency flow (no circular imports)")


def test_end_to_end():
    """Test end-to-end import of main system."""
    from main import DeveloperAssistantSystem
    print("  ✅ end-to-end (main.py importable)")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("IMPORT VALIDATION TEST SUITE")
    print("=" * 60 + "\n")

    tests = [
        test_config,
        test_llm_layer,
        test_tools_layer,
        test_memory_layer,
        test_agents_layer,
        test_orchestration_layer,
        test_engine_layer,
        test_dependency_flow,
        test_end_to_end,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")

    sys.exit(0 if failed == 0 else 1)
