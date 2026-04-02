# Code Analysis - Side-by-Side Comparisons of Duplicate Code

## 1. DUPLICATE AGENT PATTERNS

### 1.1 Execute Method Template Comparison

**All 6 agents follow this structure:**

#### Debug Agent - `src/agents/debug.py:26-104`
```python
def execute(self, code: str, line_number: Optional[int] = None, ...) -> dict:
    try:
        # Agent-specific logic (25+ lines)
        static_issues = detect_all_issues(code)
        manual_issues = self._manual_logic_checks(code)
        llm_analysis = self._llm_logic_analysis(code)
        # ... build output ...
        return { "status": "success", "output": ui_output, ... }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return { "status": "error", "output": "", "error": ... }
```

#### Explain Agent - `src/agents/explain.py:35-83`
```python
def execute(self, code: str, line_number: Optional[int] = None, ...) -> AgentResult:
    try:
        # Agent-specific logic (25+ lines)
        if line_number:
            explanation = self._explain_at_line(code, line_number, detail_level)
        else:
            explanation = self._explain_structure(code, detail_level)
        # ... build output ...
        return AgentResult(success=True, output=explanation, metadata={...})
    except Exception as e:
        return AgentResult(success=False, output="", error=f"Explanation generation failed: {e}")
```

#### Test Agent - `src/agents/test.py:29-91`
```python
def execute(self, code: str, line_number: Optional[int] = None, ...) -> AgentResult:
    try:
        if test_framework not in ("pytest", "unittest"):
            return AgentResult(success=False, output="", error="test_framework must be...")
        
        if line_number:
            tests = self._generate_function_tests(...)
        else:
            tests = self._generate_suite_tests(code, test_framework, coverage)
        
        return AgentResult(success=True, output=tests, metadata={...})
    except Exception as e:
        return AgentResult(success=False, output="", error=f"Test generation failed: {e}")
```

**PROBLEM:** Same structure repeated verbatim in all 6 agents. Only the internal logic changes.

**SOLUTION:**
```python
# src/agents/base.py - ADD THIS
class BaseAgent(ABC):
    def execute_safe(self, **kwargs) -> AgentResult:
        """Wraps execute() with consistent error handling."""
        try:
            return self._execute_impl(**kwargs)  # subclass implements this
        except Exception as e:
            logger.error(f"{self.role} failed", exc_info=False)
            return AgentResult(
                success=False,
                output="",
                error=f"{self.__class__.__name__} failed: {e}"
            )
    
    @abstractmethod
    def _execute_impl(self, **kwargs) -> AgentResult:
        """Subclasses override this instead of execute()."""
        ...
```

---

## 2. DUPLICATE PROMPT PATTERNS

### 2.1 "Expert Role" Pattern

#### Creator - `src/agents/creator.py:164-165`
```python
f"You are an expert software architect. Create a complete Python project "
f"based on the following description.\n\n"
```

#### Editor - `src/agents/editor.py:173-174`  
```python
f"You are an expert code editor. Your task is to modify code based on instructions.\n\n"
```

#### Completion - `src/agents/completion.py:118-119`
```python
f"You are an expert Python code completion engine.\n\n"
```

#### FileSelector - `src/file_selector.py:175`
```python
f"You are a code assistant. Given the user's request and the list of files "
```

**PATTERN MATCH:**
```
"You are an expert [ROLE]. [TASK DESCRIPTION]\n\n"
```

**SOLUTION:** Create `src/llm/prompts.py`:
```python
EXPERT_ROLES = {
    "architect": "You are an expert software architect. Create projects from descriptions.",
    "editor": "You are an expert code editor. Modify code based on instructions.",
    "completion": "You are an expert Python code completion engine.",
    "assistant": "You are a code assistant. Help with code analysis and selection.",
}

def build_expert_prompt(role_key: str, task_description: str) -> str:
    return f"{EXPERT_ROLES[role_key]} {task_description}\n\n"
```

### 2.2 "Return ONLY" Pattern

#### Creator (JSON) - `src/agents/creator.py:168`
```python
f"1. Return ONLY a JSON object — no text before or after\n"
```

#### Editor (Code) - `src/agents/editor.py:179-180`
```python
f"1. Return ONLY the complete modified file content\n"
f"2. Do NOT include explanations before or after the code\n"
```

#### Debug (JSON) - `src/agents/debug.py:136-140`
```python
"Return JSON ONLY with exact format:\n"
"{\n"
'  "bugs_found": true,\n'
'  "issues": ["Issue 1", "Issue 2"],\n'
...
```

#### FileSelector (JSON Array) - `src/file_selector.py:190`
```python
f"Return ONLY a JSON array of file paths to modify. Example:\n"
```

