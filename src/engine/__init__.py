"""
Engine Layer — Event-driven trigger system.

Detects code events and routes them to appropriate agents.
Designed for performance with minimal coupling.

Dependency: tools.bug_detector (for syntax checking).
"""
from src.engine.trigger import (
    TriggerEngine,
    Event,
    EventType,
    TriggerPriority,
    CodeState,
    RoutingResult,
)

__all__ = [
    "TriggerEngine",
    "Event",
    "EventType",
    "TriggerPriority",
    "CodeState",
    "RoutingResult",
]
