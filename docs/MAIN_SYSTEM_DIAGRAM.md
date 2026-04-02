# System Integration Architecture

## Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                               │
│                   (Code from Editor)                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MAIN ENTRY POINT                              │
│              DeveloperAssistantSystem                           │
│                                                                 │
│  • Initializes all components                                   │
│  • Coordinates processing pipeline                              │
│  • Manages lifecycle                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────┬────────┴─────────┬────────────┐
        ▼            ▼                  ▼            ▼
    ┌────────┐  ┌────────┐         ┌──────────┐ ┌──────────┐
    │ Memory │  │ Trigger│ Routes  │  Agent   │ │   LLM    │
    │ Store  │  │ Engine │ Code ───Orchest.──┤ │Provider  │
    └────────┘  └────────┘         └──────────┘ └──────────┘
        ▲            ▲                  ▲            ▲
        └─Snapshots  └─Events           └─Executes  └─Generates
                                              │       Response
                                              │
                        ┌─────────────────┬───┘
                        │                 │
                    Agents:        Uses specialized
                    - Debug         code analysis:
                    - Explain       - AST Parser
                    - Complete      - Bug Detector
                    - Test          - Context Extractor
                        │
                        ▼
                   ┌──────────────┐
                   │ Agent Result │
                   │ (Success/Err)│
                   └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐
                   │ SYSTEM OUTPUT│
                   │   (Result)   │
                   └──────────────┘
```

## Module Dependencies (No Circular Dependencies)

```
┌──────────────────────────────────────────────────────────┐
│                    main.py                               │
│         (Single integration point - imports all)         │
└────────┬──────────┬──────────┬──────────┬────────────────┘
         │          │          │          │
         ▼          ▼          ▼          ▼
    ┌────────┐  ┌─────────┐  ┌────────┐ ┌──────────┐
    │ config │  │ hf_llm  │  │  agent │ │ trigger_ │
    │        │  │         │  │  orch  │ │ engine   │
    └────┬───┘  └────┬────┘  └───┬────┘ └────┬─────┘
         │           │           │           │
         │      ┌────▼────────┐  │      ┌────▼─────┐
         │      │ base_agent  │  │      │ memory   │
         │      │ +           │  │      │ store    │
         │      │ *_agent.py  │  │      └──────────┘
         │      └─────┬───────┘  │
         │            │          │
         └────────────┼──────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
    ┌─────────┐  ┌──────────┐  ┌──────────────┐
    │ast_     │  │bug_      │  │context_      │
    │parser   │  │detector  │  │extractor     │
    └─────────┘  └──────────┘  └──────────────┘
         ▲            ▲            ▲
         └────────────┼────────────┘
                      │
             (All independent,
              no cross-talk
              except via main)
```

## Dependency Injection Pattern

```python
# Clean flow - no tight coupling

┌─────────────────────────────────────┐
│  1. Create LLM Instance             │
│     llm = initialize_llm(config)    │
└────────────┬────────────────────────┘
             │ (Inject into agents)
             ▼
┌─────────────────────────────────────┐
│  2. Create Agent Orchestrator       │
│     agents = initialize_agents(llm) │
└────────────┬────────────────────────┘
             │ (Inject into trigger)
             ▼
┌─────────────────────────────────────┐
│  3. Create Trigger Engine           │
│     triggers = initialize_          │
│         trigger_engine(agents)      │
└────────────┬────────────────────────┘
             │ (Plus memory)
             ▼
┌─────────────────────────────────────┐
│  4. Main Coordinator                │
│     system = DeveloperAssistantSystem│
│         (llm, agents, triggers,     │
│          memory all injected)       │
└─────────────────────────────────────┘

Result: Zero global state, easy to test,
        components are reusable
```

## Input → Trigger → Agent → Output Flow

```python
# Concrete example flow:

User Input: code = "def foo() print('hi')"
                └──────┬──────────────────────────────────┐
                       ▼                                  │
            1. process_code_input(code)                  │
                       ▼                                  │
            2. memory.snapshot_code()                    │
               └─ Store: "Code v1: incomplete"         │
                       ▼                                  │
            3. detect_all_issues(code)                   │
               └─ Find: ["SyntaxError on line 1"]      │
                       ▼                                  │
            4. Create Event(SYNTAX_ERROR, code)          │
                       ▼                                  │
            5. trigger_engine.route_event()              │
               └─ Route condition: event.type == SYNTAX_ERROR
                       ▼                                  │
            6. Return RoutingResult                      │
               └─ agent_type="debug"                    │
                  agent_name="debug"                    │
                  priority=3                            │
                       ▼                                  │
            7. assistant.registry.execute(               │
                   "debug", code, issues=...)           │
                       ▼                                  │
            8. DebugAgent.execute() runs:                │
               - Builds prompt with context             │
               - Calls llm.generate(prompt)             │
               - Formats response                       │
                       ▼                                  │
            9. Return AgentResult(success, output)       │
                       ▼                                  │
           10. memory.add_entry(response)                │
               └─ Store: "Debug response: ..."         │
                       ▼                                  │
           11. Return to caller ───────────────────────┘

