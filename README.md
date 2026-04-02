# Hugging Face Coding Assistant API Client

A minimal, production-ready client for the Hugging Face Inference API with support for code generation models, plus a reusable tools layer for Python code analysis.

## Project Structure

```
├── [LLM CLIENT LAYER]
├── config.py              # Configuration management
├── hf_client.py           # Low-level HF API client
├── hf_llm.py              # High-level LLM abstraction with retry logic
│
├── [AGENT LAYER]
├── base_agent.py          # Abstract base & registry for all agents
├── completion_agent.py    # Code completion specialist
├── debug_agent.py         # Bug detection & fixing
├── explain_agent.py       # Code explanation
├── test_agent.py          # Test generation
├── agent_orchestrator.py  # Simple agent coordinator
│
├── [CREWAL ORCHESTRATION]
├── tasks.py               # Task definitions & registry (agents-independent)
├── crew_setup.py          # CrewAI workflow with dynamic routing
├── crew_examples.py       # Usage examples
│
├── [TOOLS LAYER - Code Analysis]
├── ast_parser.py          # Extract functions, classes, imports
├── bug_detector.py        # Detect syntax errors, undefined vars
├── context_extractor.py   # Extract code context at cursor position
│
├── tools_test.py          # Tools layer test suite
├── TOOLS_LAYER.md         # Tools layer documentation
├── CREW_GUIDE.md          # CrewAI setup & integration guide
├── requirements.txt       # Dependencies
└── README.md             # This file
```

## Features

- **Clean architecture**: Separated config and API logic
- **Environment-based configuration**: No hardcoded secrets
- **Simple API**: Single `call_hf_api()` function
- **Error handling**: Proper exception handling for API failures
- **Flexible models**: Support for deepseek-coder and starcoder
- **LLM Abstraction**: `HuggingFaceLLM` with automatic retry logic and exponential backoff
- **Code Analysis Tools**: Pure Python AST parsing, bug detection, and context extraction
- **Zero LLM dependency**: Tools layer works completely offline

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Hugging Face API Key

