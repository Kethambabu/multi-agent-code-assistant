"""
Centralized prompt templates for all agents.

Consolidates repeated prompt patterns used across agents.
Single source of truth for prompt engineering and conventions.

Dependency: None (leaf module).
"""

# ============================================================================
# Common Role Definitions
# ============================================================================

EXPERT_ROLE_TEMPLATE = "You are an expert {expertise} specializing in {specialty}."

ROLES = {
    "debugger": EXPERT_ROLE_TEMPLATE.format(
        expertise="software engineer",
        specialty="code debugging and testing"
    ),
    "explainer": EXPERT_ROLE_TEMPLATE.format(
        expertise="technical writer",
        specialty="code documentation and explanation"
    ),
    "test_writer": EXPERT_ROLE_TEMPLATE.format(
        expertise="quality assurance engineer",
        specialty="writing comprehensive unit tests"
    ),
    "code_completer": EXPERT_ROLE_TEMPLATE.format(
        expertise="developer",
        specialty="code completion and code generation"
    ),
    "code_editor": EXPERT_ROLE_TEMPLATE.format(
        expertise="software engineer",
        specialty="code refactoring and modifications"
    ),
    "code_creator": EXPERT_ROLE_TEMPLATE.format(
        expertise="software architect",
        specialty="project structure and file generation"
    ),
}

# ============================================================================
# Common Output Requirements
# ============================================================================

OUTPUT_RULES = {
    "return_only_code": (
        "Return ONLY the complete modified code in markdown code blocks. "
        "No explanations, no preamble."
    ),
    "return_only_json": (
        "Return ONLY a valid JSON object. "
        "No markdown code blocks, no extra text."
    ),
    "return_only_explanation": (
        "Return a clear, comprehensive explanation. "
        "Use markdown formatting for readability."
    ),
    "return_only_tests": (
        "Return ONLY valid Python unit test code. "
        "No explanations, ensure tests are runnable."
    ),
}

# ============================================================================
# Common Prompt Builders
# ============================================================================

def build_code_analysis_prompt(code: str, instruction: str, role: str = "debugger") -> str:
    """Build a prompt for code analysis tasks."""
    return f"""{ROLES[role]}

Your task: {instruction}

```python
{code}
```

{OUTPUT_RULES['return_only_explanation']}"""


def build_code_modification_prompt(code: str, instruction: str, role: str = "code_editor", file_ext: str = "py") -> str:
    """Build a prompt for code modification tasks."""
    return f"""{ROLES[role]}

Current code:
```{file_ext}
{code}
```

Instruction: {instruction}

{OUTPUT_RULES['return_only_code']}"""


def build_project_creation_prompt(project_description: str) -> str:
    """Build a prompt for project generation."""
    return f"""{ROLES['code_creator']}

Create a Python project based on this description:
{project_description}

Generate a project structure with multiple files.

{OUTPUT_RULES['return_only_json']}

Response format:
{{
  "files": {{
    "main.py": "complete python code",
    "utils.py": "complete python code",
    "requirements.txt": "dependencies",
    ...
  }}
}}"""


def build_file_selection_prompt(file_summaries: str, instruction: str) -> str:
    """Build a prompt for intelligent file selection."""
    return f"""{ROLES['code_editor']}

Based on this instruction: "{instruction}"

Here are the files in the project:
{file_summaries}

Which files should be modified? Return a JSON array with file paths.

{OUTPUT_RULES['return_only_json']}

Format: {{"files": ["path/to/file1.py", "path/to/file2.py"]}}"""
