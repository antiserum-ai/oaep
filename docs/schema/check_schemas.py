#!/usr/bin/env python3
"""Stdlib smoke test for oaep/0.1 JSON Schemas and example fixtures.

Validates that schemas parse and that examples satisfy the Level-0 required
shape. If the optional `jsonschema` package is installed, examples are also
checked against the full draft-07 schemas.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXAMPLES = HERE / "examples"
HEX = re.compile(r"^0x[0-9a-fA-F]+$")
EVENT_TYPES = {
    "TASK_CREATED",
    "AGENT_STARTED",
    "MODEL_INFERENCE_STARTED",
    "MODEL_INFERENCE_COMPLETED",
    "TOOL_CALLED",
    "TOOL_RETURNED",
    "AGENT_DELEGATED",
    "AGENT_RESULT_RECEIVED",
    "POLICY_CHECK",
    "DATA_ACCESSED",
    "OUTPUT_GENERATED",
    "EXECUTION_COMPLETED",
}
RECEIPT_REQUIRED = ("version", "execution_id", "agent", "task", "output", "signature")
EVENT_REQUIRED = ("version", "type", "execution_id", "commitment")
RECEIPT_PROPERTIES = {
    "version",
    "execution_id",
    "agent",
    "task",
    "models",
    "tools",
    "delegations",
    "output",
    "execution",
    "proofs",
    "trace_root",
    "signature",
}


def load(path: Path) -> object:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def fail(message: str) -> None:
    raise SystemExit(f"check_schemas: {message}")


def expect_hex(label: str, value: object) -> None:
    if not isinstance(value, str) or not HEX.match(value):
        fail(f"{label} must be 0x-prefixed hex, got {value!r}")


def check_receipt_schema(schema: object) -> None:
    if not isinstance(schema, dict):
        fail("receipt schema must be an object")
    if "draft-07" not in str(schema.get("$schema", "")):
        fail("receipt schema must declare JSON Schema draft-07")
    required = schema.get("required")
    if list(required) != list(RECEIPT_REQUIRED):
        fail(f"receipt required set mismatch: {required}")
    props = schema.get("properties")
    if not isinstance(props, dict) or set(props) != RECEIPT_PROPERTIES:
        fail(f"receipt properties mismatch: {props}")


def check_event_schema(schema: object) -> None:
    if not isinstance(schema, dict):
        fail("event schema must be an object")
    if "draft-07" not in str(schema.get("$schema", "")):
        fail("event schema must declare JSON Schema draft-07")
    required = schema.get("required")
    if list(required) != list(EVENT_REQUIRED):
        fail(f"event required set mismatch: {required}")
    enum = schema.get("$defs", {}).get("eventType", {}).get("enum")
    if set(enum or []) != EVENT_TYPES:
        fail(f"event type enum mismatch: {enum}")


def check_receipt_instance(path: Path, instance: object) -> None:
    if not isinstance(instance, dict):
        fail(f"{path.name}: receipt must be an object")
    missing = [key for key in RECEIPT_REQUIRED if key not in instance]
    if missing:
        fail(f"{path.name}: missing required fields {missing}")
    if instance.get("version") != "oaep/0.1":
        fail(f"{path.name}: version must be oaep/0.1")
    expect_hex(f"{path.name}.execution_id", instance["execution_id"])
    expect_hex(f"{path.name}.signature", instance["signature"])
    agent = instance["agent"]
    if not isinstance(agent, dict) or not agent.get("id"):
        fail(f"{path.name}: agent.id is required")
    task = instance["task"]
    if not isinstance(task, dict):
        fail(f"{path.name}: task must be an object")
    expect_hex(f"{path.name}.task.commitment", task.get("commitment"))
    output = instance["output"]
    if not isinstance(output, dict):
        fail(f"{path.name}: output must be an object")
    expect_hex(f"{path.name}.output.commitment", output.get("commitment"))


def check_event_instance(path: Path, instance: object) -> None:
    if not isinstance(instance, dict):
        fail(f"{path.name}: event must be an object")
    missing = [key for key in EVENT_REQUIRED if key not in instance]
    if missing:
        fail(f"{path.name}: missing required fields {missing}")
    if instance.get("version") != "oaep/0.1":
        fail(f"{path.name}: version must be oaep/0.1")
    if instance.get("type") not in EVENT_TYPES:
        fail(f"{path.name}: unknown event type {instance.get('type')!r}")
    expect_hex(f"{path.name}.execution_id", instance["execution_id"])
    expect_hex(f"{path.name}.commitment", instance["commitment"])


def check_with_jsonschema(schema: object, instance: object) -> None:
    try:
        import jsonschema
    except ImportError:
        return
    jsonschema.validate(instance=instance, schema=schema)


def reject_receipt(schema: object, instance: object, why: str) -> None:
    try:
        check_receipt_instance(Path(why), instance)
    except SystemExit:
        return
    try:
        import jsonschema
    except ImportError:
        fail(f"expected invalid receipt ({why})")
    try:
        jsonschema.validate(instance=instance, schema=schema)
    except jsonschema.ValidationError:
        return
    fail(f"schema accepted invalid receipt ({why})")


def reject_event(schema: object, instance: object, why: str) -> None:
    try:
        check_event_instance(Path(why), instance)
    except SystemExit:
        return
    try:
        import jsonschema
    except ImportError:
        fail(f"expected invalid event ({why})")
    try:
        jsonschema.validate(instance=instance, schema=schema)
    except jsonschema.ValidationError:
        return
    fail(f"schema accepted invalid event ({why})")


def main() -> None:
    receipt_schema = load(HERE / "oaep-receipt.schema.json")
    event_schema = load(HERE / "oaep-event.schema.json")
    check_receipt_schema(receipt_schema)
    check_event_schema(event_schema)

    receipt_examples = sorted(EXAMPLES.glob("receipt*.json"))
    event_examples = sorted(EXAMPLES.glob("event*.json"))
    if not receipt_examples or not event_examples:
        fail("expected receipt* and event* fixtures under examples/")

    for path in receipt_examples:
        instance = load(path)
        check_receipt_instance(path, instance)
        check_with_jsonschema(receipt_schema, instance)
    for path in event_examples:
        instance = load(path)
        check_event_instance(path, instance)
        check_with_jsonschema(event_schema, instance)

    reject_receipt(receipt_schema, {}, "empty receipt")
    reject_receipt(
        receipt_schema,
        {
            "version": "oaep/9.9",
            "execution_id": "0x01",
            "agent": {"id": "did:agent:example"},
            "task": {"commitment": "0x02"},
            "output": {"commitment": "0x03"},
            "signature": "0x04",
        },
        "wrong protocol version",
    )
    reject_event(
        event_schema,
        {
            "version": "oaep/0.1",
            "type": "NOT_A_PRD_EVENT",
            "execution_id": "0x01",
            "commitment": "0x02",
        },
        "unknown event type",
    )

    print(
        f"ok: {len(receipt_examples)} receipt fixtures, "
        f"{len(event_examples)} event fixtures"
    )


if __name__ == "__main__":
    try:
        main()
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON: {exc}")
