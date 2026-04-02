# Streamlit UI - Architecture Diagrams

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     User/Browser                             │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTP/WebSocket
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                   STREAMLIT UI LAYER                         │
│              (Pure Presentation - Zero Logic)                │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ streamlit_app.py                                    │   │
│  │                                                     │   │
│  │  Page Layout & Styling                            │   │
│  │  ├─ Header                                        │   │
│  │  ├─ Sidebar (Status)                              │   │
│  │  └─ Main Content                                  │   │
│  │      ├─ Code Editor (Text Area)                   │   │
│  │      ├─ Action Buttons                            │   │
│  │      │  ├─ 💡 Explain                            │   │
│  │      │  ├─ 🔧 Fix                                │   │
│  │      │  ├─ 🧪 Generate Tests                     │   │
│  │      │  └─ 📊 Analyze                            │   │
│  │      └─ Result Display                            │   │
│  │                                                     │   │
│  │  Session State (UI Only)                          │   │
│  │  ├─ code_input                                    │   │
│  │  ├─ last_result                                   │   │
│  │  └─ system reference (cached)                     │   │
│  │                                                     │   │
│  │  Error Display                                     │   │
│  │  ├─ Empty code message                            │   │
│  │  ├─ Backend error display                         │   │
│  │  └─ Exception handling                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                         │                                    │
│  Responsibility:        │ Calls Backend Only               │
│  - Display             │                                    │
│  - Input Collection    │                                    │
│  - Layout/Styling      │                                    │
│  - Error Presentation  │                                    │
│  - Session State       │                                    │
│                        │                                    │
└────────────────────────┼────────────────────────────────────┘
                         │
                         │ result = system.explain_code(code)
                         │ result = system.debug_code(code)
                         │ analysis = system.analyze_code(code)
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                   BUSINESS LOGIC LAYER                       │
│              (All Logic - All Processing)                    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ main.py                                             │   │
│  │ DeveloperAssistantSystem                            │   │
│  │                                                     │   │
│  │  ├─ LLM (Hugging Face)                            │   │
│  │  │  └─ API calls, retry logic, error handling     │   │
│  │  │                                                 │   │
│  │  ├─ Agents (Orchestrator)                         │   │
│  │  │  ├─ Debug Agent                                │   │
│  │  │  ├─ Explain Agent                              │   │
│  │  │  ├─ Complete Agent                             │   │
│  │  │  └─ Test Agent                                 │   │
│  │  │                                                 │   │
│  │  ├─ Trigger Engine                                │   │
│  │  │  └─ Event routing & rule evaluation            │   │
│  │  │                                                 │   │
│  │  ├─ Memory Store                                  │   │
│  │  │  ├─ Code snapshots                             │   │
│  │  │  └─ Conversation history                       │   │
│  │  │                                                 │   │
│  │  └─ Analysis Tools                                │   │
│  │     ├─ AST Parser                                 │   │
│  │     ├─ Bug Detector                               │   │
│  │     └─ Context Extractor                          │   │
│  │                                                     │   │
│  │  Processing Pipeline:                             │   │
│  │  Input → Analyze → Route → Agent → LLM → Output  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  Responsibility:                                            │
│  - Code analysis                                            │
│  - Agent orchestration                                      │
│  - LLM calls                                                │
│  - Error handling                                           │
│  - Memory management                                        │
│  - Trigger routing                                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Data Flow - Detailed

### User Clicks "Explain" Button

