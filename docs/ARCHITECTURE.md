"""
ARCHITECTURE.md - Complete system architecture and design patterns.
Explains how all components work together.
"""

# =============================================================================
# SYSTEM LAYERS
# =============================================================================

"""
┌──────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                                 │
│  (Your code: editors, APIs, CLIs, custom workflows)                     │
└──────────────────────────────────────────────────────────────────────────┘
                                   │
   ┌───────────────────────────────┼───────────────────────────────┐
   ▼                               ▼                               ▼
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│ Orchestration    │        │ Agent            │        │ Tools            │
│ Layer            │        │ Orchestrator     │        │ Utilities        │
│ (CrewAI)         │        │ (Simple)         │        │ (Analysis)       │
└──────────────────┘        └──────────────────┘        └──────────────────┘
   │                           │                           │
   ├─ crew_setup.py           ├─ agent_orchestrator.py    ├─ ast_parser.py
   ├─ tasks.py                │                           ├─ bug_detector.py
   └─ CREW_GUIDE.md           │                           └─ context_extractor.py
                              │
┌────────────────────────────────────────────────────────────────────────────┐
│                           AGENT LAYER                                      │
│  (Specialized modules for different development tasks)                    │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐       │
│  │ Completion       │  │ Debug            │  │ Explain          │       │
│  │ Agent            │  │ Agent            │  │ Agent            │       │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤       │
│  │ Role: Completion │  │ Role: Debugger   │  │ Role: Analyzer   │       │
│  │ Goal: Generate   │  │ Goal: Fix bugs   │  │ Goal: Explain    │       │
│  │       code       │  │       & issues   │  │       code       │       │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘       │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Test Agent                                                       │   │
│  ├──────────────────────────────────────────────────────────────────┤   │
│  │ Role: Test Generator                                             │   │
│  │ Goal: Generate comprehensive test cases                          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  base_agent.py: Abstract base class for all agents                        │
│  (Defines interface, dependency injection, standard result format)        │
└────────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
┌───────────────────────────────┐  ┌──────────────────────────────────┐
│      LLM ABSTRACTION LAYER    │  │   TOOLS/ANALYSIS LAYER           │
│      (hf_llm.py)              │  │   (Pure Python, no LLM calls)   │
├───────────────────────────────┤  ├──────────────────────────────────┤
│                               │  │                                  │
│ HuggingFaceLLM                │  │ AST Parser                       │
│ - Retry logic                 │  │ - extract_functions()           │
│ - Error handling              │  │ - extract_classes()             │
│ - Exponential backoff         │  │ - extract_imports()             │
│ - Input validation            │  │                                  │
│                               │  │ Bug Detector                     │
└───────────────────────────────┘  │ - detect_syntax_errors()        │
                    │               │ - detect_undefined_variables()  │
                    │               │ - detect_unused_imports()       │
                    │               │                                  │
                    │               │ Context Extractor               │
                    │               │ - get_current_context()         │
                    │               │ - get_function_context()        │
                    │               │ - get_imports_context()         │
                    │               │                                  │
                    │               └──────────────────────────────────┘
                    │
┌───────────────────┴───────────────────┐
│   API CLIENT LAYER                    │
│   (hf_client.py)                      │
├───────────────────────────────────────┤
│                                       │
│ call_hf_api(prompt)                   │
│ - HTTP requests to HF API             │
│ - Response parsing                    │
│ - Low-level error handling            │
│                                       │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│   CONFIGURATION LAYER                 │
│   (config.py)                         │
├───────────────────────────────────────┤
│                                       │
│ Config class                          │
│ - Environment variables               │
│ - API key management                  │
│ - Model selection                     │
│ - Request settings                    │
│                                       │
└───────────────────┬───────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Hugging Face API     │
         │ (External Service)   │
         └──────────────────────┘
"""

# =============================================================================
# DATA FLOW EXAMPLES
# =============================================================================