**SOLUTION:**
```python
# src/llm/prompts.py
OUTPUT_RULES = {
    "json_object": "Return ONLY a JSON object — no text before or after",
    "json_array": "Return ONLY a JSON array — no text before or after",
    "python_code": "Return ONLY Python code — no explanations or markdown fences",
    "complete_file": "Return ONLY the complete modified file content. Preserve structure and style.",
}

def build_rules_section(rule_keys: list[str]) -> str:
    rules = [f"{i+1}. {OUTPUT_RULES[key]}" for i, key in enumerate(rule_keys)]
    return "RULES:\n" + "\n".join(rules) + "\n"
```

---

## 3. DUPLICATE JSON PARSING

### 3.1 JSON Extraction Code Comparison

#### Creator - `src/agents/creator.py:195-217`
```python
def _parse_file_map(self, llm_response: str) -> Dict[str, str]:
    response = llm_response.strip()
    
    # Try extracting from markdown code fences
    json_str = self._extract_json_block(response)
    if json_str:
        return self._parse_json_map(json_str)
    
    # Try direct JSON parse
    result = self._parse_json_map(response)
    if result:
        return result
    
    # Try to find JSON object in the response
    start = response.find("{")
    end = response.rfind("}") + 1
    if start != -1 and end > start:
        return self._parse_json_map(response[start:end])
    
    return {}

def _extract_json_block(self, response: str) -> Optional[str]:
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def _parse_json_map(self, json_str: str) -> Dict[str, str]:
    try:
        data = json.loads(json_str)
        if isinstance(data, dict):
            if "files" in data and isinstance(data["files"], dict):
                return {str(k): str(v) for k, v in data["files"].items()}
            return {str(k): str(v) for k, v in data.items()}
    except json.JSONDecodeError:
        logger.debug(f"JSON parse failed for: {json_str[:100]}...")
    return {}
```

#### Debug - `src/agents/debug.py:145-160`
```python
def _llm_logic_analysis(self, code: str) -> dict:
    # ... build prompt ...
    try:
        response = self.llm.generate(prompt, max_tokens=600, temperature=0.2)
        response = response.strip()
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        
        start_idx = response.find("{")
        end_idx = response.rfind("}") + 1
        if start_idx != -1 and end_idx != -1:
            return json.loads(response[start_idx:end_idx])
        return {}
    except Exception as e:
        print(f"DEBUG: LLM Logic Analysis Failed: {e}")
        return {}
```

#### FileSelector - `src/file_selector.py:202-216`
```python
def _parse_file_list(self, response: str, valid_files: List[str]) -> List[str]:
    response = response.strip()
    
    # Try to extract JSON array
    match = re.search(r"\[.*?\]", response, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, list):
                return [f for f in parsed if f in valid_files]
        except json.JSONDecodeError:
            pass
    
    # Fallback: look for file paths in the response
    selected = []
    for f in valid_files:
        if f in response:
            selected.append(f)
    return selected
```

**PROBLEM:** 3 nearly identical implementations with slight variations:
- Creator uses regex `r"```(?:json)?\s*\n?(.*?)```"`
- Debug uses string split `"```json"... split("```")`
- FileSelector uses regex `r"\[.*?\]"` for arrays

