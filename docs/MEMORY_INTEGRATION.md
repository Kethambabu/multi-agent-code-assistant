"""
MEMORY INTEGRATION GUIDE

Complete documentation of how the memory system integrates with agents,
workflow, and task execution for context-aware development assistance.
"""

# ============================================================================
# TABLE OF CONTENTS
# ============================================================================

1. Architecture Overview
2. Memory Store Components
3. Agent Memory Integration
4. Task Execution Flow
5. Workflow Memory Management
6. Memory Context for Agents
7. Usage Patterns
8. Best Practices
9. Performance Considerations
10. Troubleshooting


# ============================================================================
# 1. ARCHITECTURE OVERVIEW
# ============================================================================

## System Layers with Memory

    ┌─────────────────────────────────────────┐
    │  User/Application Layer                 │
    │  (execute_task, run_agent, etc.)        │
    └──────────────┬──────────────────────────┘
                   │
    ┌──────────────▼──────────────────────────┐
    │  CrewWorkflow (Orchestration)           │
    │  - Memory initialization & management   │
    │  - Task execution with memory updates   │
    │  - Error tracking                       │
    └──────────────┬──────────────────────────┘
                   │
    ┌──────────────▼──────────────────────────┐
    │  Task Router & Agent Selection          │
    │  - Route to appropriate agent           │
    │  - Inject memory context                │
    └──────────────┬──────────────────────────┘
                   │
    ┌──────────────▼──────────────────────────┐
    │  Individual Agents (with Memory)        │
    │  - CompletionAgent                      │
    │  - DebugAgent                           │
    │  - ExplainAgent                         │
    │  - TestAgent                            │
    │  - MemoryContext parameter for all      │
    └──────────────┬──────────────────────────┘
                   │
    ┌──────────────▼──────────────────────────┐
    │  MemoryStore (Persistent State)         │
    │  - Code snapshots (versioning)          │
    │  - Response history (FIFO deque)        │
    │  - Error tracking                       │
    │  - Context metadata                     │
    └─────────────────────────────────────────┘


## Data Flow: Task Execution with Memory

    Task Request (with code)
            ↓
    CrewWorkflow.execute_task()
    - Validate task
    - Update memory with code (code snapshot)
    - Enrich parameters (add defaults)
    - Create MemoryContext (read-only wrapper)
    - Add memory_context to parameters
            ↓
    TaskRouter.route()
    - Select appropriate agent
            ↓
    Agent.execute(..., memory_context=MemoryContext)
    - Access memory for context (recent responses, errors, history)
    - Include memory context in prompts if needed
    - Generate response with LLM
            ↓
    Store Response & Metadata
    - Store successful response in memory
    - Track agent name, task type, metadata
    - Update statistics
            ↓
    Store Error (if failed)
    - Store error message in memory
    - Track error type and agent
    - Update error statistics
            ↓
    Return AgentResult to user
    - success flag
    - output (completion, explanation, etc.)
    - metadata (including used_memory flag)
    - error message (if failed)


# ============================================================================
# 2. MEMORY STORE COMPONENTS
# ============================================================================

## MemoryEntry Dataclass

    Fields:
    - timestamp: datetime
      When the entry was created
    - entry_type: str
      'response', 'error', 'context', 'metadata'
    - content: str
      The actual content (response text, error message, etc.)
    - metadata: Dict[str, Any]
      Additional info (agent_name, task_type, line_number, etc.)

    Example creation:
    MemoryEntry(
        timestamp=datetime.now(),
        entry_type='response',
        content='def calculate(): return 42',
        metadata={'agent': 'CompletionAgent', 'task': 'completion'}
    )


## CodeSnapshot Dataclass

    Fields:
    - code: str
      The actual source code
    - timestamp: datetime
      When snapshot was created
    - version: int
      Version number (1, 2, 3, ...)
    - description: str
      Optional description of changes

    Example creation:
    CodeSnapshot(
        code='def foo():\n    pass',
        timestamp=datetime.now(),
        version=1,
        description='Initial function definition'
    )


