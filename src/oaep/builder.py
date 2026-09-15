"""Build a signed oaep/0.1 receipt from an in-process execution."""

from __future__ import annotations

import time
from typing import Any, Callable, Never

from oaep.canonical import (
    as_bytes,
    canonical_dumps,
    child_receipt_commitment,
    commit,
    generate_nonce,
    sha256_hex,
    to_hex,
)
from oaep.errors import OaepError
from oaep.events import EventType, event_kind, parse_event_type
from oaep.keys import AgentKey
from oaep.merkle import merkle_root_hex
from oaep.sign import sign_receipt

Clock = Callable[[], int]
NonceFn = Callable[[], bytes]


class Execution:
    """In-process OAEP execution that emits events and a signed receipt."""

    def __init__(
        self,
        key: AgentKey,
        task: bytes | str,
        *,
        agent_version: str | None = None,
        environment: str | None = None,
        clock: Clock | None = None,
        nonce: NonceFn | None = None,
        task_nonce: bytes | None = None,
        start_nonce: bytes | None = None,
    ) -> None:
        self._key = key
        self._clock = clock or (lambda: int(time.time()))
        self._nonce = nonce or generate_nonce
        self._agent = key.agent_dict(version=agent_version)
        self._environment = environment
        self._started_at = self._clock()
        self._events: list[dict[str, Any]] = []
        self._models: list[dict[str, Any]] = []
        self._tools: list[dict[str, Any]] = []
        self._delegations: list[dict[str, Any]] = []
        self._model_seen: set[str] = set()
        self._tool_seen: set[str] = set()
        self._completed: dict[str, Any] | None = None

        task_nonce = task_nonce if task_nonce is not None else self._nonce()
        start_nonce = start_nonce if start_nonce is not None else self._nonce()
        self._task_commitment = commit(task, task_nonce)
        self._execution_id = commit(
            canonical_dumps({"agent": self._agent["id"], "task": self._task_commitment}),
            start_nonce,
        )
        self.emit(EventType.TASK_CREATED, {"task_commitment": self._task_commitment})
        self.emit(EventType.AGENT_STARTED, {"agent": self._agent["id"]})

    @property
    def execution_id(self) -> str:
        return self._execution_id

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def emit(
        self,
        event_type: str | EventType,
        payload: dict[str, Any] | None = None,
        *,
        occurred_at: int | None = None,
        event_nonce: bytes | None = None,
    ) -> dict[str, Any]:
        if self._completed is not None:
            raise OaepError("execution already completed")
        parsed = parse_event_type(event_type)
        payload = dict(payload) if payload else {}
        nonce = event_nonce if event_nonce is not None else self._nonce()
        event = {
            "version": "oaep/0.1",
            "type": parsed.value,
            "execution_id": self._execution_id,
            "event_id": to_hex(nonce),
            "seq": len(self._events),
            "occurred_at": self._clock() if occurred_at is None else occurred_at,
            "commitment": commit(canonical_dumps(payload), nonce),
            "payload": payload,
        }
        self._events.append(event)
        self._note(parsed, payload)
        return event

    def model_inference(
        self,
        identity: bytes | str,
        input_data: bytes | str,
        output: bytes | str,
        *,
        version: str | None = None,
        fingerprint: bytes | str | None = None,
    ) -> None:
        identity_hex = _identity_hex(identity)
        model: dict[str, Any] = {"identity": identity_hex}
        if fingerprint is not None:
            model["fingerprint"] = _identity_hex(fingerprint)
        if version is not None:
            model["version"] = version
        self.emit(
            EventType.MODEL_INFERENCE_STARTED,
            {"model": model, "input_commitment": commit(input_data, self._nonce())},
        )
        self.emit(
            EventType.MODEL_INFERENCE_COMPLETED,
            {"model": model, "output_commitment": commit(output, self._nonce())},
        )

    def tool_call(
        self,
        identity: bytes | str,
        input_data: bytes | str,
        output: bytes | str,
    ) -> None:
        tool = {
            "identity": _identity_hex(identity),
            "input_commitment": commit(input_data, self._nonce()),
            "output_commitment": commit(output, self._nonce()),
        }
        self.emit(EventType.TOOL_CALLED, {"tool": tool})
        self.emit(EventType.TOOL_RETURNED, {"tool": tool})

    def add_delegation(
        self,
        agent_id: str,
        child_receipt: dict[str, Any],
        *,
        path: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "agent": agent_id,
            "receipt": child_receipt_commitment(child_receipt),
        }
        if path is not None:
            payload["path"] = path
        self.emit(EventType.AGENT_DELEGATED, payload)

    def complete(self, output: bytes | str) -> dict[str, Any]:
        if self._completed is not None:
            return self._completed
        output_commitment = commit(output, self._nonce())
        self.emit(EventType.OUTPUT_GENERATED, {"output_commitment": output_commitment})
        completed_at = self._clock()
        self.emit(EventType.EXECUTION_COMPLETED, {"output_commitment": output_commitment})
        receipt: dict[str, Any] = {
            "version": "oaep/0.1",
            "execution_id": self._execution_id,
            "agent": dict(self._agent),
            "task": {"commitment": self._task_commitment},
            "models": list(self._models),
            "tools": list(self._tools),
            "delegations": list(self._delegations),
            "output": {"commitment": output_commitment},
            "execution": {
                "environment": self._environment or "local",
                "started_at": self._started_at,
                "completed_at": completed_at,
            },
            "trace_root": merkle_root_hex(self._events),
        }
        signed = sign_receipt(receipt, self._key)
        self._completed = signed
        return signed

    def _note(self, event_type: EventType, payload: dict[str, Any]) -> None:
        kind = event_kind(event_type)
        match kind:
            case "model":
                model = payload.get("model")
                if not isinstance(model, dict):
                    return
                ident = model.get("identity")
                if not isinstance(ident, str) or ident in self._model_seen:
                    return
                self._model_seen.add(ident)
                entry: dict[str, Any] = {"identity": ident}
                if "fingerprint" in model:
                    entry["fingerprint"] = model["fingerprint"]
                if "version" in model:
                    entry["version"] = model["version"]
                self._models.append(entry)
            case "tool":
                tool = payload.get("tool")
                if not isinstance(tool, dict):
                    return
                ident = tool.get("identity")
                if not isinstance(ident, str) or ident in self._tool_seen:
                    return
                self._tool_seen.add(ident)
                self._tools.append(dict(tool))
            case "delegation":
                if event_type is not EventType.AGENT_DELEGATED:
                    return
                agent_id = payload.get("agent")
                receipt = payload.get("receipt")
                if isinstance(agent_id, str) and isinstance(receipt, str):
                    entry: dict[str, Any] = {"agent": agent_id, "receipt": receipt}
                    path = payload.get("path")
                    if isinstance(path, str) and path:
                        entry["path"] = path
                    self._delegations.append(entry)
            case "trace":
                return
            case _:
                unreachable: Never = kind
                raise OaepError(f"unhandled event kind: {unreachable}")


def start(
    *,
    agent: AgentKey,
    task: bytes | str,
    agent_version: str | None = None,
    environment: str | None = None,
    clock: Clock | None = None,
    nonce: NonceFn | None = None,
    task_nonce: bytes | None = None,
    start_nonce: bytes | None = None,
) -> Execution:
    return Execution(
        key=agent,
        task=task,
        agent_version=agent_version,
        environment=environment,
        clock=clock,
        nonce=nonce,
        task_nonce=task_nonce,
        start_nonce=start_nonce,
    )


def _identity_hex(value: bytes | str) -> str:
    if isinstance(value, str) and value.startswith("0x"):
        return value.lower()
    return sha256_hex(as_bytes(value))
