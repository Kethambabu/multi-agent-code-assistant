"""
TRIGGER SYSTEM QUICK REFERENCE

Fast lookup for TriggerEngine usage patterns and common scenarios.
"""

# ============================================================================
# QUICK START
# ============================================================================

## 30-Second Example

```python
from trigger_engine import TriggerEngine
from crew_setup import CrewWorkflow
from tasks import TaskType

# Create engine
engine = TriggerEngine(typing_pause_duration=1.0)
workflow = CrewWorkflow()

# On code change (e.g., editor keystroke)
def on_code_change(code, line_number):
    # Detect events
    event = engine.detect_event(code, line_number=line_number)
    
    if event:
        # Route to agent
        routing = engine.route_to_agent(event)
        
        # Execute if needed
        if routing.should_execute:
            result = workflow.execute_task({
                "task_type": TaskType.DEBUG if "debug" in routing.agent_type else TaskType.COMPLETION,
                **routing.suggested_params
            })
            
            return result.output
```


# ============================================================================
# COMMON PATTERNS
# ============================================================================

## Pattern: Listen for Errors and Auto-Debug

```python
engine = TriggerEngine()

# Subscribe to errors
def on_error(event):
    print(f"Error detected: {event.metadata['error_count']} issues")

engine.subscribe(EventType.SYNTAX_ERROR, on_error)
engine.subscribe(EventType.MULTIPLE_ERRORS, on_error)

# Usage
code = "def foo(\npass"
event = engine.detect_event(code)
if event:
    engine.emit_event(event)
```

## Pattern: Suggest Completions on Pause

```python
engine = TriggerEngine(typing_pause_duration=1.0)

# When user stops typing
code = "def fibonacci(n):\n    if n <= 1:\n        return"

# Wait for pause...
time.sleep(1.1)

event = engine.detect_event(code, line_number=3)
if event and event.event_type == EventType.TYPING_PAUSE:
    routing = engine.route_to_agent(event)
    # routing.agent_name will be "CompletionAgent"
```

## Pattern: Custom Routing by Severity

```python
engine = TriggerEngine()

# Route critical errors to test agent
engine.add_routing_rule(
    EventType.MULTIPLE_ERRORS,
    lambda e: e.metadata.get("error_count") > 5,
    agent_type="test"
)

code = "def f(\ndef g(\n" * 10  # Many errors
event = engine.detect_event(code)
routing = engine.route_to_agent(event)
# routing.agent_name will prefer TestAgent
```

## Pattern: Process Event Queue

```python
engine = TriggerEngine()

# Emit multiple events
for code in code_list:
    event = engine.detect_event(code)
    if event:
        engine.emit_event(event)

# Process in batch
while True:
    events = engine.get_events(max_count=10)
    if not events:
        break
    
    for event in events:
        route = engine.route_to_agent(event)
        execute_agent(route)
```

## Pattern: Real-Time Monitoring

```python
engine = TriggerEngine()

# Monitor for issues
def monitor():
    while running:
        event = engine.detect_event(current_code())
        
        if event and event.event_type == EventType.MULTIPLE_ERRORS:
            send_alert(f"Critical: {event.metadata['error_count']} errors")
        
        time.sleep(0.1)

threading.Thread(target=monitor, daemon=True).start()
```


# ============================================================================
# API REFERENCE
# ============================================================================

## TriggerEngine Methods

### detect_event(code, line_number=0, timestamp=None) -> Optional[Event]
Detect events from code changes.

```python
event = engine.detect_event("def foo():\n    ", line_number=2)
# Returns Event or None
```

**Returns:**
- Event if TYPING_PAUSE, SYNTAX_ERROR, MULTIPLE_ERRORS, or ERROR_CLEARED detected
- None if no event

### route_to_agent(event) -> RoutingResult
Determine which agent should handle this event.