**SOLUTION:** Create unified parser:
```python
# src/utils/response_parsers.py
import json
import re
from typing import Any, Optional, List, Dict

class ResponseParser:
    @staticmethod
    def extract_json(response: str) -> Optional[dict]:
        """Extract JSON object from LLM response (handles fences)."""
        response = response.strip()
        
        # Try ```json ... ``` fences first
        match = re.search(r"```(?:json)?\s*\n?(.*?)```", response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try raw JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON object boundaries
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(response[start:end])
            except json.JSONDecodeError:
                pass
        
        return None
    
    @staticmethod
    def extract_json_array(response: str) -> Optional[List]:
        """Extract JSON array from LLM response."""
        response = response.strip()
        
        # Try ```json ... ``` fences  
        match = re.search(r"```(?:json)?\s*\n?(.*?)```", response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try [...]
        match = re.search(r"\[.*?\]", response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None
    
    @staticmethod
    def extract_code_block(response: str, language: str = "") -> Optional[str]:
        """Extract code from ```language ... ``` blocks."""
        response = response.strip()
        
        # Try ```language ... ```
        if language:
            pattern = rf"```(?:{language}|{language.lower()})?\s*\n?(.*?)```"
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Try generic ``` ```
        match = re.search(r"```\s*\n?(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return response  # Return as-is if no fences
```

**USAGE:**
```python
# In creator.py - replace 23 lines with 1
file_map = ResponseParser.extract_json(llm_response)

# In debug.py - replace 15 lines with 1
analysis = ResponseParser.extract_json(response)

# In file_selector.py - replace 14 lines with 1
file_list = ResponseParser.extract_json_array(response)
```

---

## 4. DUPLICATE EDITOR/CREATOR RULES

### 4.1 Creator RULES - `src/agents/creator.py:167-181`
```python
f"RULES:\n"
f"1. Return ONLY a JSON object — no text before or after\n"
f"2. Use this exact format:\n"
f'{{\n'
f'  "files": {{\n'
f'    "main.py": "complete python code here",\n'
...
f"3. Include a main.py as the entry point\n"
f"4. Include requirements.txt with dependencies\n"
f"5. Each file must contain complete, runnable code\n"
f"6. Use proper Python best practices (docstrings, type hints)\n"
f"7. Add folder paths as needed (e.g. 'models/user.py')\n"
f"8. Include __init__.py files for packages\n\n"
```

### 4.2 Editor RULES - `src/agents/editor.py:178-188`
```python
f"RULES:\n"
f"1. Return ONLY the complete modified file content\n"
f"2. Do NOT include explanations before or after the code\n"
f"3. Do NOT add markdown code fences around your response\n"
f"4. Preserve existing code style, indentation, and structure\n"
f"5. Only change what the instruction asks for\n"
f"6. If the instruction asks to add something, add it in the correct location\n"
f"7. Keep all existing functionality intact unless told to remove it\n\n"
```

**SHARED CONCEPTS:**
- Both use RULES: section
- Both emphasize "Return ONLY..."
- Both avoid explanations  
- Both preserve existing code

**DIFFERENCE:**
- Creator focuses on file structure
- Editor focuses on modification boundaries

**SOLUTION:** Parameterized rules:
```python
# src/llm/prompts.py
def build_prompt(
    expert_role: str,
    task: str,
    rules: List[str],
    additional_instructions: str = "",
    examples: str = "",
) -> str:
    prompt = f"{EXPERT_ROLES[expert_role]}\n\n"
    prompt += f"{task}\n\n"
    
    if rules:
        prompt += "RULES:\n"
        for i, rule in enumerate(rules, 1):
            prompt += f"{i}. {rule}\n"
        prompt += "\n"
    
    if examples:
        prompt += f"EXAMPLES:\n{examples}\n\n"
    
    if additional_instructions:
        prompt += f"INSTRUCTIONS:\n{additional_instructions}\n\n"
    
    return prompt
```

---

## 5. DUPLICATE ERROR HANDLING PATTERNS

### 5.1 Pattern Comparison Table

| Agent | Location | Pattern | Logging |
|-------|----------|---------|---------|
| Debug | L104 | `except Exception as e: return {... error=f"..." }` | print() |
| Explain | L83 | `except Exception as e: return AgentResult(..., error=f"...failed"` | None |
| Test | L91 | `except Exception as e: return AgentResult(..., error=f"...failed"` | None |
| Completion | L96 | `except Exception as e: return AgentResult(..., error=f"...failed"` | None |
| Editor | L152 | `except Exception as e: logger.error(...); return AgentResult(...)` | logger.error() |
| Creator | L149 | `except Exception as e: logger.error(...); return AgentResult(...)` | logger.error() |

**PROBLEMS:**
1. Inconsistent: str(e) vs f-string vs no message
2. Inconsistent logging: some use logger, some print(), some silent
3. Debug returns dict, others return AgentResult
4. No consistent error notification level (debug, info, warning, error)

**SOLUTION:** Mixin class
```python
# src/agents/error_handling.py
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class ErrorHandlingMixin:
    """Provides consistent error handling for agents."""
    
    def safe_execute(self, method_name: str, **kwargs):
        """Decorator-like error handler."""
        try:
            method = getattr(self, method_name)
            return method(**kwargs)
        except Exception as e:
            error_msg = f"{self.__class__.__name__}.{method_name} failed: {type(e).__name__}: {e}"
            logger.error(error_msg, exc_info=False)
            
            return AgentResult(
                success=False,
                output="",
                error=error_msg,
            )

# Usage in any agent:
class DebugAgent(BaseAgent, ErrorHandlingMixin):
    def execute(self, **kwargs):
        return self.safe_execute("_execute_impl", **kwargs)
    
    def _execute_impl(self, **kwargs):
        # Actual logic here - no try/except needed
        ...
```

---

## 6. SUMMARY: Lines of Code to Consolidate

| Consolidation | Current State | After Refactor | Lines Saved |
|---|---|---|---|
| Response Parsing | 3 locations, 80 LOC | 1 utility class, 40 LOC | **40 LOC** |
| Prompt Templates | 15+ repetitions, 100 LOC | 1 prompts.py file, 30 LOC | **70 LOC** |
| Execute() pattern | 6 agents, 200 LOC | 1 base implementation, 50 LOC | **150 LOC** |
| Error Handling | 6 patterns, 100 LOC | 1 mixin class, 30 LOC | **70 LOC** |
| Agent Rules | 2 locations, 20 LOC | 1 parameterized function, 5 LOC | **15 LOC** |
| **TOTAL CONSOLIDATION** | **~500 LOC** | **~155 LOC** | **~345 LOC** (70% reduction) |