Total: 11 steps, 0 duplicated logic, all decoupled
```

## Extension Points

```
┌────────────────────────────────────────────────┐
│         ADD CUSTOM AGENT                       │
├────────────────────────────────────────────────┤
│ class MyCustomAgent(BaseAgent):                │
│     role = "my_role"                           │
│     goal = "my_goal"                           │
│     execute(context) → AgentResult             │
│                                                │
│ system.assistant.register_agent(               │
│     "my_custom", MyCustomAgent(system.llm)     │
│ )                                              │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│         ADD CUSTOM TRIGGER RULE                │
├────────────────────────────────────────────────┤
│ def custom_condition(event):                   │
│     return "TODO" in event.code                │
│                                                │
│ def custom_route(event):                       │
│     return RoutingResult(...)                  │
│                                                │
│ system.trigger_engine.register_rule(           │
│     condition=custom_condition,                │
│     route=custom_route                         │
│ )                                              │
└────────────────────────────────────────────────┘

Result: Extended without modifying existing code
        (Open/Closed Principle)
```

## Memory Management

```
┌──────────────────────────────────────┐
│      MemoryStore (Internal)          │
├──────────────────────────────────────┤
│                                      │
│  _memory (deque, max=100 entries)   │
│  ├─ code: "def foo()..."            │
│  ├─ response: "Agent response"      │
│  ├─ error: "Syntax error at..."     │
│  └─ context: "imports, classes"     │
│                                      │
│  _snapshots (deque, max=10)         │
│  ├─ CodeSnapshot v1                 │
│  ├─ CodeSnapshot v2                 │
│  └─ CodeSnapshot v3                 │
│                                      │
└──────────────────────────────────────┘
        ▲                  ▲
        │ snapshot_code()  │ add_entry()
        │                  │
   ┌────┴──────────────────┴────┐
   │  DeveloperAssistantSystem   │
   │  - On new code input        │
   │  - On agent response        │
   │  - On errors                │
   └─────────────────────────────┘
```

## Trigger Routing Rules

```
Event arrives: SYNTAX_ERROR

                    ┌─────────────────────────┐
                    │  Route Event            │
                    └──────────┬──────────────┘
                               │
                    ┌──────────▼──────────┐
                    │ Check each rule:    │
                    │ (order matters)     │
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
   ┌──────────────┐      ┌──────────────┐     ┌──────────────┐
   │ Rule 1       │      │ Rule 2       │     │ Rule 3       │
   │ SYNTAX_ERROR │      │ CODE_CHANGE  │     │ etc...       │
   │ → DEBUG      │      │ → COMPLETE   │     │              │
   └──────┬───────┘      └──────────────┘     └──────────────┘
          │
          │ ✓ MATCH!
          │
          ▼
   ┌──────────────────────────┐
   │ RoutingResult:           │
   │ - agent_type: "debug"    │
   │ - agent_name: "debug"    │
   │ - priority: 3 (HIGH)     │
   └──────────────────────────┘
```

## Key Characteristics

```
✓ MODULARITY
  - No duplicate logic
  - Clean separation of concerns
  - Independent modules

✓ DEPENDENCY INJECTION
  - Components injected via constructor
  - No global state
  - Easy to test

✓ EVENT-DRIVEN
  - Trigger engine routes events
  - Loose coupling between components
  - Extensible with new rules

✓ MEMORY MANAGEMENT
  - Code snapshots tracked
  - Conversation history preserved
  - Automatic cleanup

✓ ERROR HANDLING
  - Graceful failures
  - Proper error propagation
  - Recovery mechanisms

✓ EXTENSIBILITY
  - Add custom agents
  - Add custom triggers
  - No core code changes needed
```

## When to Use Each Method

```
process_code_input()
├─ When: Editor changes, user input
├─ Does: Full pipeline (trigger → route → execute)
├─ Returns: AgentResult
└─ Example: On typing pause

debug_code()
├─ When: User clicks debug button
├─ Does: Direct agent execution (skips trigger)
├─ Returns: AgentResult
└─ Example: Manual debugging

explain_code()
├─ When: User clicks explain button
├─ Does: Direct agent execution
├─ Returns: AgentResult
└─ Example: Code explanation on demand

analyze_code()
├─ When: Just need info (no agent)
├─ Does: Code analysis only
├─ Returns: Dict with analysis
└─ Example: Extracting functions/classes

complete_code()
├─ When: User requests completion
├─ Does: Direct agent execution
├─ Returns: AgentResult
└─ Example: Code completion on demand
```
