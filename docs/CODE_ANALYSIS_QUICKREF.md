# Code Analysis - Quick Reference by Issue Type

## 1. DUPLICATE PATTERNS - BY CATEGORY

### 1.1 Prompt Template Repetition

**"You are an expert..." pattern (4 occurrences):**
- Creator: `src/agents/creator.py:164` - "architect"
- Editor: `src/agents/editor.py:173` - "code editor"  
- Completion: `src/agents/completion.py:118` - "completion engine"
- FileSelector: `src/file_selector.py:175` - "code assistant"

**"Return ONLY..." pattern (3+ occurrences):**
- Creator JSON: `src/agents/creator.py:168` - "Return ONLY a JSON object"
- Editor CODE: `src/agents/editor.py:179` - "Return ONLY the complete modified file"
- Debug JSON: `src/agents/debug.py:136` - "Return JSON ONLY"
- FileSelector JSON: `src/file_selector.py:190` - "Return ONLY a JSON array"

### 1.2 JSON Extraction Logic (3 locations)
1. `src/agents/creator.py:195-217` - _extract_json_block() + _parse_json_map()
2. `src/agents/debug.py:145-160` - lines 147-154 JSON extraction
3. `src/file_selector.py:202-216` - _parse_file_list() JSON extraction

All use regex patterns: `r"```json..```"` or `r"[.*?]"` to extract

### 1.3 Code Fence Extraction (3 locations)
1. `src/agents/editor.py:219-243` - _extract_code() with 3 approaches
2. `src/agents/creator.py:219-225` - _extract_json_block()
3. `src/agents/debug.py:145-160` - similar fence splitting

### 1.4 Execute() Method Pattern
All 6 agents follow identical structure:
```python
def execute(self, ...):
    try:
        # agent-specific logic
        return AgentResult(success=True, ...)
    except Exception as e:
        return AgentResult(success=False, ..., error=str(e))
```

Locations:
- `src/agents/debug.py:26-104`
- `src/agents/explain.py:35-83`
- `src/agents/test.py:29-91`
- `src/agents/completion.py:30-96`
- `src/agents/editor.py:52-152`
- `src/agents/creator.py:48-149`

## 2. UNUSED IMPORTS

### 2.1 Confirmed Unused
- `src/agents/debug.py:9` - `from src.tools.ast_parser import get_ast`
  - Imported but function never called anywhere in file
  - File uses detect_all_issues() for static analysis, not get_ast()

---

## 3. DEAD CODE

### 3.1 Never Called Methods
1. **BaseAgent._build_prompt()** 
   - Location: `src/agents/base.py:46-47`
   - Never called in any subclass
   - Each agent builds prompts directly

2. **DebugAgent._suggest_fix()**
   - Location: `src/agents/debug.py:165-182`
   - Only called in unreachable path (see 3.3)
   - Actually never invoked in practice

3. **ExplainAgent._generate_explanation()**
   - Location: `src/agents/explain.py:114-125` 
   - Wait, this IS called (line 76, 82, 112)
   - Actually used ✓

### 3.2 Unreachable Code Paths
1. **src/agents/debug.py:78-80** 
   - Lines 78-86 check `if not corrected_code and static_issues:`
   - But if we reach here, bugs_found=True (early return at line 47 if False)
   - static_issues can be accessed but logic is awkward

2. **src/llm/huggingface.py:71-75**
   - ValueError exception handler
   - But call_hf_api() already converts ValueErrors to messages
   - Can never be raised from call_hf_api()

### 3.3 Unused Modules/Classes
**Complete list:**

| Component | Location | Lines | Status |
|-----------|----------|-------|--------|
| CrewWorkflow | `src/orchestration/crew.py:100-200+` | 150+ | DEAD - pipeline.py never imports |
| TaskRouter | `src/orchestration/crew.py:49-80` | 31 | DEAD - part of unused CrewWorkflow |
| RoutingStrategy | `src/orchestration/crew.py:44-47` | 4 | DEAD - enum never used |
| TaskFactory | `src/orchestration/tasks.py:57-112` | 55 | DEAD - only used by unused CrewWorkflow |
| TaskValidator | `src/orchestration/tasks.py:141-170` | 29 | DEAD |
| TaskRegistry | `src/orchestration/tasks.py:167-224` | 57 | DEAD |
| TriggerEngine | `src/engine/trigger.py:82-430` | 350+ | DEAD - never instantiated in pipeline |
| DebugAgent | `src/agents/debug.py` | ENTIRE FILE | PARTIALLY - registered but never called |
| ExplainAgent | `src/agents/explain.py` | ENTIRE FILE | PARTIALLY - registered but never called |
| TestAgent | `src/agents/test.py` | ENTIRE FILE | PARTIALLY - registered but never called |
| CompletionAgent | `src/agents/completion.py` | ENTIRE FILE | PARTIALLY - registered but never called |

