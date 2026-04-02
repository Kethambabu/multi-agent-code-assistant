# Components Index

Complete reference guide for all project components and their relationships.

## Quick Navigation

### 🎯 Start Here
- [README.md](README.md) - Main documentation and setup
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and data flow
- [CREW_GUIDE.md](CREW_GUIDE.md) - Integration examples and patterns
- [TOOLS_LAYER.md](TOOLS_LAYER.md) - Code analysis tools documentation

### 📦 Core Modules
- [Configuration](#configuration-layer)
- [API Client](#api-client-layer)
- [LLM Abstraction](#llm-abstraction-layer)
- [Agents](#agent-layer)
- [Orchestration](#orchestration-layer)
- [Tools](#tools-analysis-layer)

---

## Configuration Layer

### `config.py`
Manages application configuration from environment variables.

**Key Classes:**
- `Config` - Central configuration with validation
- `get_config()` - Validate and return config

**Key Features:**
- Environment-based API key loading
- Model selection (deepseek-coder, starcoder)
- Timeout and retry configuration
- Type-safe with Literal types

**Used by:** `hf_client.py`, `hf_llm.py`

**Example:**
```python
from config import get_config
config = get_config()  # Validates HUGGINGFACE_API_KEY is set
print(f"Using model: {config.MODEL}")
```

---

## API Client Layer

### `hf_client.py`
Low-level HTTP client for Hugging Face Inference API.

**Key Functions:**
- `call_hf_api(prompt, max_tokens, temperature)` - Make API call

**Features:**
- Single responsibility: API communication only
- Error handling for 401, 429, 503 responses
- Timeout handling with informative messages
- Response parsing (handles multiple HF response formats)

**Used by:** `hf_llm.py`

**Example:**
```python
from hf_client import call_hf_api
result = call_hf_api("def hello():", max_tokens=50)
```

---

## LLM Abstraction Layer

### `hf_llm.py`
High-level LLM interface with resilience and error handling.

**Key Classes:**
- `HuggingFaceLLM` - Main LLM interface
  - `generate(prompt, **kwargs)` - Generate with retries
  - `_wait_before_retry()` - Exponential backoff
- `LLMError` - Base LLM exception
- `LLMRetryError` - Retry exhaustion exception

**Features:**
- Automatic retry with exponential backoff
- Input validation (reject empty prompts)
- Output validation (reject empty responses)
- Distinguishes retryable vs non-retryable errors
- Type hints and comprehensive docstrings

**Used by:** All agents, tests, orchestrator

**Example:**
```python
from hf_llm import HuggingFaceLLM, LLMRetryError
llm = HuggingFaceLLM(max_retries=3)
try:
    result = llm.generate("def hello():")
except LLMRetryError as e:
    print(f"Failed after retries: {e}")
```

---

## Agent Layer

Abstract base class for all agents.

### `base_agent.py`
Defines agent interface and infrastructure.

**Key Classes:**
- `BaseAgent` - Abstract base class
  - `role` - Agent's role
  - `goal` - Agent's goal
  - `execute(context, **kwargs)` - Execute task (abstract)
  - `_build_prompt(template, **kwargs)` - Helper for prompt construction
- `AgentResult` - Standardized result format
- `AgentRegistry` - Manager for agents

**Features:**
- Dependency injection pattern (LLM passed to `__init__`)
- Standardized result format (success, output, error, metadata)
- Registry for dynamic agent management
- Safe error handling with AgentResult wrapper

**Extended by:** CompletionAgent, DebugAgent, ExplainAgent, TestAgent

**Example:**
```python
from base_agent import BaseAgent, AgentResult, AgentRegistry
from hf_llm import HuggingFaceLLM

registry = AgentRegistry()
registry.register("my_agent", my_agent_instance)
agent = registry.get("my_agent")
```

### `completion_agent.py`
Generates code completions at cursor position.

**Key Class:**
- `CompletionAgent` - Completion specialist

**Methods:**
- `execute(code, line_number, max_tokens, temperature)` - Generate completion
- `_get_scope_info(code, line_number)` - Get context (function/class)
- `_build_completion_prompt(context, scope_info, line_number)` - Build LLM prompt

**Dependencies:**
- context_extractor - Get surrounding code
- ast_parser - Find containing function/class
- hf_llm - Generate completion

**Example:**
```python
from completion_agent import CompletionAgent
from hf_llm import HuggingFaceLLM

llm = HuggingFaceLLM()
agent = CompletionAgent(llm)
result = agent.execute(code="def ", line_number=1, max_tokens=100)
```

### `debug_agent.py`
Detects and suggests fixes for bugs.

**Key Class:**
- `DebugAgent` - Debug specialist

**Methods:**
- `execute(code, line_number)` - Analyze for bugs
- `_analyze_issues(code, issues)` - Format bug analysis
- `_suggest_fix(code, issue)` - Generate fix using LLM
- `_get_severity_breakdown(issues)` - Count by severity

**Dependencies:**
- bug_detector - Find issues
- context_extractor - Get context for fixes
- hf_llm - Generate fixes

**Example:**
```python
from debug_agent import DebugAgent
from hf_llm import HuggingFaceLLM

agent = DebugAgent(HuggingFaceLLM())
result = agent.execute(code="def broken(\n    pass")
# Returns: syntax errors, undefined variables, unused imports
```

### `explain_agent.py`
Provides code explanations.

**Key Class:**
- `ExplainAgent` - Explanation specialist

**Methods:**
- `execute(code, line_number, detail_level)` - Generate explanation
- `_explain_at_line(code, line_number)` - Explain specific scope
- `_explain_structure(code)` - Explain overall structure
- `_generate_explanation(code_context, subject)` - LLM-based explanation

**Dependencies:**
- ast_parser - Extract structure info
- context_extractor - Get relevant context
- hf_llm - Generate explanation

**Example:**
```python
from explain_agent import ExplainAgent
from hf_llm import HuggingFaceLLM

agent = ExplainAgent(HuggingFaceLLM())
result = agent.execute(code="...", line_number=10, detail_level="detailed")
```

### `test_agent.py`
Generates test cases and test code.

**Key Class:**
- `TestAgent` - Test generation specialist

**Methods:**
- `execute(code, line_number, test_framework, coverage)` - Generate tests
- `_generate_function_tests(code, line_number)` - Tests for specific function
- `_generate_suite_tests(code)` - Test suite for all functions
- `_generate_tests_for_function(func_code, func_name)` - LLM test generation
- `_format_tests(test_code, func_name, framework)` - Format output

**Dependencies:**
- ast_parser - Extract function info
- context_extractor - Get function context
- hf_llm - Generate test code

**Example:**
```python
from test_agent import TestAgent
from hf_llm import HuggingFaceLLM

agent = TestAgent(HuggingFaceLLM())
result = agent.execute(code="...", test_framework="pytest", coverage="comprehensive")
```

### `agent_orchestrator.py`
Simple coordinator for all agents.

**Key Classes:**
- `DeveloperAssistant` - Main interface combining all agents

**Methods:**
- `complete_code(code, line_number)` - Dispatch to completion
- `debug_code(code, line_number)` - Dispatch to debug
- `explain_code(code, line_number, detail_level)` - Dispatch to explain
- `generate_tests(code, framework, coverage)` - Dispatch to test
- `run_agent(agent_name, context)` - Run any agent

**Example:**
```python
from agent_orchestrator import DeveloperAssistant

assistant = DeveloperAssistant()
result = assistant.debug_code("def broken():\n    pass")
```

---

## Orchestration Layer

### `tasks.py`
Task definitions independent of agents.

**Key Classes:**
- `TaskType` - Enum of task types (COMPLETION, DEBUG, EXPLAIN, TEST, CUSTOM)
- `TaskDefinition` - Task specification with validation
- `TaskFactory` - Create standard task definitions
- `TaskValidator` - Validate task parameters
- `TaskRegistry` - Manage all available tasks

**Features:**
- Tasks defined separately from agents
- Parameter validation against task definition
- Default parameter enrichment
- Optional pre/post processing hooks
- Support for custom tasks

**Key Methods:**
- `TaskFactory.create_completion_task()` - Create completion task
- `TaskFactory.create_debug_task()` - Create debug task
- `TaskFactory.create_custom_task()` - Create custom task
- `TaskValidator.validate(task_def, params)` - Check required params
- `TaskValidator.enrich_params(task_def, params)` - Merge with defaults

**Example:**
```python
from tasks import TaskFactory, TaskRegistry, TaskValidator
from tasks import TaskType

registry = TaskRegistry()
task_def = registry.get(TaskType.DEBUG)

params = {"code": "..."}
is_valid, error = TaskValidator.validate(task_def, params)
enriched = TaskValidator.enrich_params(task_def, params)
```

### `crew_setup.py`
CrewAI workflow orchestration with dynamic routing.

**Key Classes:**
- `RoutingRule` - Single routing rule
- `RoutingStrategy` - Enum (DIRECT, CONDITIONAL, CUSTOM)
- `TaskRouter` - Route tasks to agents
- `CrewWorkflow` - Main orchestrator
- `WorkflowConfig` - Workflow configuration

**Key Methods - CrewWorkflow:**
- `execute_task(task_type, params)` - Execute by TaskType
- `execute_custom_task(task_id, params)` - Execute by custom ID
- `add_routing_rule(task_type, target_agent, condition)` - Override routing
- `register_custom_agent(name, agent)` - Add custom agent
- `register_custom_task(id, task_def)` - Add custom task
- `get_available_tasks()` - List all tasks
- `get_available_agents()` - List all agents

**Key Methods - TaskRouter:**
- `add_rule(task_type, target_agent, condition)` - Add routing rule
- `set_custom_router(router_fn)` - Set custom routing function
- `route(task_def, params)` - Determine target agent

**Example:**
```python
from crew_setup import CrewWorkflow, RoutingStrategy
from tasks import TaskType

crew = CrewWorkflow(routing_strategy=RoutingStrategy.DIRECT)

# Execute task
result = crew.execute_task(TaskType.DEBUG, {"code": "..."})

# Add routing rule
crew.add_routing_rule(
    TaskType.DEBUG,
    "custom_debug",
    condition=lambda p: len(p["code"]) > 500
)
```

### `crew_examples.py`
Comprehensive usage examples for CrewAI setup.

**Contains:**
- Basic usage example
- Direct routing example
- Conditional routing example
- Custom task example
- Configuration example
- Agent composition example
- Workflow summary example
- Error handling example

**Run with:**
```bash
python crew_examples.py
```

---

## Tools/Analysis Layer

Code analysis tools with no LLM dependency - works offline.

### `ast_parser.py`
Extract structural information from code using Python AST.

**Key Classes:**
- `FunctionInfo` - Function metadata
- `ClassInfo` - Class metadata
- `ImportInfo` - Import metadata
- `ParseError` - Parsing exception

**Key Functions:**
- `get_ast(code)` - Parse code to AST
- `extract_functions(code)` - Get all functions
- `extract_classes(code)` - Get all classes
- `extract_imports(code)` - Get all imports
- `get_function_by_line(code, line)` - Function containing line
- `get_class_by_line(code, line)` - Class containing line

**Dependencies:** ast (Python standard library)

**Example:**
```python
from ast_parser import extract_functions, extract_classes

functions = extract_functions(code)
for func in functions:
    print(f"{func.name}({', '.join(func.args)})")

classes = extract_classes(code)
for cls in classes:
    print(f"class {cls.name}: {cls.methods}")
```

### `bug_detector.py`
Detect code quality issues.

**Key Classes:**
- `BugReport` - Report for detected issue
- `TaskValidator` - Validate tasks

**Key Functions:**
- `detect_syntax_errors(code)` - Find syntax errors
- `detect_undefined_variables(code)` - Find undefined vars
- `detect_unused_imports(code)` - Find unused imports
- `detect_all_issues(code)` - Run all checks

**Dependencies:** ast_parser

**Issue Types:**
- `syntax_error` - Invalid Python
- `undefined_variable` - Used without definition
- `unused_import` - Never referenced

**Example:**
```python
from bug_detector import detect_all_issues

issues = detect_all_issues(code)
for issue in issues:
    print(f"Line {issue.line_number}: {issue.message}")
```

### `context_extractor.py`
Extract code context at specific positions.

**Key Classes:**
- `CodeContext` - Complete context object

**Key Functions:**
- `get_current_context(code, line, context_lines)` - Context at line
- `get_function_context(code, line)` - Complete function
- `get_imports_context(code)` - All imports
- `get_code_before_cursor(code, line)` - Code before line
- `get_code_after_cursor(code, line)` - Code after line
- `get_line_content(code, line)` - Single line content
- `get_context_summary(code, line)` - Human-readable summary

**Dependencies:** ast_parser

**Example:**
```python
from context_extractor import get_current_context

context = get_current_context(code, line_number=42, context_lines=10)
print(context.imports)           # All imports
print(context.parent_scope)      # def/class containing line
print(context.surrounding_code)  # Lines around position
```

---

## Testing & Documentation

### `tools_test.py`
Comprehensive test suite for tools layer.

**Test Groups:**
- AST Parser tests
- Bug Detector tests
- Context Extractor tests

**Run with:**
```bash
python tools_test.py
```

### `TOOLS_LAYER.md`
Complete documentation for tools/analysis layer.

**Covers:**
- Module descriptions
- Function signatures
- Usage examples
- Design principles
- Performance characteristics

### `CREW_GUIDE.md`
Integration guide for CrewAI workflow.

**Covers:**
- Quick start
- Integration patterns (editor, REST API, CLI)
- Custom workflows
- Configuration patterns
- Task routing matrix

### `ARCHITECTURE.md`
Complete system design documentation.

**Covers:**
- System layers and data flow
- Design patterns used
- Separation of concerns
- Extensibility points
- Testing strategy

### `.env.example`
Template for environment variables.

```env
HUGGINGFACE_API_KEY=hf_your_token_here
HF_MODEL=deepseek-coder
```

### `requirements.txt`
Python dependencies.

```
requests>=2.31.0
python-dotenv>=1.0.0
crewai>=0.1.0
```

---

## Dependency Graph

```
applications (editors, APIs, CLIs)
    ↓
crew_setup.py (CrewWorkflow) ←─ tasks.py (TaskRegistry, TaskValidator)
    ↓
    ├─ completion_agent.py
    ├─ debug_agent.py
    ├─ explain_agent.py
    └─ test_agent.py
         ↓
    base_agent.py (BaseAgent)
         ↓
    hf_llm.py (HuggingFaceLLM)
         ↓
    hf_client.py (call_hf_api)
         ↓
    config.py (Config)

agents also use:
    ├─ ast_parser.py
    ├─ bug_detector.py
    └─ context_extractor.py
         ↓
    (no external dependencies - pure Python analysis)
```

---

## File Relationships

| File | Imports From | Imported By | Purpose |
|------|------|------|---------|
| config.py | os | hf_client | Configuration |
| hf_client.py | requests, config | hf_llm | API communication |
| hf_llm.py | requests, hf_client | agents | LLM abstraction |
| base_agent.py | hf_llm | all agents | Agent interface |
| completion_agent.py | base_agent, hf_llm, tools | crew_setup | Code completion |
| debug_agent.py | base_agent, hf_llm, tools | crew_setup | Bug detection |
| explain_agent.py | base_agent, hf_llm, tools | crew_setup | Explanation |
| test_agent.py | base_agent, hf_llm, tools | crew_setup | Test generation |
| tasks.py | - | crew_setup | Task definitions |
| crew_setup.py | base_agent, tasks, all agents | applications | Orchestration |
| ast_parser.py | ast | tools, agents | Code parsing |
| bug_detector.py | ast_parser | agents | Bug detection |
| context_extractor.py | ast_parser | agents | Context extraction |

---

## Quick Reference

### Finding What You Need

**Q: How do I use the system?**  
A: Start with [crew_setup.py](#crew_setup.py) and [CREW_GUIDE.md](#crew_guide.md)

**Q: How does it work internally?**  
A: Read [ARCHITECTURE.md](#architecture.md)

**Q: How do I add a new agent?**  
A: Create class extending [base_agent.py](#base_agent.py), see [ARCHITECTURE.md](#architecture.md) extensibility section

**Q: How do I analyze code without LLM?**  
A: Use [ast_parser.py](#ast_parser.py), [bug_detector.py](#bug_detector.py), [context_extractor.py](#context_extractor.py)

**Q: How do I configure routing?**  
A: See [crew_setup.py](#crew_setup.py) and [CREW_GUIDE.md](#crew_guide.md) routing section

**Q: How do I integrate with my application?**  
A: See [CREW_GUIDE.md](#crew_guide.md) integration examples section

**Q: What are the dependencies?**  
A: See [requirements.txt](#requirements.txt) and dependency graph above
