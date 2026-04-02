"""
TRIGGER ENGINE GUIDE

Complete documentation for event-driven code analysis triggers.
Detects user actions and code changes, routes to appropriate agents.
"""

# ============================================================================
# TABLE OF CONTENTS
# ============================================================================

1. Architecture Overview
2. Event Types
3. Trigger Detection
4. Event Routing
5. Queue Management
6. Configuration
7. Integration Patterns
8. Performance Considerations
9. Usage Examples
10. Best Practices


# ============================================================================
# 1. ARCHITECTURE OVERVIEW
# ============================================================================

## Design Principles

### Event-Driven
- Code changes trigger events
- Events route to agents asynchronously
- No direct coupling between detection and handling

### Fast & Responsive
- Minimal latency for event detection
- Non-blocking event processing
- Debouncing prevents redundant work

### Loosely Coupled
- Agents don't know about trigger engine
- Trigger engine doesn't import agents
- Communication through events and routing

### Thread-Safe
- RLock for concurrent access
- Timer-based debouncing
- Thread-safe queue operations


## System Flow

    User Types Code
         ↓
    TriggerEngine.detect_event()
         ↓
    Check: Typing Pause / Syntax Error / Error Cleared
         ↓
    Emit Event (if detected)
         ↓
    TriggerEngine.route_to_agent()
         ↓
    Select Agent (CompletionAgent, DebugAgent, etc.)
         ↓
    Return RoutingResult with Parameters
         ↓
    CrewWorkflow executes agent
         ↓
    Response returned to user


## Component Interactions

TriggerEngine
├── Event Detection
│   ├── _detect_typing_pause() - User inactivity
│   ├── _detect_syntax_error() - Code quality issues
│   └── _detect_error_cleared() - Problems fixed
│
├── Event Routing
│   ├── route_to_agent() - Main routing logic
│   ├── add_routing_rule() - Custom rules
│   └── _select_agent() - Agent selection
│
├── Event Queue
│   ├── emit_event() - Add to queue
│   ├── get_events() - Retrieve events
│   └── clear_queue() - Clear queue
│
└── Subscriptions
    └── subscribe() - Event listeners


# ============================================================================
# 2. EVENT TYPES
# ============================================================================

## EventType Enum

```python
class EventType(Enum):
    TYPING_PAUSE = "typing_pause"        # User stopped typing (N seconds)
    SYNTAX_ERROR = "syntax_error"        # Code has syntax issues
    CODE_CHANGE = "code_change"          # Code modified
    ERROR_CLEARED = "error_cleared"      # Errors were fixed
    MULTIPLE_ERRORS = "multiple_errors"  # Many errors detected (>3)
```

## Event Structure

```python
@dataclass
class Event:
    event_type: EventType              # What happened
    code: str                          # Source code
    timestamp: float                   # When it happened
    line_number: int = 0               # Cursor position
    priority: TriggerPriority          # How urgent
    metadata: Dict[str, Any]           # Event-specific data
    source_agent: Optional[str]        # Which agent generated (if any)
```

## Event-to-Agent Mapping

| Event | Default Agent | Triggered By | Priority |
|-------|---------------|--------------|----------|
| TYPING_PAUSE | CompletionAgent | 1+ second inactivity | NORMAL |
| SYNTAX_ERROR | DebugAgent | Syntax errors detected | HIGH |
| MULTIPLE_ERRORS | DebugAgent | 3+ errors | CRITICAL |
| ERROR_CLEARED | (none) | All errors fixed | NORMAL |
| CODE_CHANGE | (none, cached) | Any code modification | LOW |


## Event Metadata Examples

### TYPING_PAUSE
```python
metadata = {
    "debounce_duration": 1.0,
    "lines_changed": 5,
    "time_since_change": 1.05
}
```

### SYNTAX_ERROR
```python
metadata = {
    "error_count": 2,
    "errors": [BugReport(...), ...],
    "lines": [5, 12]
}
```

### MULTIPLE_ERRORS
```python
metadata = {
    "error_count": 7,
    "errors": [BugReport(...), ...],
    "lines": [3, 5, 8, 12, 15, 20, 25]
}
```

### ERROR_CLEARED
```python
metadata = {
    "previously_had": 3,
    "now_have": 0
}
```


# ============================================================================
# 3. TRIGGER DETECTION
# ============================================================================

## Typing Pause Detection

Purpose: Trigger completion when user pauses typing