### 3.4 Dead Code Paths in Pipeline
**File: src/pipeline.py**

Lines 132-135: Registers 4 agents that are never used:
```python
self.registry.register("debug", DebugAgent(self.llm))
self.registry.register("explain", ExplainAgent(self.llm))
self.registry.register("test", TestAgent(self.llm))
```

But pipeline only uses EditorAgent and CreatorAgent through explicit calls:
- Line 194: `self._create_project(prompt)` - uses CreatorAgent only
- Line 197: `self._edit_project(prompt)` - uses EditorAgent only

**Result:** 4 agents are prepared but no code path invokes them. Lines 212, 226 iterate agent_results but those come from creator/editor only, never from debug/explain/test/completion.

---

## 4. OVERLY COMPLEX ABSTRACTIONS

### 4.1 Unused Task Infrastructure
**Total lines of dead code:** ~150 lines across 2 files

**src/orchestration/tasks.py - Complete breakdown:**
- `TaskType enum` (6 lines) - UNUSED
- `TaskDefinition dataclass` (15 lines) - UNUSED  
- `TaskFactory` class (55 lines) - UNUSED
- `TaskValidator` class (29 lines) - UNUSED
- `TaskRegistry` class (57 lines) - UNUSED

**What it's for:** Defining 4 hardcoded tasks (COMPLETION, DEBUG, EXPLAIN, TEST) and validating them

**Current alternative in code:** Hard to find because pipeline doesn't use it

**Simpler approach:**
```python
# Instead of 200 lines of infrastructure:
TASKS = {
    "debug": {"agent": "debug", "required": ["code"]},
    "explain": {"agent": "explain", "required": ["code"]},
    ...
}
```

### 4.2 Over-Engineered Routing
**src/orchestration/crew.py:49-80**

`RoutingStrategy` enum with 3 strategies:
- DIRECT (simple)
- CONDITIONAL (with functions)
- CUSTOM (with arbitrary router function)

**Actual usage:** Only DIRECT is ever set (default)

**What pipeline actually needs:** If-statement deciding between EditorAgent and CreatorAgent

### 4.3 LLMProvider Protocol Abstraction

**File: src/llm/provider.py** (30 lines)

Defines Protocol interface with @runtime_checkable decorator

**Problem:** 
- Only one implementation exists (HuggingFaceLLM)
- Protocol is marked for duck-typing but agents explicitly call LLMProvider type
- Would only matter if swapping implementations

**True complexity:** None - adds indirection without benefit

---

## 5. REPEATED STRINGS & TEMPLATES

### 5.1 Prompt Instruction Patterns

**Instruction: Output Format (4+ locations)**
```
"Return ONLY a JSON object — no text before or after"       [creator.py:168]
"Return ONLY the complete modified file content"            [editor.py:179]  
"Return ONLY a JSON array of file paths to modify"          [file_selector.py:190]
"Return JSON ONLY with exact format: { ... }"               [debug.py:136-140]
```

**Instruction: Code Style (3 locations)**
```
"Preserve existing code style, indentation, and structure"  [editor.py:184]
"Use proper Python best practices (docstrings, type hints)" [creator.py:173]
"Professional, well-commented"                              [test.py:163]
```

**Expert Role Pattern (4 locations)**
```python
f"You are an expert software architect..."                   [creator.py:164]
f"You are an expert code editor..."                          [editor.py:173]
f"You are an expert Python code completion engine..."        [completion.py:118]
f"You are a code assistant..."                              [file_selector.py:175]
```