## MemoryStore Class

    Constructor:
    MemoryStore(
        max_history: int = 100,
        max_snapshots: int = 10
    )

    Key Methods:

    1. update_code(code: str, line_number: int = 0, description: str = '')
       Purpose: Store code snapshot and update current code
       Returns: Version number
       Effect: Creates new CodeSnapshot if code changed
       Memory: Deque stores up to max_snapshots versions

    2. store_response(agent_name: str, response: str, task_type: str, 
                      metadata: Dict = None)
       Purpose: Record agent response
       Returns: Entry ID (index)
       Effect: Adds MemoryEntry to response history
       Memory: Deque stores up to max_history entries

    3. store_error(error_message: str, agent_name: str, error_type: str)
       Purpose: Record error for analysis
       Returns: Entry ID
       Effect: Adds error MemoryEntry
       Memory: Separate tracking, included in history

    4. store_context(context_data: Dict, description: str = '')
       Purpose: Store context metadata
       Returns: Entry ID
       Effect: Stores contextual information
       Usage: Before/after values, intermediate state

    5. get_context(include_code: bool = True, include_history: int = 5,
                   include_recent_errors: bool = False) -> Dict
       Purpose: Main retrieval API for agents
       Returns: {
           'current_code': str,
           'current_line': int,
           'metadata': dict,
           'recent_history': list[dict],
           'recent_errors': list[dict] (if requested)
       }

    6. get_recent_responses(agent_name: str = None, 
                           limit: int = 5) -> List[Dict]
       Purpose: Get recent responses optionally filtered by agent
       Returns: List of response dicts with agent, response, timestamp

    7. get_code_history() -> List[Dict]
       Purpose: Get all code versions
       Returns: List of code snapshots with version numbers

    8. get_statistics() -> Dict
       Purpose: Get memory usage statistics
       Returns: {
           'total_entries': int,
           'responses_generated': int,
           'errors_encountered': int,
           'code_changes': int,
           'max_history': int,
           'max_snapshots': int
       }

    9. export_memory() -> Dict
       Purpose: Complete serializable state
       Returns: JSON-ready dict with all entries, snapshots, stats

    10. get_details() -> Dict
        Purpose: Get raw access to internal state
        Returns: {
            'memory': list of all MemoryEntry objects,
            'code_snapshots': list of CodeSnapshot objects,
            'errors': filtered error entries,
            'responses': filtered response entries,
            'metadata': statistics and configuration
        }


## MemoryContext Class

    Purpose: Read-only wrapper preventing agents from modifying memory directly

    Constructor:
    MemoryContext(memory_store: MemoryStore)

    Methods (all read-only):
    - get_current_code() -> str
    - get_recent_responses(agent_name: str = None, limit: int = 5) -> List
    - get_context(include_history: int = 5) -> Dict
    - get_statistics() -> Dict
    - get_details() -> Dict

    Design Principle:
    - Agents receive MemoryContext, not MemoryStore
    - Prevents accidental memory corruption
    - All operations are read-only queries
    - Memory updates happen through CrewWorkflow


# ============================================================================
# 3. AGENT MEMORY INTEGRATION
# ============================================================================

## Updated Agent Signatures

    All agents now accept optional memory_context parameter:

    def execute(self, code: str, ..., memory_context=None, **kwargs)

    Agents that have been updated:
    1. CompletionAgent
    2. DebugAgent
    3. ExplainAgent
    4. TestAgent


## CompletionAgent with Memory

    Usage:
    completion_agent.execute(
        code=source_code,
        line_number=10,
        max_tokens=150,
        temperature=0.5,
        memory_context=memory_ctx
    )

    Memory Integration:
    - Retrieves recent completions from memory
    - Includes completion history in prompt
    - Adds context from previous similar requests
    - Tracks used_memory flag in metadata

    Behavior:
    ```python
    if memory_context:
        recent_responses = memory_context.get_recent_responses(
            agent_name="CompletionAgent",
            limit=2,
        )
        if recent_responses:
            recent = "\n".join([
                f"# Previous: {r['response'][:60]}..." 
                for r in recent_responses
            ])
            prompt = f"{recent}\n\n{prompt}"
    ```