Mechanism:
1. Track last change timestamp
2. When code changes, schedule timer
3. If no changes for N seconds, emit TYPING_PAUSE
4. Debouncing prevents multiple events

```python
engine = TriggerEngine(typing_pause_duration=1.0)

code = "def hello():\n    "

# t=0: User types
event = engine.detect_event(code, line_number=2)
# Returns None (waiting for pause)

# t=1.1: User hasn't typed for 1+ second
event = engine.detect_event(code, line_number=2)
# Returns TYPING_PAUSE event
```

Configuration:
```python
# Very responsive (0.3 seconds)
engine = TriggerEngine(typing_pause_duration=0.3)

# Relaxed (2 seconds)
engine = TriggerEngine(typing_pause_duration=2.0)
```

## Syntax Error Detection

Purpose: Immediately alert on errors

Mechanism:
1. Run bug_detector.detect_syntax_errors()
2. Compare error count to previous
3. Emit SYNTAX_ERROR if changed
4. Emit MULTIPLE_ERRORS if count > 3
5. Debounce syntax checks (prevent cpu overload)

```python
engine = TriggerEngine(syntax_check_debounce=0.5)

code = "def foo(\n    pass"

event = engine.detect_event(code)
# Returns SYNTAX_ERROR with metadata:
# {
#   "error_count": 2,
#   "errors": [...],
#   "lines": [1, 2]
# }
```

Debouncing:
```python
# Check syntax max once per 0.5 seconds
engine = TriggerEngine(syntax_check_debounce=0.5)

# More aggressive (check every 0.1 seconds)
engine = TriggerEngine(syntax_check_debounce=0.1)

# Relaxed (check every 2 seconds)
engine = TriggerEngine(syntax_check_debounce=2.0)
```

## Error Clearing Detection

Purpose: Confirm when errors are fixed

Mechanism:
1. Track previous error count
2. Detect when error count goes to 0
3. Emit ERROR_CLEARED event
4. Useful for confirmation/validation

```python
code_with_errors = "def foo(\n    pass"
code_fixed = "def foo():\n    pass"

# t=1: Errors detected
event1 = engine.detect_event(code_with_errors)
# Returns SYNTAX_ERROR

# t=2: Fix code
event2 = engine.detect_event(code_fixed)
# Returns ERROR_CLEARED
```


# ============================================================================
# 4. EVENT ROUTING
# ============================================================================

## Routing Result

```python
@dataclass
class RoutingResult:
    agent_type: str                    # completion, debug, explain, test
    agent_name: str                    # CompletionAgent, DebugAgent, etc.
    priority: TriggerPriority          # LOW, NORMAL, HIGH, CRITICAL
    should_execute: bool = True         # Execute or skip
    reason: str                        # Why routed
    suggested_params: Dict             # Parameters for agent
```

## Default Routing Rules

```python
# TYPING_PAUSE -> CompletionAgent (NORMAL)
event = Event(event_type=EventType.TYPING_PAUSE, ...)
result = engine.route_to_agent(event)
# result.agent_name == "CompletionAgent"

# SYNTAX_ERROR -> DebugAgent (HIGH)
event = Event(event_type=EventType.SYNTAX_ERROR, ...)
result = engine.route_to_agent(event)
# result.agent_name == "DebugAgent"
# result.priority == TriggerPriority.HIGH

# MULTIPLE_ERRORS -> DebugAgent (CRITICAL)
event = Event(event_type=EventType.MULTIPLE_ERRORS, ...)
result = engine.route_to_agent(event)
# result.agent_name == "DebugAgent"
# result.priority == TriggerPriority.CRITICAL

# ERROR_CLEARED -> (no routing)
event = Event(event_type=EventType.ERROR_CLEARED, ...)
result = engine.route_to_agent(event)
# result.should_execute == False
```

## Custom Routing Rules

Override default routing with conditions:

```python
engine = TriggerEngine()

# Route high error count to test agent instead
engine.add_routing_rule(
    event_type=EventType.MULTIPLE_ERRORS,
    condition=lambda e: e.metadata.get("error_count", 0) > 5,
    agent_type="test"
)

# Route typing pause only if near specific lines
engine.add_routing_rule(
    event_type=EventType.TYPING_PAUSE,
    condition=lambda e: e.line_number < 20,  # First 20 lines
    agent_type="completion"
)

# Never route syntax errors (ignore them)
engine.add_routing_rule(
    event_type=EventType.SYNTAX_ERROR,
    condition=lambda e: False,  # Never matches
    agent_type="none"
)
```