### 5.2 Rule Section Duplication
Editor & Creator both have RULES: section with similar content:
- Editor (7 rules, [src/agents/editor.py:178-188](src/agents/editor.py#L178))
- Creator (8 rules, [src/agents/creator.py:167-181](src/agents/creator.py#L167))

Overlap:
- Both say "Return ONLY..."
- Both say "Do NOT include explanations"
- Both say "Preserve/follow best practices"

---

## 6. REDUNDANT ERROR HANDLING

### 6.1 Exception Pattern Inconsistency

**Pattern A: Generic with str()**
```python
except Exception as e:
    return AgentResult(..., error=str(e))
```
Locations: `debug.py:104`, `creator.py:149`, `test.py:91`

**Pattern B: Generic with f-string**
```python
except Exception as e:
    return AgentResult(..., error=f"Xxx failed: {e}")
```
Locations: `explain.py:83`, `completion.py:96`, `editor.py:152`

**Pattern C: Bare except (bad practice)**
```python
except Exception:
    return f"Could not..."
```
Locations: `explain.py:167`, `test.py:167`

**Pattern D: With logging**
Some do it, some don't:
- `editor.py:152` - logs with exc_info=True ✓
- `debug.py:104` - no logging ✗
- `creator.py:149` - logs ✓
- `explain.py:83` - no logging ✗

### 6.2 Double Error Wrapping

**src/llm/client.py:56-69** catches exceptions:
```python
except ValueError as e:
    raise ValueError("Invalid API key...")
except requests.exceptions.Timeout:
    raise requests.exceptions.RequestException(...)
```

**src/llm/huggingface.py:50-98** then catches those and wraps:
```python
except ValueError as e:
    return f"Error: Invalid configuration..."
except requests.exceptions.Timeout as e:
    # retry logic...
```

### 6.3 Silent Error Swallowing in Tools

**src/tools/bug_detector.py:30-37**
```python
except ParseError as e:
    # Returns error report
```

**src/tools/context_extractor.py:48-50**
```python
except ParseError:
    return None  # Caller doesn't know if actual error or no data
```

Inconsistent handling of same exception type.

---

## 7. ARCHITECTURAL DUPLICATION

### 7.1 Two Parallel Orchestration Systems

**System 1: AssistantPipeline** ([src/pipeline.py](src/pipeline.py))
- Binary decision tree (empty → create, else → edit)
- 2 agents (Editor, Creator)
- Direct orchestration
- Memory integrated

**System 2: CrewWorkflow** ([src/orchestration/crew.py](src/orchestration/crew.py))
- Task-based routing
- 4 agents (Completion, Debug, Explain, Test)  
- Router-based dispatch
- Task validation/preprocessing

**Problem:** Pipeline doesn't use CrewWorkflow at all. They're completely separate implementations of orchestration.

**Why it's problematic:**
- If you add a new agent, which system do you modify?
- If you want to fix agent behavior, which one is the "real" implementation?
- 200+ lines of code duplicated

### 7.2 Duplicate Agent Registration
**In src/pipeline.py:132-135**
```python
self.registry.register("debug", DebugAgent(self.llm))
self.registry.register("explain", ExplainAgent(self.llm))
self.registry.register("test", TestAgent(self.llm))
```

**In src/orchestration/crew.py:132-135**
```python
self.agent_registry.register("completion", CompletionAgent(self.llm))
self.agent_registry.register("debug", DebugAgent(self.llm))
self.agent_registry.register("explain", ExplainAgent(self.llm))
self.agent_registry.register("test", TestAgent(self.llm))
```

Same registrations in two places!

---

## 8. SUMMARY STATISTICS

| Category | Count | Severity | Est. LOC |
|----------|-------|----------|---------|
| Repeated prompts | 4+ patterns | MEDIUM | 100+ |
| Repeated JSON parsing | 3 locations | MEDIUM | 60 |
| Repeated code fence extraction | 3 locations | MEDIUM | 50 |
| Similar execute() patterns | 6 agents | MEDIUM | 200+ |
| Unused imports | 1 | LOW | 1 |
| Dead methods | 2 | LOW | 30 |
| Unreachable code paths | 2 | MEDIUM | 20 |
| Unused agent modules | 4 | HIGH | 600+ |
| Dead modules (crew/tasks/engine) | 3 | HIGH | 400+ |
| Over-complex abstractions | 3 | HIGH | 150 |
| Error handling inconsistencies | 6 patterns | MEDIUM | 100+ |

**Total Dead/Redundant Code:** 1,400+ lines (35-40% of src/ codebase)

