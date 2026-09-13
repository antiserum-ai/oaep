"""PRD §8 execution-event types."""

from __future__ import annotations

from enum import Enum
from typing import Literal, Never

from oaep.errors import OaepError


class EventType(str, Enum):
    TASK_CREATED = "TASK_CREATED"
    AGENT_STARTED = "AGENT_STARTED"
    MODEL_INFERENCE_STARTED = "MODEL_INFERENCE_STARTED"
    MODEL_INFERENCE_COMPLETED = "MODEL_INFERENCE_COMPLETED"
    TOOL_CALLED = "TOOL_CALLED"
    TOOL_RETURNED = "TOOL_RETURNED"
    AGENT_DELEGATED = "AGENT_DELEGATED"
    AGENT_RESULT_RECEIVED = "AGENT_RESULT_RECEIVED"
    POLICY_CHECK = "POLICY_CHECK"
    DATA_ACCESSED = "DATA_ACCESSED"
    OUTPUT_GENERATED = "OUTPUT_GENERATED"
    EXECUTION_COMPLETED = "EXECUTION_COMPLETED"


def parse_event_type(value: str | EventType) -> EventType:
    if isinstance(value, EventType):
        return value
    try:
        return EventType(value)
    except ValueError:
        raise OaepError(f"unknown event type: {value!r}") from None


def event_kind(event_type: EventType) -> Literal["model", "tool", "delegation", "trace"]:
    """Classify an event for receipt bookkeeping. Exhaustive over EventType."""
    match event_type:
        case EventType.MODEL_INFERENCE_STARTED | EventType.MODEL_INFERENCE_COMPLETED:
            return "model"
        case EventType.TOOL_CALLED | EventType.TOOL_RETURNED:
            return "tool"
        case EventType.AGENT_DELEGATED | EventType.AGENT_RESULT_RECEIVED:
            return "delegation"
        case (
            EventType.TASK_CREATED
            | EventType.AGENT_STARTED
            | EventType.POLICY_CHECK
            | EventType.DATA_ACCESSED
            | EventType.OUTPUT_GENERATED
            | EventType.EXECUTION_COMPLETED
        ):
            return "trace"
        case _:
            unreachable: Never = event_type
            raise OaepError(f"unhandled event type: {unreachable}")