"""
EXAMPLE 1: CODE COMPLETION REQUEST
===================================

User Request:
  "Complete this code at line 5"
       ↓
Editor Plugin (or API)
       ↓
crew.execute_task(TaskType.COMPLETION, {
    "code": code_string,
    "line_number": 5,
})
       ↓
CrewWorkflow
  │
  ├─ TaskRegistry.get(COMPLETION) → TaskDefinition
  │
  ├─ TaskValidator.validate(definition, params) → OK
  │
  ├─ TaskValidator.enrich_params(definition, params)
  │  # Merges defaults: max_tokens=150, temperature=0.5
  │
  ├─ TaskRouter.route(task_def, params) → "completion"
  │
  ├─ AgentRegistry.get("completion") → CompletionAgent
  │
  ├─ CompletionAgent.execute(code="...", line_number=5, ...)
  │   │
  │   ├─ get_current_context(code, 5) → CodeContext
  │   │   (Uses context_extractor to understand surrounding code)
  │   │
  │   ├─ _get_scope_info(code, 5) → "in function 'my_func'"
  │   │   (Uses ast_parser to find containing function)
  │   │
  │   ├─ _build_completion_prompt(...) → formatted prompt
  │   │
  │   ├─ self.llm.generate(prompt, max_tokens=150, temperature=0.5)
  │   │   │
  │   │   ├─ HuggingFaceLLM.generate()
  │   │   │   │
  │   │   │   ├─ Validate input not empty
  │   │   │   │
  │   │   │   ├─ Attempt API call (retry up to 3 times)
  │   │   │   │   │
  │   │   │   │   ├─ call_hf_api(prompt, ...) 
  │   │   │   │   │   │
  │   │   │   │   │   ├─ Get config (API key, model)
  │   │   │   │   │   │
  │   │   │   │   │   ├─ Build request to HF API
  │   │   │   │   │   │
  │   │   │   │   │   ├─ requests.post() → HTTP call
  │   │   │   │   │   │
  │   │   │   │   │   ├─ Parse JSON response
  │   │   │   │   │   │
  │   │   │   │   │   └─ Return generated_text
  │   │   │   │   │
  │   │   │   │   └─ Retry on timeout/rate-limit with backoff
  │   │   │   │
  │   │   │   └─ Return text or raise LLMRetryError
  │   │   │
  │   │   └─ Return AgentResult(success=True, output="completion")
  │   │
  │   └─ Return AgentResult
  │
  └─ Return AgentResult to user

Output: "    return greet(name) + '!'"


EXAMPLE 2: BUG DETECTION & ANALYSIS
===================================

User Request:
  "Find bugs in this code"
       ↓
crew.execute_task(TaskType.DEBUG, {"code": code_string})
       ↓
CrewWorkflow
  │
  ├─ TaskRegistry.get(DEBUG) → TaskDefinition
  ├─ Validate & enrich params
  ├─ TaskRouter.route(task_def, params) → "debug"
  ├─ AgentRegistry.get("debug") → DebugAgent
  │
  ├─ DebugAgent.execute(code="...")
  │   │
  │   ├─ bug_detector.detect_all_issues(code)
  │   │   │
  │   │   ├─ detect_syntax_errors(code) → [SyntaxError]
  │   │   │   (Uses ast_parser to check syntax)
  │   │   │
  │   │   ├─ detect_undefined_variables(code) → [UndefinedVar]
  │   │   │   (Uses ast_parser to analyze scopes)
  │   │   │
  │   │   ├─ detect_unused_imports(code) → [UnusedImport]
  │   │   │   (Uses ast_parser to find imports and usage)
  │   │   │
  │   │   └─ Combine all issues sorted by line number
  │   │
  │   ├─ For each issue:
  │   │   ├─ Format for display
  │   │   ├─ For high-severity issues:
  │   │   │   ├─ get_current_context(code, issue.line) → context
  │   │   │   ├─ Build fix prompt
  │   │   │   └─ llm.generate(fix_prompt) → suggested fix
  │   │   │
  │   │   └─ Add to analysis output
  │   │
  │   └─ Return AgentResult with formatted analysis
  │
  └─ Return AgentResult with all issues and fixes


EXAMPLE 3: CUSTOM ROUTING
==========================

User Request:
  Complete code that's > 500 chars using special handling
       ↓
crew.add_routing_rule(
    TaskType.COMPLETION,
    "advanced_completion",
    condition=lambda p: len(p["code"]) > 500
)
       ↓
crew.execute_task(TaskType.COMPLETION, {"code": large_code})
       ↓
CrewWorkflow
  │
  ├─ TaskRouter.route(task_def, params)
  │   │
  │   ├─ Check routing rule for COMPLETION
  │   ├─ Rule has condition function
  │   ├─ Call condition(params) → len(large_code) > 500 → True
  │   └─ Return "advanced_completion" instead of default "completion"
  │
  ├─ AgentRegistry.get("advanced_completion") → CustomAgent
  │
  └─ Execute custom agent instead of default
"""

# =============================================================================
# DESIGN PATTERNS USED
# =============================================================================

"""
1. DEPENDENCY INJECTION
   - All agents receive HuggingFaceLLM via __init__()
   - Agents don't create their own LLM instances
   - Enables easy testing and swapping implementations
   
   Example:
   ```python
   llm = HuggingFaceLLM(max_retries=5)
   agent = CompletionAgent(llm)  # Inject dependency
   ```

2. ABSTRACT BASE CLASS
   - BaseAgent defines interface all agents must implement
   - Enforces consistency across all agents
   - Enables polymorphic use (any agent can be called same way)
   
   Example:
   ```python
   def execute_any_agent(agent: BaseAgent, context: str):
       return agent.execute(context)
   ```

3. REGISTRY PATTERN
   - AgentRegistry, TaskRegistry manage collections
   - Enables dynamic addition/removal of components
   - Decouples client code from specific components
   
   Example:
   ```python
   crew.register_custom_agent("my_agent", my_agent)
   agent = crew.agent_registry.get("my_agent")
   ```

4. STRATEGY PATTERN
   - RoutingStrategy enum enables swappable routing logic
   - TaskRouter supports different routing algorithms
   - Easy to add new routing strategies
   
   Example:
   ```python
   router = TaskRouter(strategy=RoutingStrategy.CONDITIONAL)
   agent = router.route(task_def, params)
   ```

5. FACTORY PATTERN
   - TaskFactory creates standardized task definitions
   - Ensures consistency and reduces boilerplate
   - Easy to create variations
   
   Example:
   ```python
   completion_task = TaskFactory.create_completion_task()
   custom_task = TaskFactory.create_custom_task(...)
   ```

6. DECORATOR PATTERN (Implicit)
   - LLM provides retry/error handling around API calls
   - Separates resilience logic from business logic
   - Makes code cleaner and more testable

7. ADAPTER PATTERN
   - Each agent adapts its specific implementation to BaseAgent interface
   - Allows agents with different internal logic to be used interchangeably
   - Makes it easy to add new agent types

8. CONFIGURATION AS DATA
   - TaskDefinition stores all configuration
   - Separates configuration from logic
   - Easy to modify routing/behavior without code changes
"""