```python
routing = engine.route_to_agent(event)
# routing.agent_name: CompletionAgent, DebugAgent, ExplainAgent, TestAgent
# routing.priority: TriggerPriority
# routing.suggested_params: dict for agent
```

**Returns:**
- RoutingResult with agent selection and parameters

### emit_event(event) -> bool
Add event to processing queue.

```python
success = engine.emit_event(event)
# Returns True if queued, False if queue full
```

### get_events(max_count=10) -> List[Event]
Retrieve queued events (FIFO).

```python
events = engine.get_events(max_count=5)
for event in events:
    # Process event...
```

### add_routing_rule(event_type, condition, agent_type) -> None
Add custom routing rule.

```python
engine.add_routing_rule(
    EventType.TYPING_PAUSE,
    lambda e: e.line_number > 100,  # Condition
    agent_type="explain"             # Agent to use
)
```

### subscribe(event_type, callback) -> None
Subscribe to specific events.

```python
def on_error(event):
    print(f"Error: {event}")

engine.subscribe(EventType.SYNTAX_ERROR, on_error)
```

### get_statistics() -> Dict
Get engine statistics.

```python
stats = engine.get_statistics()
# Keys: total_events, routed_events, dropped_events, queued_events, queue_size
```


# ============================================================================
# EVENT TYPES
# ============================================================================

| Type | Trigger | Default Agent | Priority |
|------|---------|---------------|----------|
| TYPING_PAUSE | No changes × 1+ sec | CompletionAgent | NORMAL |
| SYNTAX_ERROR | Error detected | DebugAgent | HIGH |
| MULTIPLE_ERRORS | 3+ errors | DebugAgent | CRITICAL |
| ERROR_CLEARED | All errors fixed | (none) | NORMAL |
| CODE_CHANGE | Any code change | (cached) | LOW |


# ============================================================================
# CONFIGURATION
# ============================================================================

## Recommended Settings

### Responsive (Low Latency)
```python
TriggerEngine(
    typing_pause_duration=0.3,
    max_events_in_queue=50,
    syntax_check_debounce=0.1
)
```

### Balanced (Default)
```python
TriggerEngine(
    typing_pause_duration=1.0,
    max_events_in_queue=100,
    syntax_check_debounce=0.5
)
```

### Efficient (Low CPU)
```python
TriggerEngine(
    typing_pause_duration=2.0,
    max_events_in_queue=200,
    syntax_check_debounce=2.0
)
```


# ============================================================================
# TROUBLESHOOTING
# ============================================================================

## Issue: No events detected
**Solution:** Call detect_event() on every code change
```python
# Wrong
event = engine.detect_event(code)

# Right
while editor.is_open():
    code = editor.get_code()
    event = engine.detect_event(code)
```

## Issue: Typing pause not triggering
**Solution:** Ensure enough time has passed
```python
# Pause = 1 second, code = unchanged
time.sleep(1.1)  # Must be > 1 second
event = engine.detect_event(same_code)
```

## Issue: Queue filling up
**Solution:** Process events more frequently
```python
# Process every 100ms instead of 1s
while True:
    events = engine.get_events()
    for event in events:
        process(event)
    time.sleep(0.1)  # Not 1.0
```

## Issue: Too many completions
**Solution:** Increase pause duration
```python
# 1 second pauses (many completions)
engine = TriggerEngine(typing_pause_duration=1.0)

# Change to 2 seconds
engine.typing_pause_duration = 2.0
```


# ============================================================================
# INTEGRATION CHECKLIST
# ============================================================================

- [ ] Create TriggerEngine instance
- [ ] Create CrewWorkflow instance
- [ ] On code change, call detect_event()
- [ ] If event returned, route with route_to_agent()
- [ ] Map agent_type to TaskType
- [ ] Execute workflow.execute_task() with suggested_params
- [ ] (Optional) Process event queue asynchronously
- [ ] (Optional) Add custom routing rules
- [ ] (Optional) Subscribe to specific events
- [ ] Monitor statistics with get_statistics()


