# Main.py Quick Reference

## One-Minute Setup

```python
from main import DeveloperAssistantSystem

# Create system (requires HUGGINGFACE_API_KEY env var)
system = DeveloperAssistantSystem()

# Process code
result = system.process_code_input(code)
print(result.output)
```

## Common Tasks

### 1. Process Code with Trigger
```python
from trigger_engine import EventType

result = system.process_code_input(
    code,
    trigger_type=EventType.CODE_CHANGE,
    line_number=10
)
```

### 2. Debug Code
```python
result = system.debug_code(code, line_number=15)
```

### 3. Explain Code
```python
result = system.explain_code(code)
```

### 4. Complete Code
```python
result = system.complete_code(code, line_number=30)
```

### 5. Generate Tests
```python
result = system.generate_tests(code, framework="pytest")
```

### 6. Analyze Code
```python
analysis = system.analyze_code(code)
# Keys: functions, classes, imports, issues, summary
```

## Configuration

```python
from main import SystemConfig, DeveloperAssistantSystem

config = SystemConfig(
    llm_max_retries=3,
    memory_max_history=100,
    enable_trigger_logging=True,
    enable_async_execution=True
)

system = DeveloperAssistantSystem(config=config)
```

## Result Handling

```python
result = system.process_code_input(code)

if result.success:
    print(result.output)           # Agent response
    print(result.metadata)         # Agent metadata
else:
    print(f"Error: {result.error}") # Error message
```

## Trigger Types

```python
from trigger_engine import EventType

EventType.CODE_CHANGE        # Code was modified
EventType.SYNTAX_ERROR       # Syntax errors detected
EventType.TYPING_PAUSE       # User stopped typing
EventType.ERROR_CLEARED      # Errors were fixed
EventType.MULTIPLE_ERRORS    # Many errors detected
```

## System Info

```python
# Status
status = system.get_system_status()
print(status['agents'])      # List of agents

# Memory
memory = system.get_memory_summary()
print(memory['total_entries'])
```

## Error Handling

```python
from main import DeveloperAssistantSystem

try:
    system = DeveloperAssistantSystem()
except ValueError as e:
    print(f"Config error (API key?): {e}")
```

## Run Example

```bash
# Set API key first
export HUGGINGFACE_API_KEY="your_key_here"

# Run with example
python main.py
```

## What Each Agent Does

| Agent | Purpose | Trigger |
|-------|---------|---------|
| **debug** | Find and fix bugs | SYNTAX_ERROR, MULTIPLE_ERRORS |
| **completion** | Code completion | CODE_CHANGE |
| **explain** | Explain code | Manual invocation |
| **test** | Generate tests | Manual invocation |

## Flow

```
process_code_input()
  → Snapshot code
  → Detect issues
  → Create event
  → Route via trigger engine
  → Execute agent
  → Store response
  → Return result
```

## Files to Know

- `main.py` - This file (main entry point)
- `MAIN_INTEGRATION_GUIDE.md` - Full documentation
- `hf_llm.py` - LLM provider
- `agent_orchestrator.py` - Agent management
- `trigger_engine.py` - Event routing
- `memory_store.py` - Context storage

## Full Example

```python
from main import DeveloperAssistantSystem
from trigger_engine import EventType

# Initialize
system = DeveloperAssistantSystem()

# Code to process
code = '''
def calculate(x, y)
    return x + y
'''

# Process (automatically detects syntax error)
result = system.process_code_input(code)

# Or explicitly specify
result = system.process_code_input(
    code,
    trigger_type=EventType.SYNTAX_ERROR,
    line_number=2
)

# Handle result
if result.success:
    print("Agent response:", result.output)
    print("Metadata:", result.metadata)
else:
    print("Failed:", result.error)
```

## Key Methods

```python
system.process_code_input(code, **kwargs)    # Full pipeline
system.analyze_code(code)                    # Code analysis only
system.debug_code(code, line_number)         # Direct debug
system.explain_code(code)                    # Direct explain
system.complete_code(code, line_number)      # Direct complete
system.generate_tests(code, framework)       # Direct test
system.get_memory_summary()                  # Memory info
system.get_system_status()                   # System info
```

---

**Start here!** → `python main.py` to see it in action.
