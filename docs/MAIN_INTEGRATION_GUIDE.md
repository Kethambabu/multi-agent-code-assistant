# Main System Integration Guide

## Overview

`main.py` provides the **single entry point** for the entire multi-agent system with trigger engine. It integrates:

- **HF LLM** - Language model provider
- **Agents** - Specialized task handlers (debug, explain, complete, test)
- **Trigger Engine** - Event-driven routing system
- **Memory Store** - Context and history management
- **Tools** - Code analysis (AST parser, bug detector, context extractor)

## Architecture: Input → Trigger → Agent → LLM → Output

```
Code Input
    ↓
[Trigger Engine] Detects event type
    ↓
[Router] Routes to best agent
    ↓
[Agent] Prepares context
    ↓
[LLM] Generates response
    ↓
[Memory] Stores for history
    ↓
Output
```

## Key Design Principles

### 1. **No Logic Duplication**
- All business logic lives in specialized modules
- `main.py` only orchestrates and coordinates
- Existing modules unchanged and reusable

### 2. **Dependency Injection**
- Components receive dependencies via constructor
- No global state or tight coupling
- Easy to test and replace components

### 3. **Clean Imports**
```python
# Core modules with clear separation
from hf_llm import HuggingFaceLLM
from agent_orchestrator import DeveloperAssistant
from trigger_engine import TriggerEngine
from memory_store import MemoryStore
```

### 4. **Runnable & Structured**
- Works out of the box with proper error handling
- Includes example usage
- Logging for visibility

## Usage

### Basic Initialization

```python
from main import DeveloperAssistantSystem

# Create system with default config
system = DeveloperAssistantSystem()
```

### Process Code Input

```python
from trigger_engine import EventType

code = """
def hello():
    print("world")  # Missing closing quote
"""

# Process through trigger engine
result = system.process_code_input(
    code,
    trigger_type=EventType.CODE_CHANGE,
    line_number=3
)

if result.success:
    print(result.output)
else:
    print(f"Error: {result.error}")
```

### Direct Agent Invocation

```python
# Debug code
debug_result = system.debug_code(code, line_number=3)

# Explain code
explain_result = system.explain_code(code)

# Complete code
completion = system.complete_code(code, line_number=3)

# Generate tests
tests = system.generate_tests(code, framework="pytest")
```

### Code Analysis

```python
analysis = system.analyze_code(code)

print(f"Functions: {analysis['functions']}")
print(f"Classes: {analysis['classes']}")
print(f"Issues: {analysis['issues']}")
print(f"Summary: {analysis['summary']}")
```

### System Introspection

```python
# Get system status
status = system.get_system_status()
print(status['agents'])      # Available agents
print(status['memory'])      # Memory statistics

# Get memory summary
memory = system.get_memory_summary()
print(memory['total_entries'])
print(memory['recent_entries'])
```

## Configuration

### System Config

```python
from main import DeveloperAssistantSystem, SystemConfig

config = SystemConfig(
    llm_max_retries=3,
    llm_retry_delay=1.0,
    memory_max_history=100,
    memory_max_snapshots=10,
    enable_trigger_logging=True,
    enable_async_execution=True
)

system = DeveloperAssistantSystem(config=config)
```

### Environment Setup

```bash
# Set HuggingFace API key
export HUGGINGFACE_API_KEY="your_api_key_here"

# Set model (optional, defaults to deepseek-coder)
export HF_MODEL="deepseek-coder"  # or "starcoder"
```

## Component Details

### `initialize_llm(config)`
- Creates HuggingFaceLLM with retry logic
- Validates configuration
- Returns configured LLM instance

### `initialize_memory(config)`
- Creates MemoryStore for context
- Manages code snapshots
- Tracks conversation history

### `initialize_agents(llm)`
- Creates DeveloperAssistant orchestrator
- Registers all default agents:
  - **completion** - Code completion
  - **debug** - Bug detection and fixing
  - **explain** - Code explanation
  - **test** - Unit test generation

### `initialize_trigger_engine(assistant, config)`
- Sets up event-driven routing
- Defines routing rules:
  - `SYNTAX_ERROR` → debug agent
  - `CODE_CHANGE` → completion agent
  - `MULTIPLE_ERRORS` → debug agent

## DeveloperAssistantSystem API

### Main Processing

| Method | Purpose | Example |
|--------|---------|---------|
| `process_code_input()` | Full pipeline: validate → trigger → route → execute → store | Handles code with event detection |
| `analyze_code()` | Parse and analyze code structure | Get functions, classes, issues |
| `debug_code()` | Find and fix bugs | Direct agent invocation |
| `explain_code()` | Explain code functionality | Direct agent invocation |
| `complete_code()` | Generate code completions | Direct agent invocation |
| `generate_tests()` | Create unit tests | Direct agent invocation |