## Agent Parameters

Routing provides suggested parameters for agents:

```python
event = Event(
    event_type=EventType.SYNTAX_ERROR,
    code="def foo(\n    pass",
    line_number=1,
    metadata={"error_count": 2}
)

result = engine.route_to_agent(event)

# result.suggested_params contains:
{
    "code": "def foo(\n    pass",
    "line_number": 1,
    "source": "trigger_engine",
    "error_count": 2,
    "errors": [...],
    # ... other event-specific params
}
```

## Routing Priority

Priority determines execution order:

```python
# LOW - background work unnecessary
completion = RoutingResult(..., priority=TriggerPriority.LOW)

# NORMAL - regular async tasks
normal = RoutingResult(..., priority=TriggerPriority.NORMAL)

# HIGH - urgent, syntax errors
urgent = RoutingResult(..., priority=TriggerPriority.HIGH)

# CRITICAL - many errors, immediate action
critical = RoutingResult(..., priority=TriggerPriority.CRITICAL)
```


# ============================================================================
# 5. QUEUE MANAGEMENT
# ============================================================================

## Event Queue

Events are queued for processing:

```python
engine = TriggerEngine(max_events_in_queue=100)

# Emit multiple events
engine.emit_event(event1)  # Queued
engine.emit_event(event2)  # Queued
engine.emit_event(event3)  # Queued

# Get and process
events = engine.get_events(max_count=10)
for event in events:
    result = engine.route_to_agent(event)
    # execute agent
```

## Queue Behavior

FIFO (First In, First Out):
- Events processed in order received
- Prevents stale events from being processed first
- Maintains causality

Bounded Size:
```python
# Queue limited to 100 events
engine = TriggerEngine(max_events_in_queue=100)

# If 101st event emitted, oldest is dropped
# _dropped_count incremented
```

Overflow Handling:
```python
# Check if event was queued
success = engine.emit_event(large_event)
if not success:
    print("Queue full, event dropped")

# Monitor drops
stats = engine.get_statistics()
print(f"Dropped: {stats['dropped_events']}")
```

## Event Processing Pattern

```python
# Process loop
while True:
    events = engine.get_events(max_count=10)
    if not events:
        time.sleep(0.01)  # Short sleep
        continue
    
    for event in events:
        routing = engine.route_to_agent(event)
        if routing.should_execute:
            # Execute agent with suggested_params
            workflow.execute_task({
                "task_type": get_task_type(routing.agent_type),
                **routing.suggested_params
            })
```


# ============================================================================
# 6. CONFIGURATION
# ============================================================================

## Initialization Parameters

```python
engine = TriggerEngine(
    typing_pause_duration=1.0,      # Seconds before pause event
    max_events_in_queue=100,         # Queue size limit
    syntax_check_debounce=0.5        # Seconds between checks
)
```

## Recommended Configurations

### Responsive (Low Latency)
```python
engine = TriggerEngine(
    typing_pause_duration=0.3,       # Fast completion suggestions
    max_events_in_queue=50,          # Smaller queue pressure
    syntax_check_debounce=0.1        # Real-time error detection
)
```

### Balanced (Default)
```python
engine = TriggerEngine(
    typing_pause_duration=1.0,
    max_events_in_queue=100,
    syntax_check_debounce=0.5
)
```

### Relaxed (CPU Efficient)
```python
engine = TriggerEngine(
    typing_pause_duration=2.0,       # Less frequent completion
    max_events_in_queue=200,         # Larger queue capacity
    syntax_check_debounce=2.0        # Less frequent checks
)
```

## Dynamic Configuration

Adjust at runtime:

```python
engine.typing_pause_duration = 2.0  # Make pauses longer
engine.syntax_check_debounce = 1.0  # Check less frequently
engine.clear_queue()                 # Clear current queue
```


# ============================================================================
# 7. INTEGRATION PATTERNS
# ============================================================================

## Pattern 1: Simple Event Processing

```python
from trigger_engine import TriggerEngine
from crew_setup import CrewWorkflow
from tasks import TaskType

engine = TriggerEngine()
workflow = CrewWorkflow()

# On each editor keystroke/change:
def on_code_change(code, line_number):
    event = engine.detect_event(code, line_number=line_number)
    
    if event:
        routing = engine.route_to_agent(event)
        
        if routing.should_execute:
            # Map agent to task type
            task_type_map = {
                "completion": TaskType.COMPLETION,
                "debug": TaskType.DEBUG,
                "explain": TaskType.EXPLAIN,
                "test": TaskType.TEST,
            }
            
            result = workflow.execute_task({
                "task_type": task_type_map[routing.agent_type],
                **routing.suggested_params
            })
```