## DebugAgent with Memory

    Usage:
    debug_agent.execute(
        code=source_code,
        line_number=None,
        memory_context=memory_ctx
    )

    Memory Integration:
    - Checks past errors for patterns
    - Enriches analysis with error history
    - Avoids repeated error messages
    - Tracks error patterns across session

    Behavior:
    ```python
    if memory_context:
        past_errors = memory_context.get_details()["errors"]
        if past_errors:
            analysis += f"\nPrevious errors: {len(past_errors)}"
    ```


## ExplainAgent with Memory

    Usage:
    explain_agent.execute(
        code=source_code,
        line_number=10,
        detail_level="medium",
        memory_context=memory_ctx
    )

    Memory Integration:
    - Checks if code already explained
    - References previous explanations
    - Adds continuity to explanations
    - Tracks explanation context

    Behavior:
    ```python
    if memory_context:
        recent = memory_context.get_recent_responses(
            agent_name="ExplainAgent",
            limit=1,
        )
        if recent:
            explanation += "\n[Previous context available]"
    ```


## TestAgent with Memory

    Usage:
    test_agent.execute(
        code=source_code,
        line_number=None,
        test_framework="pytest",
        coverage="comprehensive",
        memory_context=memory_ctx
    )

    Memory Integration:
    - Checks code change history
    - Adds notes about session progress
    - References previous test patterns
    - Tracks test coverage across versions

    Behavior:
    ```python
    if memory_context:
        stats = memory_context.get_details()
        changes = stats['metadata']['code_changes']
        tests += f"\n# {changes} code changes tracked"
    ```


# ============================================================================
# 4. TASK EXECUTION FLOW
# ============================================================================

## Step-by-Step Execution with Memory

    1. Task Request
       workflow.execute_task({
           "task_type": TaskType.COMPLETION,
           "code": source_code,
           "line_number": 10,
           "max_tokens": 256
       })

    2. Validate Task
       TaskValidator.validate(task_def, params)
       - Check required parameters present
       - Verify parameter types
       - Confirm task_type is valid

    3. Update Memory with Code
       workflow.memory.update_code(
           code=params["code"],
           line_number=params.get("line_number", 0)
       )
       - Creates CodeSnapshot if code changed
       - Updates current_line
       - Increments version number

    4. Enrich Parameters
       enriched_params = TaskValidator.enrich_params(task_def, params)
       - Adds default values for missing params
       - Maintains required fields
       - Example: max_tokens=150 (default)

    5. Create MemoryContext
       memory_context = MemoryContext(workflow.memory)
       - Read-only wrapper to memory
       - Prevents agents from modifying state
       - Provides query interface

    6. Inject Memory into Parameters
       enriched_params["memory_context"] = memory_context
       - Memory passed as keyword argument
       - All agents receive same interface
       - Optional: agents can ignore

    7. Route to Agent
       agent_name = workflow.router.route(task_def, enriched_params)
       agent = workflow.agent_registry.get(agent_name)
       - Select appropriate agent for task
       - Match task_type to agent role

    8. Execute Agent
       result = agent.execute("", **enriched_params)
       - Call agent.execute() with all parameters
       - Memory context available as kwarg
       - Agent generates response with optional memory

    9. Store Response
       if result.success:
           workflow.memory.store_response(
               agent_name=agent_name,
               response=result.output,
               task_type=task_def.task_type.value,
               metadata=result.metadata
           )
       - Record successful output
       - Track agent name and task type
       - Store execution metadata

    10. Store Error
        if not result.success:
            workflow.memory.store_error(
                error_message=result.error,
                agent_name=agent_name,
                error_type=task_def.task_type.value
            )
        - Track failed execution
        - Store error message
        - Record error context

    11. Postprocess
        if task_def.postprocess and result.success:
            result.output = task_def.postprocess(result.output)
        - Apply optional post-processing
        - Format output as needed

    12. Return Result
        return result
        - AgentResult with success, output, metadata, error


