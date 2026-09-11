"""Level-0 structural verification of a local OAEP receipt."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

from oaep.errors import OaepError

SCHEMA_RESOURCE = "oaep-receipt.schema.json"
# Level-0 required set from docs/schema/oaep-receipt.schema.json (protocol #4).
REQUIRED_FIELDS = (
    "version",
    "execution_id",
    "agent",
    "task",
    "output",
    "signature",
)
OPTIONAL_FIELDS = (
    "models",
    "tools",
    "delegations",
    "execution",
    "proofs",
    "trace_root",
)
TOP_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS
LEVEL = 0
LEVEL_NAME = "structural"


def load_receipt_schema() -> dict[str, Any]:
    """Load the packaged v0.1 receipt schema (local file; never fetched)."""
    path = files("oaep") / "schema" / SCHEMA_RESOURCE
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class Report:
    path: Path
    valid: bool
    errors: list[str] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    version: str | None = None
    schema_id: str = "oaep/0.1"
    level: int = LEVEL

    def to_json_obj(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "level": self.level,
            "level_name": LEVEL_NAME,
            "path": str(self.path),
            "schema": self.schema_id,
            "version": self.version,
            "errors": list(self.errors),
            "checks": [
                {"name": c.name, "ok": c.ok, "detail": c.detail} for c in self.checks
            ],
        }


def verify_path(path: Path | str) -> Report:
    """Load a local receipt JSON and run Level-0 structural validation."""
    receipt_path = Path(path)
    if not receipt_path.is_file():
        raise OaepError(f"receipt not found: {receipt_path}")
    try:
        text = receipt_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OaepError(f"cannot read receipt: {receipt_path}: {exc}") from exc
    try:
        instance: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OaepError(f"not valid JSON: {receipt_path}: {exc}") from exc
    return verify_receipt(instance, path=receipt_path)


def verify_receipt(instance: Any, *, path: Path | str = Path("-")) -> Report:
    """Validate an in-memory receipt against the packaged v0.1 schema."""
    schema = load_receipt_schema()
    receipt_path = Path(path)
    version = instance.get("version") if isinstance(instance, dict) else None
    if not isinstance(version, str):
        version = None

    validator = Draft7Validator(schema)
    schema_errors = sorted(validator.iter_errors(instance), key=_error_sort_key)
    messages = [_format_error(err) for err in schema_errors]
    checks = _checks_from_instance(instance, schema_errors)
    return Report(
        path=receipt_path,
        valid=not schema_errors,
        errors=messages,
        checks=checks,
        version=version,
        schema_id="oaep/0.1",
    )


def format_text(report: Report) -> str:
    """Human-readable Level-0 structural report (PRD §21 shape, schema only)."""
    mark = "✓" if report.valid else "✗"
    lines = [
        "OAEP Execution Verification",
        "",
        "Level 0  structural    schema only (no signature, TEE, or zk)",
        "",
        f"Receipt              {report.path}",
        f"Schema               {report.schema_id}",
        "",
    ]
    width = max(len(check.name) for check in report.checks)
    for check in report.checks:
        flag = "✓" if check.ok else "✗"
        detail = f"  {check.detail}" if check.detail else ""
        lines.append(f"{check.name:<{width}}  {flag}{detail}")
    lines.append("")
    if report.valid:
        lines.append(f"{mark}  Structurally valid")
    else:
        lines.append(f"{mark}  Structurally invalid")
        if report.errors:
            lines.append("")
            lines.append("Errors")
            for message in report.errors:
                lines.append(f"  {message}")
    lines.append("")
    return "\n".join(lines)


def _error_sort_key(err: Any) -> tuple[str, ...]:
    return tuple(str(part) for part in err.absolute_path)


def _format_error(err: Any) -> str:
    path = _json_pointer(err.absolute_path)
    return f"{path}: {err.message}"


def _json_pointer(absolute_path: Any) -> str:
    if not absolute_path:
        return "$"
    parts: list[str] = []
    for part in absolute_path:
        if isinstance(part, int):
            parts.append(f"[{part}]")
        else:
            parts.append(f".{part}")
    return "$" + "".join(parts)


def _checks_from_instance(instance: Any, schema_errors: list[Any]) -> list[Check]:
    failed: dict[str, list[str]] = {name: [] for name in TOP_FIELDS}
    if not isinstance(instance, dict):
        return [
            Check(name=name, ok=False, detail="receipt must be a JSON object")
            for name in TOP_FIELDS
        ]

    for err in schema_errors:
        path = list(err.absolute_path)
        if path and str(path[0]) in failed:
            failed[str(path[0])].append(err.message)
            continue
        if err.validator == "required" and isinstance(err.instance, dict):
            required = err.validator_value
            if isinstance(required, list):
                for key in required:
                    if key in failed and key not in err.instance:
                        failed[key].append("required field missing")
            continue
        if err.validator == "type" and not path:
            for name in TOP_FIELDS:
                failed[name].append(err.message)

    checks: list[Check] = []
    for name in TOP_FIELDS:
        messages = failed[name]
        if messages:
            checks.append(Check(name=name, ok=False, detail=messages[0]))
            continue
        present = name in instance
        detail = _ok_detail(name, instance.get(name), present=present)
        checks.append(Check(name=name, ok=True, detail=detail))
    return checks


def _ok_detail(name: str, value: Any, *, present: bool) -> str:
    if not present:
        return "omitted"
    if name == "version" and isinstance(value, str):
        return value
    if name in {"models", "tools", "delegations", "proofs"} and isinstance(value, list):
        return str(len(value))
    if name == "agent" and isinstance(value, dict):
        ident = value.get("id")
        return ident if isinstance(ident, str) else ""
    return ""