```
┌─────────────────────────────────────────────────────────────┐
│ 1. UI: User Enters Code                                     │
│    code = "def hello(): print('hi')"                        │
│    Button click: "Explain"                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 2. UI: Show Spinner                                         │
│    with st.spinner("🤔 Explaining code...")                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 3. UI: Call Backend (via Cached System)                     │
│    system = get_system()  # From cache                      │
│    result = system.explain_code(code)                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 4. Backend: Process Request                                 │
│    │                                                         │
│    ├─ Memory: snapshot_code()                               │
│    ├─ Analysis: detect_issues()                             │
│    ├─ Routing: Create event                                 │
│    ├─ Agent: ExplainAgent.execute()                         │
│    ├─ LLM: llm.generate(prompt)                             │
│    ├─ Memory: store result                                  │
│    └─ Return: AgentResult(success, output)                  │
│                                                              │
└──────────────────────┬──────────────────────────────────────┘
                       │ result =
                       │ {
                       │   success: True,
                       │   output: "This is a hello function..." ,
                       │   metadata: {...}
                       │ }
┌──────────────────────▼──────────────────────────────────────┐
│ 5. UI: Display Result                                       │
│    display_result(result, "Code Explanation")               │
│                                                              │
│    if result.success:                                       │
│        st.success(result.output)  # Green box               │
│    else:                                                    │
│        st.error(result.error)     # Red box                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Interaction

```
        STREAMLIT UI
             │
        ┌────┴─────┬─────────┬──────────┐
        │           │         │          │
    Sidebar      Editor    Buttons   Results
        │           │         │          │
        │      Display      Get      Display
        │      Code Input  Input    Results
        │           │       │          │
        │           └───┬───┴──────────┘
        │               │
        │        system.explain_code()
        │        system.debug_code()
        │        system.generate_tests()
        │        system.analyze_code()
        │
        └───────────────┬──────────────────
                        │
                    BACKEND
                        │
        ┌──────┬────────┼────────┬──────┬──────────┐
        │      │        │        │      │          │
       LLM   Agent   Memory   Trigger Analysis    Tools
              |
        ┌─────┴────────┬───────────┬──────────┐
        │              │           │          │
      Debug        Explain      Complete    Test
      Agent        Agent        Agent       Agent
```

---

## Processing Paths

### Path 1: Explain Code
```
explain_code(code)
    ↓
ExplainAgent.execute(code)
    ↓
  llm.generate("Explain: " + code)
    ↓
  result = "This code does..."
    ↓
AgentResult(success=True, output=result)
```

### Path 2: Debug Code
```
debug_code(code)
    ↓
  detect_issues(code)
    ↓
  DebugAgent.execute(code, issues)
    ↓
  llm.generate("Fix these issues: " + issues)
    ↓
  result = "Issues: ..., Fixes: ..."
    ↓
AgentResult(success=True, output=result)
```

### Path 3: Generate Tests
```
generate_tests(code)
    ↓
  TestAgent.execute(code, framework="pytest")
    ↓
  llm.generate("Generate tests for: " + code)
    ↓
  result = "def test_...(): ..."
    ↓
AgentResult(success=True, output=result)
```

### Path 4: Analyze Code
```
analyze_code(code)
    ↓
  extract_functions(code)
    extract_classes(code)
    extract_imports(code)
    detect_all_issues(code)
    get_context_summary(code)
    ↓
  analysis = {
    functions: [...],
    classes: [...],
    imports: [...],
    issues: [...],
    summary: {...}
  }
    ↓
  UI displays metrics & details
```

---

## Separation of Concerns

```
┌──────────────────────────────────┐
│      STREAMLIT UI LAYER          │
├──────────────────────────────────┤
│                                  │
│  Concerns:                       │
│  ✓ Display layout                │
│  ✓ Input collection              │
│  ✓ Button handlers               │
│  ✓ Error presentation            │
│  ✓ Session state                 │
│                                  │
│  NOT Concerns:                   │
│  ✗ Code analysis                 │
│  ✗ Agent selection               │
│  ✗ LLM calls                     │
│  ✗ Error handling logic          │
│  ✗ Memory management             │
│                                  │
└────────────────┬─────────────────┘
                 │ Delegates everything
                 │