# ============================================================================
# 5. WORKFLOW MEMORY MANAGEMENT
# ============================================================================

## CrewWorkflow Memory Integration

    Initialization:
    workflow = CrewWorkflow(
        max_memory_entries=100,   # FIFO history size
        config=WorkflowConfig()   # Optional config
    )

    Constructor creates:
    - self.memory = MemoryStore(max_history=max_memory_entries)
    - Available to all agents during task execution


## Memory Lifecycle

    1. Initialization
       - Create MemoryStore with max_history and max_snapshots
       - Initialize empty deques
       - Set up statistics tracking

    2. Code Updates (per task)
       - update_code() called before routing
       - Creates CodeSnapshot if code changed
       - Maintains version history
       - Updates current_line for context

    3. Agent Execution
       - MemoryContext created
       - Passed to agent.execute()
       - Agent reads but doesn't modify
       - Agent may reference historical data

    4. Response Storage
       - Successful responses stored
       - Agent name tracked for filtering
       - Task type recorded
       - Metadata includes execution details

    5. Error Tracking
       - Failed executions stored as errors
       - Error messages captured
       - Error type and agent recorded
       - Can be queried for patterns

    6. Memory Export
       - Complete state serializable to dict
       - Can be saved to JSON
       - Can be analyzed post-execution
       - Can be used for logging

    7. Cleanup (optional)
       - Memory is in-process (not persistent by default)
       - Clears on process exit
       - Can implement save_to_file() manually


## Memory Boundaries

    Per-Agent Memory:
    - Agents can read: recent responses (specific agent only)
    - Agents cannot: modify, delete, or corrupt memory
    - Isolation: agent A doesn't modify what agent B sees

    Per-Task Memory:
    - Code snapshot created/updated
    - Response stored with task type
    - Error recorded with task context
    - All tasks share same MemoryStore

    Session Memory:
    - All tasks in one workflow share memory
    - Multiple workflows = separate memories
    - No cross-workflow memory sharing
    - Memory is transient (process-scoped)


# ============================================================================
# 6. MEMORY CONTEXT FOR AGENTS
# ============================================================================

## MemoryContext API (Read-Only)

    agents receive MemoryContext, not MemoryStore

    Methods Available:

    1. get_current_code() -> str
       Returns: The current source code
       Usage: agent can read code being analyzed

    2. get_current_line() -> int
       Returns: Current line number
       Usage: agent aware of cursor position

    3. get_recent_responses(agent_name: str = None, limit: int = 5)
       Returns: List of recent responses
       Params:
       - agent_name: filter by specific agent (optional)
       - limit: number of responses to return
       Usage: agent references previous work

    4. get_context(include_history: int = 5)
       Returns: Dict with {
           current_code, current_line,
           metadata, recent_history
       }
       Usage: comprehensive context snapshot

    5. get_statistics() -> Dict
       Returns: {total_entries, responses_generated, errors, changes}
       Usage: agent aware of session progress

    6. get_details() -> Dict
       Returns: Detailed state dict
       Keys: 'memory', 'code_snapshots', 'errors', 'responses', 'metadata'
       Usage: full introspection (for advanced agents)


## Design Rationale

    Why Read-Only?
    Problem: Mutable memory can cause:
    - Agents corrupting shared state
    - Race conditions (concurrent agents)
    - Difficult debugging of memory issues
    - Uncertainty about state consistency

    Solution: MemoryContext
    - All methods are queries, not mutations
    - Agents cannot call update_code() or store_response()
    - Memory updates happen through CrewWorkflow
    - Separation of concerns: agents generate, workflow manages

    Why Optional?
    Problem: Not all tasks need memory
    Solution: memory_context=None
    - Agents check if memory_context provided
    - Gracefully degrade if no memory
    - Default behavior unchanged