# ============================================================================
# PERFORMANCE TIPS
# ============================================================================

✅ DO:
- Use one TriggerEngine per user/session
- Process queue in separate thread
- Monitor dropped_events in statistics
- Increase debounce if CPU high
- Use custom rules for business logic

❌ DON'T:
- Create multiple engines (wastes memory)
- Process queue only on demand (events lag)
- Ignore dropped_events
- Block in event handlers
- Import agents into trigger_engine


# ============================================================================
# EXAMPLE: VS CODE EXTENSION
# ============================================================================

```python
# In VS Code extension
class TriggerLanguageServer:
    def __init__(self):
        self.engine = TriggerEngine()
        self.workflow = CrewWorkflow()
    
    def on_did_change(self, uri, version, content_changes):
        """Called on document change."""
        code = self.get_file_content(uri)
        line = self.get_cursor_line(uri)
        
        # Detect event
        event = self.engine.detect_event(code, line_number=line)
        
        if event:
            # Route to agent
            routing = self.engine.route_to_agent(event)
            
            # Send diagnostic/hint/completion
            if routing.agent_type == "debug":
                self.send_diagnostic(uri, routing)
            elif routing.agent_type == "completion":
                self.send_completion_hint(uri, routing)
    
    def send_diagnostic(self, uri, routing):
        """Send error diagnostic to client."""
        # Create VS Code diagnostic from routing.suggested_params
        pass
    
    def send_completion_hint(self, uri, routing):
        """Send completion hint to client."""
        # Get completion from agent and send as VS Code CodeAction
        pass
```


# ============================================================================
# TESTING TEMPLATE
# ============================================================================

```python
import unittest
from trigger_engine import TriggerEngine, EventType

class TestTriggerEngine(unittest.TestCase):
    def setUp(self):
        self.engine = TriggerEngine(typing_pause_duration=0.1)
    
    def test_syntax_error_detection(self):
        bad_code = "def foo(\npass"
        event = self.engine.detect_event(bad_code)
        self.assertEqual(event.event_type, EventType.SYNTAX_ERROR)
    
    def test_typing_pause(self):
        code = "x = 1"
        event1 = self.engine.detect_event(code)
        self.assertIsNone(event1)
        
        time.sleep(0.15)
        event2 = self.engine.detect_event(code)
        self.assertEqual(event2.event_type, EventType.TYPING_PAUSE)
    
    def test_error_cleared(self):
        bad = "def foo(\npass"
        self.engine.detect_event(bad)
        
        good = "def foo():\n    pass"
        event = self.engine.detect_event(good)
        self.assertEqual(event.event_type, EventType.ERROR_CLEARED)
    
    def test_routing(self):
        event = Event(event_type=EventType.TYPING_PAUSE, code="")
        routing = self.engine.route_to_agent(event)
        self.assertEqual(routing.agent_type, "completion")

if __name__ == "__main__":
    unittest.main()
```


# ============================================================================
# GLOSSARY
# ============================================================================

**Debounce**: Prevent repeated triggers by requiring inactivity time

**Event**: Detected action (typing pause, syntax error, etc.)

**Route**: Select which agent should handle an event

**RoutingResult**: Decision result with agent name and parameters

**Priority**: Urgency level (LOW, NORMAL, HIGH, CRITICAL)

**Event Queue**: FIFO buffer of emitted events

**Subscription**: Function called when specific event occurs

**Metadata**: Event-specific additional information


# ============================================================================
# RELATED FILES
# ============================================================================

- trigger_engine.py - Main implementation
- TRIGGER_ENGINE_GUIDE.md - Complete documentation
- trigger_integration_examples.py - 6 detailed examples
- crew_setup.py - Workflow integration
- bug_detector.py - Syntax error detection (used by engine)


---

**Last Updated**: Phase 7 - Trigger System
**Status**: ✅ Complete
**Lines of Code**: 900+ (implementation + examples)
**Type Hints**: 100%