┌────────────────▼─────────────────┐
│    BACKEND LOGIC LAYER           │
├──────────────────────────────────┤
│                                  │
│  Concerns:                       │
│  ✓ Code analysis                 │
│  ✓ Agent orchestration           │
│  ✓ LLM communication             │
│  ✓ Error handling                │
│  ✓ Memory management             │
│  ✓ Trigger routing               │
│                                  │
│  NOT Concerns:                   │
│  ✗ Display formatting            │
│  ✗ User interface                │
│                                  │
└──────────────────────────────────┘
```

---

## Session State Diagram

```
┌─────────────────────────────────────────┐
│       STREAMLIT SESSION                 │
├─────────────────────────────────────────┤
│                                         │
│  @st.cache_resource                     │
│  get_system()                           │
│  └─ System created ONCE                 │
│     └─ Reused for all interactions      │
│                                         │
│  st.session_state                       │
│  ├─ code_input: str                     │
│  │  └─ Current code in editor           │
│  │                                      │
│  ├─ last_result: str or None            │
│  │  └─ Last button clicked              │
│  │                                      │
│  └─ system: DeveloperAssistantSystem    │
│     └─ Reference (from cache)           │
│                                         │
│  Streamlit Rerun on:                    │
│  - Button click                         │
│  - Text area change                     │
│  - Slider/input change                  │
│                                         │
│  Cache Behavior:                        │
│  - get_system() runs ONCE per session   │
│  - Subsequent calls return cached ref   │
│  - Memory preserved across reruns       │
│                                         │
└─────────────────────────────────────────┘
```

---

## Error Handling Flow

```
┌──────────────────────────────────────┐
│          USER ACTION                 │
│    (Click Button, Enter Code)        │
└────────────────┬─────────────────────┘
                 │
    ┌────────────▼────────────┐
    │ UI validation           │
    │ if code == "":          │
    │   show info ("Empty")   │
    │   return                │
    └────────────┬────────────┘
                 │
    ┌────────────▼────────────┐
    │ Call backend            │
    │ try:                    │
    │   result = system...()  │
    │ except Exception as e:  │
    │   show error (e)        │
    │   return                │
    └───┬────────────┬────────┘
        │            │
    Success         Error
        │            │
    ┌───▼──┐    ┌────▼──┐
    │Check│    │Show    │
    │Result    │Error   │
    │Status    │        │
    └───┬──┐   └────────┘
        │ │
   Success│Error
        │ │
    Display Display
    Output Error Msg
```

---

## Caching Strategy

```
First Request:
│
├─ Call get_system()
│  ├─ Check cache (MISS)
│  ├─ Create system
│  │  ├─ Initialize LLM (slow)
│  │  ├─ Create agents
│  │  ├─ Create memory
│  │  ├─ Create triggers
│  │  └─ Ready
│  └─ Store in cache
│
├─ Process request
│  ├─ Call agent (LLM call ~10s)
│  └─ Return result
│
└─ Display: Total ~15-20s

Subsequent Requests:
│
├─ Call get_system()
│  ├─ Check cache (HIT!)
│  ├─ Return cached reference
│  └─ INSTANT
│
├─ Process request
│  ├─ Call agent (LLM call ~10s)
│  └─ Return result
│
└─ Display: Total ~10-15s

Benefit: 50% faster after first request!
```

---

## File Dependencies

```
streamlit_app.py
    │
    ├─ imports main
    │   └─ main.py
    │       ├─ imports config
    │       ├─ imports hf_llm
    │       ├─ imports agent_orchestrator
    │       ├─ imports memory_store
    │       ├─ imports trigger_engine
    │       ├─ imports ast_parser
    │       ├─ imports bug_detector
    │       └─ imports context_extractor
    │
    └─ imports base_agent
        └─ AgentResult class
```

**Important**: streamlit_app.py only imports main and base_agent!

---

## Deployment Architecture

### Local Development
```
User Browser ──→ Streamlit Dev Server ──→ Backend
(localhost:8501)    (streamlit_app.py)
```

### Production (Streamlit Cloud)
```
User Browser ──→ Streamlit Cloud ──→ Container ──→ Backend
                                      (app code)
```

### Docker Deployment
```
User Browser ──→ Docker Container ──→ Streamlit App ──→ Backend
                 (port 8501)          (streamlit_app.py)
```

---

## Architecture Principles

```
SOLID Principles:

S - Single Responsibility
  ✓ UI layer only handles display
  ✓ Backend only handles logic

O - Open for Extension
  ✓ Add new buttons → Call new system methods
  ✓ No need to change existing code

L - Liskov Substitution
  ✓ Any AgentResult can be displayed

I - Interface Segregation
  ✓ UI only needs system.method() interface
  ✓ Doesn't need internal details

D - Dependency Inversion
  ✓ UI depends on Backend abstraction
  ✓ Not on specific implementations
```

---

## Summary

```
┌────────────────────────────────────────────┐
│  STREAMLIT UI                              │
│  • Presentation Only                       │
│  • Input Collection                        │
│  • Result Display                          │
│  • Error Presentation                      │
│  • NO Business Logic                       │
╔════════════════════════════════════════════╗
║              Separation Line               ║
║   (Only system method calls cross here)    ║
╚════════════════════════════════════════════╝
│  BACKEND LOGIC (main.py)                   │
│  • Code Analysis                           │
│  • Agent Orchestration                     │
│  • LLM Communication                       │
│  • Memory Management                       │
│  • Error Handling                          │
│  • Trigger Routing                         │
└────────────────────────────────────────────┘
```

**Key**: Clean separation enables both layers to be developed, tested, and deployed independently!