## Pattern 2: Async Processing

```python
import asyncio
from queue import Queue

event_queue = Queue()
engine = TriggerEngine()

# Detection thread
def detect_thread():
    while running:
        code = editor.get_current_code()
        event = engine.detect_event(code)
        if event:
            event_queue.put(event)

# Processing thread
async def process_thread():
    while running:
        event = event_queue.get(timeout=0.1)
        if not event:
            continue
        
        routing = engine.route_to_agent(event)
        await execute_agent_async(routing)

# Start both threads
detection_task = threading.Thread(target=detect_thread)
processing_task = asyncio.create_task(process_thread())
```

## Pattern 3: Event Subscription

```python
engine = TriggerEngine()

# Subscribe to alerts
def on_critical_errors(event):
    if event.metadata.get("error_count", 0) > 5:
        send_notification(f"Critical: {event.metadata['error_count']} errors")
        play_sound()

engine.subscribe(EventType.MULTIPLE_ERRORS, on_critical_errors)

# Subscribe to completions
def on_pause(event):
    print(f"Pause at line {event.line_number}, suggesting completion...")

engine.subscribe(EventType.TYPING_PAUSE, on_pause)
```

## Pattern 4: VS Code Extension Integration

```python
# VS Code extension using Language Server Protocol

class CodeTriggerServer:
    def __init__(self):
        self.engine = TriggerEngine()
        self.workflow = CrewWorkflow()
    
    def on_did_change(self, uri, changes):
        """Called when file changes."""
        code = get_file_content(uri)
        line = get_current_line(uri)
        
        event = self.engine.detect_event(code, line_number=line)
        
        if event:
            routing = self.engine.route_to_agent(event)
            
            # Send to client with diagnostic/hint
            self.send_diagnostic(uri, routing)
    
    def on_completion_request(self, uri, position):
        """Called on completion request."""
        code = get_file_content(uri)
        line = position.line
        
        routing = self.engine.route_to_agent(Event(
            event_type=EventType.TYPING_PAUSE,
            code=code,
            line_number=line
        ))
        
        # Get completion from agent
        result = self.workflow.execute_task({
            "task_type": TaskType.COMPLETION,
            **routing.suggested_params
        })
        
        return completion_items(result.output)
```


# ============================================================================
# 8. PERFORMANCE CONSIDERATIONS
# ============================================================================

## CPU Usage

- Syntax checking: O(n) where n = code length
- Non-blocking with configurable debounce
- Default: 0.5s between checks

Optimization:
```python
# Less frequent syntax checks
engine = TriggerEngine(syntax_check_debounce=2.0)

# Larger pause threshold
engine = TriggerEngine(typing_pause_duration=2.0)
```

## Memory Usage

Per Engine:
- Event queue: 100 events × ~1 KB = 100 KB
- State tracking: ~50 KB
- Subscriptions: ~10 KB
Total: ~160 KB per engine

Multiple Engines:
```python
# Per-file engines (not recommended)
engines = {file: TriggerEngine() for file in files}
# Total memory: files × 160 KB

# Single shared engine (recommended)
engine = TriggerEngine()
# Total memory: 160 KB
```

## Latency

Event Detection: <1ms (debounced)
Routing: <1ms (small rule set)
Queue Operations: <1ms

Total: <5ms from code change to routing result

## Throughput

- Event detection: 1000s per second (debounced)
- Routing: 1000s per second
- Queue FIFO: bounded by max_events_in_queue

Bottleneck: Agent execution (LLM latency ~500ms)


# ============================================================================
# 9. USAGE EXAMPLES
# ============================================================================

## Example 1: Basic Detection

```python
engine = TriggerEngine()

code = """
def fibonacci(n)
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""

# t=0: Code with error
event = engine.detect_event(code, line_number=2)
print(event.event_type)  # SYNTAX_ERROR

# t=1: Fix error
code_fixed = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""

event = engine.detect_event(code_fixed)
print(event.event_type)  # ERROR_CLEARED

# t=2: User pauses (after 1 second)
time.sleep(1.0)
event = engine.detect_event(code_fixed)
print(event.event_type)  # TYPING_PAUSE
```

