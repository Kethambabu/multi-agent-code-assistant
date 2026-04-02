"""
Quick reference and integration guide for CrewAI workflow.
Demonstrates practical usage patterns for developers.
"""

# =============================================================================
# QUICK START
# =============================================================================

"""
from crew_setup import create_developer_crew
from tasks import TaskType

# Create crew
crew = create_developer_crew()

# Execute a task
result = crew.execute_task(
    TaskType.DEBUG,
    {"code": "your_code_here"}
)

if result.success:
    print(result.output)
else:
    print(f"Error: {result.error}")
"""

# =============================================================================
# INTEGRATION EXAMPLES
# =============================================================================

"""
1. EDITOR INTEGRATION
======================
from crew_setup import create_developer_crew
from tasks import TaskType

crew = create_developer_crew()

class EditorIntegration:
    def on_completion_request(self, code, line):
        result = crew.execute_task(
            TaskType.COMPLETION,
            {"code": code, "line_number": line}
        )
        return result.output if result.success else None
    
    def on_error_detected(self, code, line):
        result = crew.execute_task(
            TaskType.DEBUG,
            {"code": code, "line_number": line}
        )
        return result.output if result.success else None
    
    def on_explain_request(self, code, line):
        result = crew.execute_task(
            TaskType.EXPLAIN,
            {"code": code, "line_number": line, "detail_level": "medium"}
        )
        return result.output if result.success else None


2. REST API INTEGRATION
=======================
from flask import Flask, request, jsonify
from crew_setup import create_developer_crew
from tasks import TaskType

app = Flask(__name__)
crew = create_developer_crew()

@app.route('/api/complete', methods=['POST'])
def complete():
    data = request.json
    result = crew.execute_task(
        TaskType.COMPLETION,
        {"code": data['code'], "line_number": data['line']}
    )
    
    return jsonify({
        "success": result.success,
        "output": result.output,
        "error": result.error,
    })

@app.route('/api/debug', methods=['POST'])
def debug():
    data = request.json
    result = crew.execute_task(
        TaskType.DEBUG,
        {"code": data['code']}
    )
    
    return jsonify({
        "success": result.success,
        "issues": result.output,
        "metadata": result.metadata,
    })


3. CLI TOOL INTEGRATION
=======================
import click
from crew_setup import create_developer_crew
from tasks import TaskType

crew = create_developer_crew()

@click.group()
def cli():
    pass

@cli.command()
@click.argument('filepath')
@click.option('--line', type=int, help='Target line number')
def explain(filepath, line):
    with open(filepath) as f:
        code = f.read()
    
    result = crew.execute_task(
        TaskType.EXPLAIN,
        {"code": code, "line_number": line}
    )
    
    if result.success:
        click.echo(result.output)
    else:
        click.echo(f"Error: {result.error}", err=True)

@cli.command()
@click.argument('filepath')
def debug(filepath):
    with open(filepath) as f:
        code = f.read()
    
    result = crew.execute_task(
        TaskType.DEBUG,
        {"code": code}
    )
    
    if result.success:
        click.echo(result.output)
    else:
        click.echo(f"Error: {result.error}", err=True)

if __name__ == '__main__':
    cli()


4. CUSTOM WORKFLOW COMPOSITION
==============================
from crew_setup import CrewWorkflow, RoutingStrategy
from tasks import TaskType

crew = CrewWorkflow(routing_strategy=RoutingStrategy.DIRECT)

def analyze_code(code):
    '''Multi-step code analysis workflow.'''
    
    # Step 1: Debug
    debug_result = crew.execute_task(
        TaskType.DEBUG,
        {"code": code}
    )
    
    if not debug_result.success:
        return {"error": debug_result.error}
    
    # Step 2: Explain (if no critical errors)
    if "error" not in debug_result.output.lower():
        explain_result = crew.execute_task(
            TaskType.EXPLAIN,
            {"code": code, "detail_level": "detailed"}
        )
        
        # Step 3: Generate tests
        test_result = crew.execute_task(
            TaskType.TEST,
            {"code": code, "coverage": "comprehensive"}
        )
        
        return {
            "debug": debug_result.output,
            "explain": explain_result.output if explain_result.success else None,
            "tests": test_result.output if test_result.success else None,
        }
    
    return {"debug": debug_result.output}


5. CUSTOM AGENT REGISTRATION
============================
from crew_setup import create_developer_crew
from base_agent import BaseAgent, AgentResult
from hf_llm import HuggingFaceLLM

class CustomAgent(BaseAgent):
    @property
    def role(self):
        return "Custom Specialist"
    
    @property
    def goal(self):
        return "Do custom task"
    
    def execute(self, context, **kwargs):
        # Custom implementation
        return AgentResult(
            success=True,
            output="Custom output",
        )

crew = create_developer_crew()
crew.register_custom_agent("custom", CustomAgent(crew.llm))

# Use custom agent
from tasks import TaskFactory
custom_task = TaskFactory.create_custom_task(
    name="Custom Task",
    description="Run custom agent",
    required_params=["input"],
    default_params={},
    expected_output="Custom output",
    target_agent="custom",
)
crew.register_custom_task("custom_task", custom_task)


6. CONDITIONAL ROUTING
======================
from crew_setup import CrewWorkflow
from tasks import TaskType

crew = CrewWorkflow()

# Custom router function
def intelligent_router(task_def, params):
    code = params.get("code", "")
    
    # Route based on code characteristics
    if "class " in code and "def " in code:
        return "explain"  # Complex code → explain
    elif len(code) > 1000:
        return "debug"  # Large code → debug
    else:
        return task_def.default_agent

crew.router.set_custom_router(intelligent_router)

result = crew.execute_task(TaskType.DEBUG, {"code": large_code})
"""