## Agent Usage Patterns

## Pattern 1: Simple Reference
    ```python
    if memory_context:
        stats = memory_context.get_statistics()
        print(f"Session: {stats['total_entries']} entries")
    ```

    ## Pattern 2: Context-Aware Prompt
    ```python
    prompt = default_prompt
    if memory_context:
        recent = memory_context.get_recent_responses(
            agent_name="CompletionAgent",
            limit=3
        )
        if recent:
            context = format_recent(recent)
            prompt = f"{context}\n\n{prompt}"
    ```

    ## Pattern 3: Error Pattern Detection
    ```python
    if memory_context:
        details = memory_context.get_details()
        error_patterns = group_errors(details['errors'])
        if error_patterns:
            add_error_handling_to_prompt(prompt, error_patterns)
    ```

    ## Pattern 4: Code History Analysis
    ```python
    if memory_context:
        history = memory_context.get_code_history()
        changes = analyze_changes(history)
        if significant_changes:
            increase_test_coverage()
    ```


# ============================================================================
# 7. USAGE PATTERNS
# ============================================================================

## Pattern 1: Simple Single Task with Memory

    workflow = CrewWorkflow()
    
    result = workflow.execute_task({
        "task_type": TaskType.COMPLETION,
        "code": my_code,
        "line_number": 10,
    })
    
    # Memory automatically:
    # - Updated with code
    # - Provided to agent as context
    # - Populated with response


## Pattern 2: Multi-Step Workflow

    workflow = CrewWorkflow(max_memory_entries=200)
    
    # Step 1: Complete code
    result1 = workflow.execute_task({
        "task_type": TaskType.COMPLETION,
        "code": incomplete_code,
        "line_number": 15,
    })
    
    # Step 2: Debug completed code (uses memory from step 1)
    result2 = workflow.execute_task({
        "task_type": TaskType.DEBUG,
        "code": result1.output,
    })
    
    # Step 3: Explain fixed code (aware of both previous steps)
    result3 = workflow.execute_task({
        "task_type": TaskType.EXPLAIN,
        "code": result2.output,
        "detail_level": "detailed"
    })


## Pattern 3: Memory Inspection

    workflow = CrewWorkflow()
    
    # Execute tasks...
    
    # Query memory
    context = workflow.memory.get_context(include_history=10)
    print(f"Code versions: {len(workflow.memory.get_code_history())}")
    print(f"Responses: {len(context['recent_history'])}")
    
    stats = workflow.memory.get_statistics()
    print(f"Total: {stats['total_entries']} entries")


## Pattern 4: Conditional Logic Based on Memory

    workflow = CrewWorkflow()
    
    # Execute task
    result = workflow.execute_task({
        "task_type": TaskType.DEBUG,
        "code": code,
    })
    
    # Check memory for patterns
    stats = workflow.memory.get_statistics()
    if stats['errors_encountered'] > 5:
        # Too many errors, use different strategy
        workflow.router.add_routing_rule(...)


## Pattern 5: Export for Analysis

    workflow = CrewWorkflow()
    
    # Execute many tasks...
    
    # Export entire memory state
    export = workflow.memory.export_memory()
    
    # Save to file
    import json
    with open("session_memory.json", "w") as f:
        json.dump(export, f, indent=2, default=str)


# ============================================================================
# 8. BEST PRACTICES
# ============================================================================

## Memory Configuration

    For short sessions (< 10 tasks):
    workflow = CrewWorkflow(max_memory_entries=50)

    For typical sessions (10-100 tasks):
    workflow = CrewWorkflow(max_memory_entries=200)

    For long sessions (100+ tasks):
    workflow = CrewWorkflow(max_memory_entries=500)

    For minimal memory usage:
    workflow = CrewWorkflow(max_memory_entries=20)


