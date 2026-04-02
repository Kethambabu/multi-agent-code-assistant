"""
Event-driven trigger system.

Detects code events (typing pauses, syntax errors) and routes
them to appropriate agents. Optimized for low latency.

Dependency: tools.bug_detector (detect_syntax_errors only).
"""
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading
import time

from src.tools.bug_detector import detect_syntax_errors


class EventType(Enum):
    """Detectable event types."""
    TYPING_PAUSE = "typing_pause"
    SYNTAX_ERROR = "syntax_error"
    CODE_CHANGE = "code_change"
    ERROR_CLEARED = "error_cleared"
    MULTIPLE_ERRORS = "multiple_errors"


class TriggerPriority(Enum):
    """Event priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class CodeState:
    """Current code state snapshot."""
    code: str
    timestamp: float
    line_number: int = 0
    version: int = 0
    has_errors: bool = False
    error_count: int = 0


@dataclass
class Event:
    """Triggering event with metadata."""
    event_type: EventType
    code: str
    timestamp: float = field(default_factory=time.time)
    line_number: int = 0
    priority: TriggerPriority = TriggerPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_agent: Optional[str] = None

    def __hash__(self):
        return hash((self.event_type, self.code[:100], self.line_number))

    def __eq__(self, other):
        if not isinstance(other, Event):
            return False
        return (
            self.event_type == other.event_type
            and self.code[:100] == other.code[:100]
            and self.line_number == other.line_number
        )


@dataclass
class RoutingResult:
    """Result of a routing decision."""
    agent_type: str
    agent_name: str
    priority: TriggerPriority
    should_execute: bool = True
    reason: str = ""
    suggested_params: Dict = field(default_factory=dict)


class TriggerEngine:
    """
    Event-driven trigger system for code analysis.

    Detects typing pauses and syntax errors, routes to appropriate agents.
    Thread-safe and optimized for low latency.
    """

    def __init__(
        self,
        typing_pause_duration: float = 1.0,
        max_events_in_queue: int = 100,
        syntax_check_debounce: float = 0.5,
    ) -> None:
        self.typing_pause_duration = typing_pause_duration
        self.max_events_in_queue = max_events_in_queue
        self.syntax_check_debounce = syntax_check_debounce

        self._event_queue: deque = deque(maxlen=max_events_in_queue)
        self._last_code_state: Optional[CodeState] = None
        self._last_typing_time: float = 0
        self._last_syntax_check: float = 0
        self._last_error_state: Dict[str, Any] = {}

        self._typing_pause_timer: Optional[threading.Timer] = None
        self._pending_pause_event: Optional[Event] = None

        self._routing_rules: Dict[EventType, List[tuple]] = {}
        self._subscribers: Dict[EventType, List[Callable]] = {}

        self._event_count = 0
        self._routed_count = 0
        self._dropped_count = 0

        self._lock = threading.RLock()
        self._setup_default_routes()

    # ------------------------------------------------------------------
    # Event detection
    # ------------------------------------------------------------------

    def detect_event(
        self,
        code: str,
        line_number: int = 0,
        timestamp: Optional[float] = None,
    ) -> Optional[Event]:
        """Detect events from code changes."""
        if timestamp is None:
            timestamp = time.time()

        with self._lock:
            pause_event = self._detect_typing_pause(code, timestamp)
            if pause_event:
                return pause_event

            current_state = CodeState(
                code=code,
                timestamp=timestamp,
                line_number=line_number,
                version=self._get_version(),
            )

            if self._should_check_syntax(timestamp):
                error_event = self._detect_syntax_error(current_state)
                if error_event:
                    self._last_code_state = current_state
                    return error_event

            clear_event = self._detect_error_cleared(current_state)
            if clear_event:
                self._last_code_state = current_state
                return clear_event

            if self._has_code_changed(current_state):
                self._last_code_state = current_state
                self._last_typing_time = timestamp
                self._schedule_typing_pause(code, line_number, timestamp)
                return None

            return None

    def _detect_typing_pause(self, code: str, timestamp: float) -> Optional[Event]:
        if self._last_typing_time == 0:
            return None
        if timestamp - self._last_typing_time >= self.typing_pause_duration:
            if self._pending_pause_event:
                event = self._pending_pause_event
                self._pending_pause_event = None
                return event
        return None

    def _detect_syntax_error(self, state: CodeState) -> Optional[Event]:
        try:
            errors = detect_syntax_errors(state.code)
            count = len(errors)
            state.has_errors = count > 0
            state.error_count = count

            prev = self._last_error_state.get("count", 0)
            if count > 0 and count != prev:
                self._last_error_state = {
                    "count": count, "errors": errors, "timestamp": state.timestamp,
                }
                priority = TriggerPriority.HIGH if count > 3 else TriggerPriority.NORMAL
                return Event(
                    event_type=EventType.MULTIPLE_ERRORS if count > 3 else EventType.SYNTAX_ERROR,
                    code=state.code,
                    line_number=state.line_number,
                    timestamp=state.timestamp,
                    priority=priority,
                    metadata={
                        "error_count": count,
                        "errors": errors,
                        "lines": [e.line_number for e in errors],
                    },
                )
        except Exception:
            pass
        return None

    def _detect_error_cleared(self, state: CodeState) -> Optional[Event]:
        if not self._last_error_state:
            return None
        try:
            errors = detect_syntax_errors(state.code)
            prev_count = self._last_error_state.get("count", 0)
            if prev_count > 0 and len(errors) == 0:
                self._last_error_state = {}
                return Event(
                    event_type=EventType.ERROR_CLEARED,
                    code=state.code,
                    line_number=state.line_number,
                    timestamp=state.timestamp,
                    priority=TriggerPriority.NORMAL,
                    metadata={"previously_had": prev_count, "now_have": 0},
                )
        except Exception:
            pass
        return None

    def _schedule_typing_pause(self, code: str, line_number: int, timestamp: float):
        if self._typing_pause_timer:
            self._typing_pause_timer.cancel()

        self._pending_pause_event = Event(
            event_type=EventType.TYPING_PAUSE,
            code=code,
            timestamp=timestamp,
            line_number=line_number,
            priority=TriggerPriority.NORMAL,
            metadata={"debounce_duration": self.typing_pause_duration},
        )

        self._typing_pause_timer = threading.Timer(
            self.typing_pause_duration, lambda: None,
        )
        self._typing_pause_timer.daemon = True
        self._typing_pause_timer.start()

    # ------------------------------------------------------------------
    # Event routing
    # ------------------------------------------------------------------

    def route_to_agent(self, event: Event) -> RoutingResult:
        """Route event to appropriate agent."""
        with self._lock:
            rules = self._routing_rules.get(event.event_type, [])
            for condition, agent_type in rules:
                if condition(event):
                    agent_name = self._select_agent(agent_type, event)
                    params = self._build_agent_params(agent_type, event)
                    self._routed_count += 1
                    return RoutingResult(
                        agent_type=agent_type,
                        agent_name=agent_name,
                        priority=event.priority,
                        should_execute=True,
                        reason=f"Matched {event.event_type.value}",
                        suggested_params=params,
                    )
            return self._get_default_route(event)

    def _select_agent(self, agent_type: str, event: Event) -> str:
        mapping = {
            "debug": "debug",
            "completion": "completion",
            "explain": "explain",
            "test": "test",
        }
        if agent_type == "completion" and event.metadata.get("error_count", 0) > 0:
            return "debug"
        return mapping.get(agent_type, agent_type)

    def _build_agent_params(self, agent_type: str, event: Event) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "code": event.code,
            "line_number": event.line_number,
            "source": "trigger_engine",
        }
        if event.event_type in (EventType.SYNTAX_ERROR, EventType.MULTIPLE_ERRORS):
            params["error_count"] = event.metadata.get("error_count", 0)
            params["errors"] = event.metadata.get("errors", [])
        elif event.event_type == EventType.TYPING_PAUSE:
            params["suggest_completion"] = True
            params["temperature"] = 0.7
        elif event.event_type == EventType.ERROR_CLEARED:
            params["verify_fix"] = True
        return params

    def _get_default_route(self, event: Event) -> RoutingResult:
        if event.event_type == EventType.SYNTAX_ERROR:
            return RoutingResult(
                agent_type="debug", agent_name="debug",
                priority=TriggerPriority.HIGH, should_execute=True,
                reason="Default syntax error routing",
                suggested_params={"code": event.code},
            )
        if event.event_type == EventType.TYPING_PAUSE:
            return RoutingResult(
                agent_type="completion", agent_name="completion",
                priority=TriggerPriority.NORMAL, should_execute=True,
                reason="Default typing pause routing",
                suggested_params={"code": event.code, "line_number": event.line_number},
            )
        return RoutingResult(
            agent_type="none", agent_name="",
            priority=TriggerPriority.LOW, should_execute=False,
            reason="No routing rule for event type",
        )

    # ------------------------------------------------------------------
    # Event queue
    # ------------------------------------------------------------------

    def emit_event(self, event: Event) -> bool:
        with self._lock:
            try:
                self._event_queue.append(event)
                self._event_count += 1
                self._notify_subscribers(event)
                return True
            except IndexError:
                self._dropped_count += 1
                return False

    def get_events(self, max_count: int = 10) -> List[Event]:
        with self._lock:
            events = []
            for _ in range(min(max_count, len(self._event_queue))):
                try:
                    events.append(self._event_queue.popleft())
                except IndexError:
                    break
            return events

    def clear_queue(self):
        with self._lock:
            self._event_queue.clear()

    # ------------------------------------------------------------------
    # Routing configuration
    # ------------------------------------------------------------------

    def add_routing_rule(
        self,
        event_type: EventType,
        condition: Callable[[Event], bool],
        agent_type: str,
    ):
        with self._lock:
            if event_type not in self._routing_rules:
                self._routing_rules[event_type] = []
            self._routing_rules[event_type].append((condition, agent_type))

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def _notify_subscribers(self, event: Event):
        for callback in self._subscribers.get(event.event_type, []):
            try:
                callback(event)
            except Exception:
                pass

    def _setup_default_routes(self):
        self.add_routing_rule(EventType.SYNTAX_ERROR, lambda e: True, "debug")
        self.add_routing_rule(
            EventType.MULTIPLE_ERRORS,
            lambda e: e.metadata.get("error_count", 0) > 3,
            "debug",
        )
        self.add_routing_rule(EventType.TYPING_PAUSE, lambda e: True, "completion")
        self.add_routing_rule(EventType.ERROR_CLEARED, lambda e: False, "none")

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _has_code_changed(self, new_state: CodeState) -> bool:
        if not self._last_code_state:
            return True
        return new_state.code != self._last_code_state.code

    def _should_check_syntax(self, timestamp: float) -> bool:
        if self._last_syntax_check == 0:
            self._last_syntax_check = timestamp
            return True
        if timestamp - self._last_syntax_check >= self.syntax_check_debounce:
            self._last_syntax_check = timestamp
            return True
        return False

    def _get_version(self) -> int:
        if not self._last_code_state:
            return 0
        return self._last_code_state.version + 1

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_events": self._event_count,
                "routed_events": self._routed_count,
                "dropped_events": self._dropped_count,
                "queued_events": len(self._event_queue),
                "queue_size": self.max_events_in_queue,
                "typing_pause_duration": self.typing_pause_duration,
                "syntax_check_debounce": self.syntax_check_debounce,
            }

    def reset(self):
        with self._lock:
            self._event_queue.clear()
            self._last_code_state = None
            self._last_typing_time = 0
            self._last_syntax_check = 0
            self._last_error_state = {}
            self._pending_pause_event = None
            self._event_count = 0
            self._routed_count = 0
            self._dropped_count = 0