# =============================================================================
# ARCHITECTURE OVERVIEW
# =============================================================================

"""
┌─────────────────────────────────────────────────────────────────┐
│                    CrewWorkflow (Orchestrator)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │AgentRegistry │  │TaskRegistry  │  │TaskRouter    │         │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤         │
│  │·completion   │  │·completion   │  │·direct       │         │
│  │·debug        │  │·debug        │  │·conditional  │         │
│  │·explain      │  │·explain      │  │·custom       │         │
│  │·test         │  │·test         │  └──────────────┘         │
│  │·custom       │  │·custom       │                             │
│  └──────────────┘  └──────────────┘                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Task Execution Pipeline             │
        ├───────────────────────────────────────┤
        │ 1. Validate parameters (TaskValidator)│
        │ 2. Enrich with defaults               │
        │ 3. Run preprocessing (optional)       │
        │ 4. Route to agent (TaskRouter)        │
        │ 5. Execute agent                      │
        │ 6. Run postprocessing (optional)      │
        │ 7. Return AgentResult                 │
        └───────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
      ┌──────────┐   ┌──────────┐   ┌──────────┐
      │Completion│   │  Debug   │   │ Explain  │
      │ Agent    │   │ Agent    │   │ Agent    │
      └──────────┘   └──────────┘   └──────────┘
            │               │               │
            └───────────────┼───────────────┘
                            ▼
                ┌──────────────────────────┐
                │  AST Parser & Tools      │
                │  Bug Detector & Context  │
                │  Extractor               │
                └──────────────────────────┘
"""

# =============================================================================
# CONFIGURATION PATTERNS
# =============================================================================

"""
PATTERN 1: SIMPLE SETUP
=======================
from crew_setup import create_developer_crew

crew = create_developer_crew()  # Uses defaults

PATTERN 2: CUSTOM CONFIG
========================
from crew_setup import WorkflowConfig, RoutingStrategy

config = WorkflowConfig(
    name="MyAssistant",
    routing_strategy=RoutingStrategy.DIRECT,
    llm_config={
        "max_retries": 5,
        "retry_delay": 2.0,
    }
)
crew = config.create_workflow()

PATTERN 3: ADVANCED SETUP
==========================
from crew_setup import CrewWorkflow, RoutingStrategy
from hf_llm import HuggingFaceLLM

llm = HuggingFaceLLM(max_retries=10)
crew = CrewWorkflow(
    llm=llm,
    routing_strategy=RoutingStrategy.CONDITIONAL
)

# Add custom routing
crew.add_routing_rule(
    TaskType.DEBUG,
    "custom_debug_agent",
    condition=lambda p: len(p['code']) > 500
)
"""

# =============================================================================
# TASK ROUTING MATRIX
# =============================================================================

"""
Default Task → Agent Mapping:

TASK TYPE      | DEFAULT AGENT | PARAMETERS          | OUTPUT
­­­­­­­­─────────────|───────────────|──────────────────────|──────────────────
COMPLETION     | completion    | code, line_number    | Code completion
               |               | max_tokens, temp     |
─────────────────────────────────────────────────────────────────────────────
DEBUG          | debug         | code                 | Bug analysis +
               |               | line_number (opt)    | fix suggestions
─────────────────────────────────────────────────────────────────────────────
EXPLAIN        | explain       | code                 | Code explanation
               |               | line_number (opt)    | + structure info
               |               | detail_level         |
─────────────────────────────────────────────────────────────────────────────
TEST           | test          | code                 | Test code with
               |               | line_number (opt)    | test cases
               |               | test_framework       |
               |               | coverage             |
"""