## Agent Best Practices

    1. Always check if memory_context is not None
    2. Use memory for context, not control logic
    3. Gracefully degrade if memory unavailable
    4. Don't assume specific agents in memory
    5. Keep memory queries efficient (limit parameter)

    Example:
    ```python
    def execute(self, code: str, memory_context=None, **kwargs):
        # Good: optional memory usage
        recent_context = ""
        if memory_context:
            recent = memory_context.get_recent_responses(limit=3)
            if recent:
                recent_context = format_responses(recent)
        
        prompt = build_prompt(code)
        if recent_context:
            prompt = f"{recent_context}\n\n{prompt}"
        
        return self.llm.generate(prompt)
    ```


## Workflow Best Practices

    1. Create one workflow per session/user
    2. Reuse workflow for multiple related tasks
    3. Monitor statistics for anomalies
    4. Export memory before major state changes
    5. Consider error patterns for routing decisions

    Example:
    ```python
    class DeveloperSession:
        def __init__(self):
            self.workflow = CrewWorkflow()
            self.start_time = datetime.now()
        
        def execute_task(self, task_data):
            result = self.workflow.execute_task(task_data)
            stats = self.workflow.memory.get_statistics()
            
            if stats['errors_encountered'] > 10:
                self.log_warning("High error rate")
            
            return result
    ```


## Testing Best Practices

    1. Create separate CrewWorkflow per test
    2. Verify memory state after tasks
    3. Check metadata for used_memory flag
    4. Validate code snapshots for changes
    5. Assert error tracking works

    Example:
    ```python
    def test_completion_with_memory():
        workflow = CrewWorkflow(max_memory_entries=100)
        
        result = workflow.execute_task({
            "task_type": TaskType.COMPLETION,
            "code": test_code,
            "line_number": 5,
        })
        
        assert result.success
        assert result.metadata['used_memory']
        assert workflow.memory.get_statistics()['total_entries'] > 0
    ```


# ============================================================================
# 9. PERFORMANCE CONSIDERATIONS
# ============================================================================

## Memory Usage

    Per Entry (MemoryEntry):
    - timestamp: ~50 bytes
    - entry_type: ~20 bytes (string)
    - content: variable (response text)
    - metadata: variable (dict)
    Typical per-entry: 500 bytes - 2 KB

    Per CodeSnapshot:
    - code: variable (source code)
    - timestamp: ~50 bytes
    - version: ~20 bytes
    - description: variable
    Typical per-snapshot: 1 KB - 50 KB

    Total Memory Estimate (100 entries, 10 snapshots):
    - 100 entries × 1 KB = ~100 KB
    - 10 snapshots × 5 KB = ~50 KB
    - Overhead: ~10 KB
    - Total: ~160 KB

    With max_memory_entries=500:
    - Estimated: ~800 KB (entries) + 50 KB (snapshots) + overhead


## Performance Tips

    1. Use max_memory_entries appropriate to task
    2. Clear memory if not needed (create new workflow)
    3. Query memory efficiently (use limits)
    4. Don't export memory frequently
    5. Monitor memory statistics

    Example throttling:
    ```python
    stats = workflow.memory.get_statistics()
    if stats['total_entries'] > workflow.memory.max_history * 0.9:
        # Memory near full, consider archiving
        export = workflow.memory.export_memory()
        save_to_archive(export)
        workflow = CrewWorkflow()  # Fresh memory
    ```


## Query Performance

    Fast Queries (O(1) or O(n < 100)):
    - get_current_code()
    - get_statistics()
    - get_recent_responses(limit=5)

    Slower Queries (O(all_entries)):
    - get_code_history()
    - export_memory()
    - get_details()

    Optimization:
    ```python
    # Good: limited history
    recent = memory_context.get_recent_responses(limit=5)
    
    # Expensive: all responses
    all_responses = memory_context.get_recent_responses(limit=None)
    ```


# ============================================================================
# 10. TROUBLESHOOTING
# ============================================================================

