"""
Main entry point for the Multi-Agent Developer Assistant System.

Responsibilities:
    1. Load and validate configuration
    2. Initialize all modules via dependency injection
    3. Wire dependencies together
    4. Run the full pipeline

Architecture:
    Config → LLM → Agents → Memory → Orchestration → Engine

Usage:
    python main.py
"""
import sys
import logging
from typing import Optional, Dict, Any

from src.config import load_config, ConfigError, SystemConfig
from src.llm.huggingface import HuggingFaceLLM
from src.agents.base import AgentResult, AgentRegistry
from src.agents.completion import CompletionAgent
from src.agents.debug import DebugAgent
from src.agents.explain import ExplainAgent
from src.agents.test import TestAgent
from src.memory.store import MemoryStore
from src.memory.context import MemoryContext
from src.engine.trigger import TriggerEngine, EventType
from src.tools import extract_functions, extract_classes, extract_imports, detect_all_issues
from src.tools.context_extractor import get_context_summary


logger = logging.getLogger(__name__)


class DeveloperAssistantSystem:
    """
    Main coordinator for the developer assistant system.

    Responsibilities:
        - Initialize all subsystems via dependency injection
        - Process user code input through the pipeline
        - Route events to appropriate agents
        - Store context and history

    Design:
        - No business logic (delegates to specialized modules)
        - All dependencies injected via constructor
        - Clean separation of concerns
    """

    def __init__(self, config: Optional[SystemConfig] = None) -> None:
        """
        Initialize the complete system.

        Args:
            config: System configuration. If None, loads from environment.
        """
        if config is None:
            config = load_config()

        self.config = config

        logger.info("Initializing Developer Assistant System...")

        # 1. LLM Layer
        self.llm = HuggingFaceLLM(config.hf)
        logger.info(f"✓ LLM initialized ({config.hf.model})")

        # 2. Memory Layer
        self.memory = MemoryStore(
            max_history=config.memory.max_history,
            max_snapshots=config.memory.max_snapshots,
        )
        logger.info("✓ Memory store initialized")

        # 3. Agents Layer
        self.registry = AgentRegistry()
        self.registry.register("completion", CompletionAgent(self.llm))
        self.registry.register("debug", DebugAgent(self.llm))
        self.registry.register("explain", ExplainAgent(self.llm))
        self.registry.register("test", TestAgent(self.llm))
        logger.info(f"✓ Agents initialized ({len(self.registry.list_agents())} agents)")

        # 4. Engine Layer
        self.trigger_engine = TriggerEngine(
            typing_pause_duration=config.engine.typing_pause_duration,
            max_events_in_queue=config.engine.max_events_in_queue,
            syntax_check_debounce=config.engine.syntax_check_debounce,
        )
        logger.info("✓ Trigger engine initialized")

        logger.info("✓ System fully initialized\n")

    # ------------------------------------------------------------------
    # High-level API
    # ------------------------------------------------------------------

    def analyze_code(self, code: str) -> Dict[str, Any]:
        """Analyze code for structure and issues (no LLM call)."""
        try:
            return {
                "functions": extract_functions(code),
                "classes": extract_classes(code),
                "imports": extract_imports(code),
                "issues": detect_all_issues(code),
                "summary": get_context_summary(code, 1),
            }
        except Exception as e:
            logger.error(f"Code analysis failed: {e}")
            return {"error": str(e)}

    def process_code_input(
        self,
        code: str,
        line_number: int = 0,
    ) -> AgentResult:
        """
        Process code through the trigger → route → agent pipeline.

        1. Store code snapshot in memory
        2. Detect events via trigger engine
        3. Route to appropriate agent
        4. Execute agent
        5. Store result in memory
        """
        self.memory.update_code(code, line_number=line_number)

        event = self.trigger_engine.detect_event(code, line_number=line_number)

        if event:
            routing = self.trigger_engine.route_to_agent(event)
            logger.info(f"🔀 Routed to: {routing.agent_name} ({routing.reason})")

            if routing.should_execute:
                result = self.registry.execute(
                    routing.agent_name,
                    code,
                    line_number=line_number,
                    memory_context=MemoryContext(self.memory),
                )
                if result.success:
                    self.memory.store_response(
                        agent_name=routing.agent_name,
                        response=result.output,
                        task_type=routing.agent_type,
                    )
                return result

        return AgentResult(success=True, output="No actionable event detected.", metadata={})

    def debug_code(self, code: str, line_number: Optional[int] = None) -> AgentResult:
        """Debug code issues."""
        return self.registry.execute(
            "debug", code, line_number=line_number,
            memory_context=MemoryContext(self.memory),
        )

    def explain_code(self, code: str, line_number: Optional[int] = None) -> AgentResult:
        """Explain code functionality."""
        return self.registry.execute(
            "explain", code, line_number=line_number,
            memory_context=MemoryContext(self.memory),
        )

    def complete_code(self, code: str, line_number: int = 1) -> AgentResult:
        """Generate code completion."""
        return self.registry.execute(
            "completion", code, line_number=line_number,
            memory_context=MemoryContext(self.memory),
        )

    def generate_tests(self, code: str, framework: str = "pytest") -> AgentResult:
        """Generate tests for code."""
        return self.registry.execute(
            "test", code, test_framework=framework,
            memory_context=MemoryContext(self.memory),
        )

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status and configuration."""
        return {
            "agents": self.registry.list_agents(),
            "memory": self.memory.get_statistics(),
            "engine": self.trigger_engine.get_statistics(),
            "model": self.config.hf.model,
        }


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Run the developer assistant system with example code."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        system = DeveloperAssistantSystem()
    except ConfigError as e:
        logger.error(f"❌ Configuration error: {e}")
        sys.exit(1)

    # Example code
    example_code = '''\
def calculate_factorial(n: int) -> int:
    """Calculate factorial of n."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0 or n == 1:
        return 1
    return n * calculate_factorial(n - 1)

def process_data(data: list) -> dict:
    """Process data and return results."""
    if not data:
        return {}
    total = sum(data)
    return {
        "sum": total,
        "count": len(data),
        "average": total / len(data) if data else 0,
    }

class DataProcessor:
    """Process and analyze data."""

    def __init__(self, data):
        self.data = data

    def analyze(self):
        return {"items": len(self.data)}
'''

    print("\n" + "=" * 70)
    print("EXAMPLE 1: Code Analysis (no LLM)")
    print("=" * 70)
    analysis = system.analyze_code(example_code)
    print(f"Functions: {len(analysis.get('functions', []))}")
    print(f"Classes:   {len(analysis.get('classes', []))}")
    print(f"Issues:    {len(analysis.get('issues', []))}")

    print("\n" + "=" * 70)
    print("EXAMPLE 2: Debug Code")
    print("=" * 70)
    result = system.debug_code(example_code)
    print(f"Success: {result.success}")
    print(f"Output:  {result.output[:200]}")

    print("\n" + "=" * 70)
    print("EXAMPLE 3: System Status")
    print("=" * 70)
    status = system.get_system_status()
    print(f"Agents: {list(status['agents'].keys())}")
    print(f"Model:  {status['model']}")

    print("\n" + "=" * 70)
    print("✓ System demonstration complete")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠ Interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ System error: {e}")
        raise