1. Sign up at [huggingface.co](https://huggingface.co)
2. Navigate to Settings → Access Tokens
3. Create a new token with read-only access

### 3. Set Environment Variables

Create a `.env` file in the project root:

```env
HUGGINGFACE_API_KEY=hf_your_token_here
HF_MODEL=deepseek-coder
```

Or set them in your shell:

```bash
export HUGGINGFACE_API_KEY="hf_your_token_here"
export HF_MODEL="deepseek-coder"
```

## Usage

### Using the LLM Abstraction (Recommended)

```python
from hf_llm import HuggingFaceLLM

# Initialize the provider
llm = HuggingFaceLLM(max_retries=3)

# Generate code with automatic retries
prompt = "def fibonacci(n):\n    "
result = llm.generate(prompt, max_tokens=100)
print(result)
```

### With Custom Parameters

```python
llm = HuggingFaceLLM(
    max_retries=3,
    retry_delay=1.0,
    exponential_backoff=True,
)

result = llm.generate(
    prompt="def quicksort(arr):\n    ",
    max_tokens=256,
    temperature=0.5,  # Lower = more deterministic
)
```

### Low-level API (Direct)

```python
from hf_client import call_hf_api

# Single API call without retries
result = call_hf_api(prompt, max_tokens=100)
```

### Running as Script

```bash
python hf_llm.py    # Test the abstraction layer
python hf_client.py # Test the low-level API
```

## Tools Layer (Code Analysis)

Three modular, zero-dependency tools for Python code analysis (no LLM calls).

### 1. AST Parser (`ast_parser.py`)

Extract structural information from code:

```python
from ast_parser import extract_functions, extract_classes, extract_imports

code = open("myfile.py").read()

# Extract functions
functions = extract_functions(code)
for func in functions:
    print(f"{func.name}({', '.join(func.args)}) at line {func.line_start}")

# Extract classes
classes = extract_classes(code)
for cls in classes:
    print(f"class {cls.name}: {', '.join(cls.methods)}")

# Extract imports
imports = extract_imports(code)
for imp in imports:
    print(f"from {imp.module} import {', '.join(imp.names)}")
```

### 2. Bug Detector (`bug_detector.py`)

Identify code quality issues:

```python
from bug_detector import detect_all_issues

code = open("myfile.py").read()

issues = detect_all_issues(code)
for issue in issues:
    print(f"Line {issue.line_number}: [{issue.type}] {issue.message}")

# Detects:
# - Syntax errors
# - Undefined variables
# - Unused imports
```

### 3. Context Extractor (`context_extractor.py`)

Extract code context at specific positions:

```python
from context_extractor import get_current_context, get_function_context

code = open("myfile.py").read()

# Get context around cursor
context = get_current_context(code, cursor_position=42)
print(context.imports)           # All imports
print(context.parent_scope)      # def/class containing cursor
print(context.surrounding_code)  # Code around position

# Get complete function
func_code = get_function_context(code, line_number=42)
```

### Testing Tools Layer

Run comprehensive tests:

```bash
python tools_test.py
```

See [TOOLS_LAYER.md](TOOLS_LAYER.md) for complete documentation.

## CrewAI Orchestration Layer

Multi-agent system with dynamic task routing and clean separation of concerns.

### Quick Start

```python
from crew_setup import create_developer_crew
from tasks import TaskType

# Create crew
crew = create_developer_crew()

# Execute tasks
code = "def hello(): print('hi')"

# Code completion
result = crew.execute_task(TaskType.COMPLETION, {
    "code": code,
    "line_number": 5,
})

# Bug detection
result = crew.execute_task(TaskType.DEBUG, {
    "code": code,
})

# Code explanation
result = crew.execute_task(TaskType.EXPLAIN, {
    "code": code,
    "detail_level": "medium",
})

# Test generation
result = crew.execute_task(TaskType.TEST, {
    "code": code,
    "coverage": "basic",
})
```

### Architecture

```
Tasks (Independent)   Agents (Interchangeable)   Routing (Configurable)
─────────────────     ──────────────────────     ──────────────────────
- Completion Task  →  CompletionAgent         →  Direct Routing
- Debug Task       →  DebugAgent              →  Conditional Routing
- Explain Task     →  ExplainAgent            →  Custom Routing
- Test Task        →  TestAgent
- Custom Tasks     →  Custom Agents
```

### Routing Strategies

```python
from crew_setup import CrewWorkflow, RoutingStrategy

# Direct routing: task type → agent
crew = CrewWorkflow(routing_strategy=RoutingStrategy.DIRECT)

# Conditional routing: based on code characteristics
crew = CrewWorkflow(routing_strategy=RoutingStrategy.CONDITIONAL)
crew.add_routing_rule(
    TaskType.DEBUG,
    "custom_agent",
    condition=lambda params: len(params["code"]) > 500,
)

# Custom routing: custom function
def my_router(task_def, params):
    if "class " in params["code"]:
        return "explain"
    return task_def.default_agent

crew.router.set_custom_router(my_router)
```

### Adding Custom Agents & Tasks

```python
from crew_setup import create_developer_crew
from base_agent import BaseAgent, AgentResult
from tasks import TaskFactory

crew = create_developer_crew()

# Register custom agent
class RefactorAgent(BaseAgent):
    @property
    def role(self):
        return "Code Refactoring Specialist"
    
    @property
    def goal(self):
        return "Refactor code for readability"
    
    def execute(self, context, **kwargs):
        # Implementation
        return AgentResult(success=True, output="refactored code")

crew.register_custom_agent("refactor", RefactorAgent(crew.llm))

# Register custom task
refactor_task = TaskFactory.create_custom_task(
    name="Refactor Code",
    description="Make code more readable",
    required_params=["code"],
    default_params={"style": "pep8"},
    expected_output="Refactored code",
    target_agent="refactor",
)
crew.register_custom_task("refactor", refactor_task)

# Use it
result = crew.execute_custom_task("refactor", {"code": code})
```

See [CREW_GUIDE.md](CREW_GUIDE.md) for integration examples (REST API, CLI, editor plugins).

## Combined Example: Full Analysis Pipeline

```python
from crew_setup import create_developer_crew
from tasks import TaskType

crew = create_developer_crew()
code = open("myfile.py").read()

# Multi-step analysis workflow
debug_result = crew.execute_task(TaskType.DEBUG, {"code": code})

if debug_result.success:
    # If no critical errors, explain and test
    explain_result = crew.execute_task(TaskType.EXPLAIN, {
        "code": code,
        "detail_level": "detailed",
    })
    
    test_result = crew.execute_task(TaskType.TEST, {
        "code": code,
        "coverage": "comprehensive",
    })
    
    print("Analysis Report:")
    print(f"  Issues: {debug_result.output}")
    print(f"  Explanation: {explain_result.output}")
    print(f"  Tests: {test_result.output}")
else:
    print(f"Critical errors found: {debug_result.output}")
```

## Configuration

Edit `config.py` to customize:

- `MODEL`: Choose between `deepseek-coder` or `starcoder`
- `TIMEOUT`: Request timeout in seconds (default: 30)
- `MAX_RETRIES`: Number of retry attempts (default: 3)

## Error Handling

### Using HuggingFaceLLM Abstraction

```python
from hf_llm import HuggingFaceLLM, LLMError, LLMRetryError

llm = HuggingFaceLLM()

try:
    result = llm.generate("def hello():")
except LLMError as e:
    print(f"LLM error: {e}")  # Configuration or validation errors
except LLMRetryError as e:
    print(f"Retry exhausted: {e}")  # Max retries exceeded
```

### Using Low-level API

```python
from hf_client import call_hf_api
import requests

try:
    result = call_hf_api(prompt)
except ValueError as e:
    print(f"Configuration error: {e}")  # Invalid API key or model
except requests.exceptions.RequestException as e:
    print(f"API error: {e}")  # Network or API issues
```

## Architecture

### Layers

```
┌─────────────────────────────────────────────────┐
│  Your Application / Business Logic              │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│  HuggingFaceLLM (Abstraction Layer)             │
│  - Retry logic                                  │
│  - Error handling                               │
│  - Input validation                             │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│  hf_client.py (API Layer)                       │
│  - HTTP requests                                │
│  - Response parsing                             │
│  - Low-level error handling                     │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│  config.py (Configuration)                      │
│  - Environment variables                        │
│  - Settings validation                          │
└─────────────────────────────────────────────────┘
```

### Design Principles

1. **Separation of Concerns**
   - `config.py`: Configuration management only
   - `hf_client.py`: Low-level API communication
   - `hf_llm.py`: High-level abstraction with retry logic

2. **Extensibility**
   - `LLMProvider` protocol enables future implementations (OpenAI, Claude, etc.)
   - Easy to create new implementations without changing existing code

3. **No Business Logic**
   - LLM modules only handle communication and resilience
   - Application logic remains in your code

### Adding New Providers

To add OpenAI support, create a new class:

```python
# openai_llm.py
from hf_llm import LLMProvider

class OpenAILLM:
    """OpenAI LLM provider implementation."""
    
    def generate(self, prompt: str) -> str:
        # OpenAI-specific implementation
        pass

# Usage
llm: LLMProvider = OpenAILLM()  # Duck typing - no parent class needed
result = llm.generate(prompt)
```


## Files

- **config.py**: Configuration management with environment variables
- **hf_client.py**: Low-level API client with `call_hf_api()` function
- **hf_llm.py**: High-level abstraction layer with `HuggingFaceLLM` class (retry logic, error handling)
- **base_agent.py**: Abstract base class and registry for agents
- **completion_agent.py**: Code completion specialist agent
- **debug_agent.py**: Bug detection and fixing agent
- **explain_agent.py**: Code explanation agent
- **test_agent.py**: Test generation agent
- **agent_orchestrator.py**: Simple agent coordinator
- **tasks.py**: Task definitions, validation, and registry (agent-independent)
- **crew_setup.py**: CrewAI workflow orchestration with dynamic routing
- **crew_examples.py**: Usage examples for CrewAI setup
- **ast_parser.py**: Extract functions, classes, imports
- **bug_detector.py**: Detect syntax errors, undefined variables
- **context_extractor.py**: Extract code context at cursor position
- **tools_test.py**: Tools layer test suite
- **TOOLS_LAYER.md**: Tools layer documentation
- **CREW_GUIDE.md**: CrewAI integration guide
- **requirements.txt**: Python dependencies
- **.env.example**: Environment variable template
- **.gitignore**: Git configuration for security

## Production Considerations

### Retry Configuration

`HuggingFaceLLM` automatically handles:
- **Timeout errors**: Connection timeout
- **Rate limits (429)**: Too many requests
- **Service unavailable (503)**: Temporary service issues
- **Connection errors**: Network issues

Non-retryable errors:
- **Invalid API key (401)**: Configuration issue
- **Not found (404)**: Invalid model
- **Empty responses**: Validation issue

### Production Setup

- Use a secrets manager for API keys in production
- Monitor retry rates for early detection of issues
- Add request logging for debugging
- Consider caching responses for duplicate prompts
- Adjust `max_retries` and `retry_delay` based on your load
- Use exponential backoff to reduce API load during issues

## License

MIT