## Issue: Memory not used by agent

    Symptom: used_memory=False in metadata

    Causes:
    1. memory_context=None not passed (check workflow)
    2. Agent doesn't check memory_context
    3. Agent always passes memory_context=None

    Solutions:
    1. Verify workflow.execute_task passes memory
    2. Check agent.execute() for memory_context parameter
    3. Review agent code for "if memory_context:" checks
    4. Add logging to verify memory injection

    Debug:
    ```python
    # Add logging in agent
    def execute(self, code, memory_context=None, **kwargs):
        if memory_context:
            print(f"Memory available: {memory_context}")
        else:
            print("WARNING: No memory context provided")
    ```


## Issue: Memory grows too large

    Symptom: Slow performance, high memory usage

    Causes:
    1. max_memory_entries too large
    2. Tasks generating large responses
    3. Code snapshots accumulating
    4. Long-running session

    Solutions:
    1. Reduce max_memory_entries
    2. Export and clear memory periodically
    3. Monitor statistics regularly
    4. Create new workflow for new session


## Issue: Code snapshots not created

    Symptom: get_code_history() returns empty or stale

    Causes:
    1. Code not actually changing (identical strings)
    2. update_code() not called
    3. Snapshots deleted (FIFO overflow)

    Solutions:
    1. Verify code is different (use diff)
    2. Check workflow._execute_task_def calls update_code
    3. Increase max_snapshots
    4. Export memory before overflow


## Issue: Errors not tracked properly

    Symptom: Error statistics wrong or empty

    Causes:
    1. AgentResult.success always True
    2. store_error() not called on failure
    3. Error entries filtered out in queries

    Solutions:
    1. Agent must return failure AgentResult
    2. Verify _execute_task_def calls store_error
    3. Use get_details() to see all entries unfiltered
    4. Check error_type matches stored errors


## Common Patterns to Verify

    1. Code Updates
    ```python
    stats_before = workflow.memory.get_statistics()
    workflow.execute_task({"code": new_code})
    stats_after = workflow.memory.get_statistics()
    assert stats_after['code_changes'] > stats_before['code_changes']
    ```

    2. Response Storage
    ```python
    result = workflow.execute_task(task)
    if result.success:
        responses = workflow.memory.get_recent_responses()
        assert len(responses) > 0
    ```

    3. Error Tracking
    ```python
    result = workflow.execute_task(bad_task)
    if not result.success:
        details = workflow.memory.get_details()
        assert len(details['errors']) > 0
    ```

    4. Memory Context Access
    ```python
    memory_ctx = MemoryContext(workflow.memory)
    assert memory_ctx.get_current_code() is not None
    assert memory_ctx.get_statistics() is not None
    ```


# ============================================================================
# APPENDIX: COMPLETE WORKFLOW EXAMPLE
# ============================================================================

from crew_setup import CrewWorkflow
from tasks import TaskType

# Initialize
workflow = CrewWorkflow(max_memory_entries=200)

# Task 1: Complete partial code
task1_result = workflow.execute_task({
    "task_type": TaskType.COMPLETION,
    "code": "def fibonacci(n):\n    if n <= 1:",
    "line_number": 2,
})

# Memory now has: code snapshot v1, response from CompletionAgent

# Task 2: Debug the completed code
task2_result = workflow.execute_task({
    "task_type": TaskType.DEBUG,
    "code": task1_result.output,
})

# Memory now has: code snapshot v2, response from DebugAgent, with access to v1

# Task 3: Explain the function
task3_result = workflow.execute_task({
    "task_type": TaskType.EXPLAIN,
    "code": task1_result.output,
    "detail_level": "detailed"
})

# Memory now has: all previous entries plus explanation

# Inspect memory
stats = workflow.memory.get_statistics()
print(f"Session: {stats['total_entries']} entries, "
      f"{stats['responses_generated']} responses, "
      f"{stats['code_changes']} code versions")

# Export
export = workflow.memory.export_memory()
# export can be saved to JSON, analyzed, etc.

# Next workflow for next session (fresh memory)
workflow2 = CrewWorkflow()
# workflow2.memory is completely separate from workflow.memory