## Example 2: Custom Routing

```python
engine = TriggerEngine()

# Route large error counts to test agent
engine.add_routing_rule(
    EventType.MULTIPLE_ERRORS,
    condition=lambda e: e.metadata.get("error_count", 0) >= 10,
    agent_type="test"
)

code_with_many_errors = "def f(\n" * 15 + "pass"

event = engine.detect_event(code_with_many_errors)
result = engine.route_to_agent(event)

print(result.agent_name)  # TestAgent
print(result.priority)    # TriggerPriority.CRITICAL
```

## Example 3: Event Queue Processing

```python
engine = TriggerEngine()

# Simulate multiple changes
codes = [
    # ... various code snippets
]

# Emit events
for code in codes:
    event = engine.detect_event(code)
    if event:
        engine.emit_event(event)

# Process queue
while True:
    events = engine.get_events(max_count=5)
    if not events:
        break
    
    for event in events:
        print(f"Processing: {event.event_type.value}")
```

## Example 4: Statistics and Monitoring

```python
engine = TriggerEngine()

# ... do work ...

stats = engine.get_statistics()

print(f"Total events: {stats['total_events']}")
print(f"Routed: {stats['routed_events']}")
print(f"Dropped: {stats['dropped_events']}")
print(f"Queued: {stats['queued_events']}")
print(f"Queue utilization: {stats['queued_events']}/{stats['queue_size']}")
```


# ============================================================================
# 10. BEST PRACTICES
# ============================================================================

## Do's

✅ Use one TriggerEngine per user/session
✅ Call detect_event() on every code change
✅ Process queue frequently (check every 100ms)
✅ Monitor statistics for anomalies
✅ Use custom routing for business logic
✅ Subscribe to events for logging
✅ Handle routing.should_execute flag

## Don'ts

❌ Create multiple engines (wastes memory)
❌ Process queue infrequently (events pile up)
❌ Ignore dropped events
❌ Block event processing thread
❌ Call agent directly (use routing)
❌ Modify Event objects after emission
❌ Assume all events should be routed

## Performance Tuning

```python
# Monitor latency
import time

start = time.time()
event = engine.detect_event(code, line)
latency_ms = (time.time() - start) * 1000

if latency_ms > 10:
    # Increase debounce
    engine.syntax_check_debounce *= 2

# Monitor queue
stats = engine.get_statistics()
if stats['queued_events'] > stats['queue_size'] * 0.8:
    # Process queue faster or increase size
    pass
```

## Error Handling

```python
try:
    event = engine.detect_event(code, line)
except Exception as e:
    # Syntax detection failed, continue
    logger.error(f"Trigger detection failed: {e}")

try:
    result = engine.route_to_agent(event)
except Exception as e:
    # Routing failed, skip
    logger.error(f"Routing failed: {e}")
    result = None

if result and result.should_execute:
    try:
        workflow.execute_task(result.suggested_params)
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
```

## Testing

```python
def test_typing_pause():
    engine = TriggerEngine(typing_pause_duration=0.1)
    code = "def foo(): pass"
    
    event = engine.detect_event(code)
    assert event is None  # No pause yet
    
    time.sleep(0.15)
    event = engine.detect_event(code)
    assert event.event_type == EventType.TYPING_PAUSE

def test_syntax_error():
    engine = TriggerEngine()
    code_bad = "def foo(\n    pass"
    
    event = engine.detect_event(code_bad)
    assert event.event_type == EventType.SYNTAX_ERROR
    
    code_good = "def foo():\n    pass"
    event = engine.detect_event(code_good)
    assert event.event_type == EventType.ERROR_CLEARED

def test_custom_routing():
    engine = TriggerEngine()
    engine.add_routing_rule(
        EventType.TYPING_PAUSE,
        lambda e: e.line_number > 100,
        "explain"
    )
    
    event = Event(
        event_type=EventType.TYPING_PAUSE,
        code="test",
        line_number=150
    )
    
    result = engine.route_to_agent(event)
    assert result.agent_name == "ExplainAgent"
```

---

**Summary**: The TriggerEngine provides fast, loosely-coupled event detection and routing for developer assistance. Key features:
- Debounced typing pause detection
- Real-time syntax error detection
- Custom routing rules
- Event queue with subscriptions
- Thread-safe operation
- <5ms latency for detection & routing