# =============================================================================
# SEPARATION OF CONCERNS
# =============================================================================

"""
CONFIG LAYER (config.py)
├─ Responsibility: Load and validate configuration
├─ Dependencies: os (environment)
└─ Used by: hf_client, hf_llm

API CLIENT LAYER (hf_client.py)  
├─ Responsibility: HTTP communication with HF API
├─ Dependencies: requests, config
└─ Used by: hf_llm

LLM ABSTRACTION (hf_llm.py)
├─ Responsibility: Resilience (retry, backoff) + validation
├─ Dependencies: hf_client, requests
└─ Used by: All agents

TOOLS/ANALYSIS LAYER
├─ ast_parser.py:        Parse code structure
├─ bug_detector.py:      Find code issues
├─ context_extractor.py: Extract context around position
├─ Dependencies: ast (standard library), no LLM calls
└─ Used by: All agents

AGENT LAYER (completion_agent.py, debug_agent.py, etc.)
├─ Responsibility: Implement specific development task
├─ Dependencies: base_agent, hf_llm, tools
└─ Used by: Orchestrator

ORCHESTRATION LAYER
├─ base_agent.py:          Abstract interface + registry
├─ tasks.py:               Task definitions + validation
├─ crew_setup.py:          Workflow + routing + execution
├─ agent_orchestrator.py:  Simple coordinator
├─ Dependencies: agents, hf_llm, tasks
└─ Used by: Applications

APPLICATION LAYER
├─ Your code: editors, APIs, CLIs
├─ Dependencies: Orchestrator/Agents
└─ Responsibility: Coordinate high-level workflows
"""

# =============================================================================
# EXTENSIBILITY POINTS
# =============================================================================

"""
1. ADD A NEW AGENT
   ├─ Create class inheriting from BaseAgent
   ├─ Implement role, goal, execute()
   ├─ Register with crew.register_custom_agent()
   └─ Create TaskDefinition targeting new agent

2. ADD A NEW TASK TYPE
   ├─ Create TaskDefinition using TaskFactory
   ├─ Register with crew.register_custom_task()
   ├─ Add routing rule linking task to agent
   └─ Agent handles execution

3. CHANGE ROUTING LOGIC
   ├─ Add conditional routing rule: crew.add_routing_rule()
   ├─ Or set custom router: crew.router.set_custom_router()
   ├─ Or change routing strategy in CrewWorkflow
   └─ No agent/task code changes needed

4. ADD PRE/POST PROCESSING
   ├─ Create preprocess/postprocess functions
   ├─ Add to TaskDefinition when creating task
   ├─ Automatically applied during task execution
   └─ Keeps task definitions clean and testable

5. SWAP LLM PROVIDER
   ├─ Create OpenAILLM implementing same interface
   ├─ Pass to agents: agent = CompletionAgent(openai_llm)
   ├─ All agents work without modification
   └─ Zero changes to task/routing logic
"""

# =============================================================================
# TESTING STRATEGY
# =============================================================================

"""
LAYER TESTING APPROACH

1. CONFIG LAYER
   └─ Unit test: Load and validate env vars

2. API CLIENT LAYER  
   └─ Unit test + Mock: Check HTTP building, error handling

3. TOOLS LAYER
   └─ Unit test: ast_parser, bug_detector, context_extractor
   └─ Test with sample code strings, no API calls

4. AGENTS
   └─ Unit test with mock LLM
   └─ Mock: llm.generate() to return predictable output
   └─ Focus on prompt building, error handling

5. ORCHESTRATION
   └─ Integration test with mock agents
   └─ Test routing logic, task execution flow
   └─ Mock: Agent.execute() for predictability

6. END-TO-END
   └─ Integration test with real API
   └─ Only test with valid HUGGINGFACE_API_KEY
   └─ Check full workflows with actual LLM calls

MOCK EXAMPLE:
```python
from unittest.mock import Mock
from completion_agent import CompletionAgent

mock_llm = Mock()
mock_llm.generate.return_value = "def hello():\\n    pass"

agent = CompletionAgent(mock_llm)
result = agent.execute(code="def ", line_number=1)

assert result.success
assert "def hello" in result.output
```
"""