### Introspection

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_memory_summary()` | Memory statistics | Entries, snapshots, recent items |
| `get_system_status()` | System health | Agents, memory, config, triggers |

## Flow Diagram

```
process_code_input(code, trigger_type, line, metadata)
    ↓
1. memory.snapshot_code()          [Store code snapshot]
    ↓
2. detect_all_issues(code)         [Analyze for issues]
    ↓
3. Event(trigger_type, code, ...)  [Create event object]
    ↓
4. trigger_engine.route_event()    [Route to agent]
    ↓
5. assistant.registry.execute()    [Execute agent with LLM]
    ↓
6. memory.add_entry()              [Store response]
    ↓
7. Return AgentResult              [Success/Error result]
```

## Integration Points

### With VS Code

The system can be integrated into VS Code extension:

```python
# In VS Code extension (JavaScript)
const { spawn } = require('child_process');

// Run Python script
const py = spawn('python', ['main.py']);
py.stdout.on('data', (data) => {
    // Handle output
});
```

### With IDE Features

- **On-type** → `process_code_input(code, EventType.CODE_CHANGE)`
- **On-error** → `process_code_input(code, EventType.SYNTAX_ERROR)`
- **On-save** → `process_code_input(code, EventType.CODE_CHANGE)`
- **On-click** → `debug_code()`, `explain_code()`, etc.

### With CI/CD

```python
# Batch code analysis for pull requests
system = DeveloperAssistantSystem()
for file in changed_files:
    code = read_file(file)
    analysis = system.analyze_code(code)
    report.add(file, analysis)
```

## Error Handling

### Configuration Errors
```python
try:
    system = DeveloperAssistantSystem()
except ValueError as e:
    # Missing HUGGINGFACE_API_KEY
    print(f"Config error: {e}")
```

### Execution Errors
```python
result = system.process_code_input(code)
if not result.success:
    print(f"Error: {result.error}")
    # Graceful fallback
```

### Network/API Errors
Handled by HuggingFaceLLM with:
- Automatic retries (configurable)
- Exponential backoff
- Timeout management

## Performance Considerations

### Memory Management
- `memory_max_history=100` - Keep last 100 entries
- `memory_max_snapshots=10` - Keep last 10 code versions
- Automatic cleanup on size limits

### Async Execution
- `enable_async_execution=True` - Non-blocking operations
- Useful for IDE integration
- Set to `False` for testing/debugging

### LLM Optimization
- Batching requests where possible
- Response caching (in memory)
- Configurable timeouts and retries

## Testing

### Unit Test Example
```python
def test_system_initialization():
    system = DeveloperAssistantSystem()
    status = system.get_system_status()
    
    assert 'agents' in status
    assert 'memory' in status
    assert len(status['agents']) == 4

def test_code_processing():
    system = DeveloperAssistantSystem()
    code = "def hello(): pass"
    
    result = system.process_code_input(code)
    assert isinstance(result, AgentResult)
```

## Troubleshooting

### LLM Not Responding
```
Error: HUGGINGFACE_API_KEY environment variable not set

Solution: export HUGGINGFACE_API_KEY="your_key"
```

### Memory Full
```
Warning: Memory history at max capacity

Solution: Increase memory_max_history in SystemConfig
```

### Trigger Not Routing
```
Check: Enable trigger logging with enable_trigger_logging=True
Then: Review routing rules in initialize_trigger_engine()
```

## Extension Points

### Add Custom Agent
```python
from base_agent import BaseAgent

class CustomAgent(BaseAgent):
    @property
    def role(self): return "Custom"
    @property
    def goal(self): return "Do custom task"
    def execute(self, context, **kwargs):
        # Implementation
        pass

system.assistant.register_agent("custom", CustomAgent(system.llm))
```

### Add Custom Trigger Rule
```python
from trigger_engine import EventType, RoutingResult

def custom_rule(event):
    if "TODO" in event.code:
        return RoutingResult(
            agent_type="debug",
            agent_name="debug",
            priority=2
        )

system.trigger_engine.register_rule(
    condition=lambda e: "TODO" in e.code,
    route=custom_rule
)
```

## Summary

`main.py` provides:

✅ **Single integration point** for entire system
✅ **Clean dependency injection** - no tight coupling
✅ **No logic duplication** - delegates to modules
✅ **Event-driven processing** - via trigger engine
✅ **Production-ready** - with error handling
✅ **Extensible** - easy to add agents/triggers
✅ **Documented** - with examples and guides

**Start here**: Run `python main.py` to see example usage!
