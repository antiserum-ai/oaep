"""Level-0 verification of a local OAEP receipt."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import Any, Never

from jsonschema import Draft7Validator

from oaep.canonical import child_receipt_commitment, hex_equal, hex_key
from oaep.delegations import DelegationStatus, delegation_mark, resolve_child_path
from oaep.errors import OaepError
from oaep.sign import verify_receipt_signature

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
LEVEL_NAME_SIGNED = "signed"
LEVEL_NAME_STRUCTURAL = "structural"


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
class ChildReport:
    index: int
    agent: str | None
    receipt: str | None
    status: DelegationStatus
    path: Path | None = None
    detail: str = ""
    commitment_matches: bool | None = None
    report: Report | None = None

    def to_json_obj(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "agent": self.agent,
            "receipt": self.receipt,
            "status": self.status,
            "path": str(self.path) if self.path is not None else None,
            "detail": self.detail,
            "commitment_matches": self.commitment_matches,
            "report": self.report.to_json_obj() if self.report is not None else None,
        }


@dataclass
class Report:
    path: Path
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    version: str | None = None
    schema_id: str = "oaep/0.1"
    level: int = LEVEL
    schema_only: bool = False
    signature_verified: bool | None = None
    delegations: list[ChildReport] = field(default_factory=list)
    strict_delegations: bool = False
    commitment: str | None = None

    @property
    def level_name(self) -> str:
        return LEVEL_NAME_STRUCTURAL if self.schema_only else LEVEL_NAME_SIGNED

    def to_json_obj(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "level": self.level,
            "level_name": self.level_name,
            "schema_only": self.schema_only,
            "signature_verified": self.signature_verified,
            "strict_delegations": self.strict_delegations,
            "path": str(self.path),
            "schema": self.schema_id,
            "version": self.version,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "checks": [
                {"name": c.name, "ok": c.ok, "detail": c.detail} for c in self.checks
            ],
            "delegations": [child.to_json_obj() for child in self.delegations],
            "commitment": self.commitment,
        }


def verify_path(
    path: Path | str,
    *,
    schema_only: bool = False,
    delegation_dir: Path | str | None = None,
    strict_delegations: bool = False,
    _seen: frozenset[str] | None = None,
) -> Report:
    """Load a local receipt JSON and run Level-0 verification."""
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
    return verify_receipt(
        instance,
        path=receipt_path,
        schema_only=schema_only,
        delegation_dir=delegation_dir,
        strict_delegations=strict_delegations,
        _seen=_seen,
    )


def verify_receipt(
    instance: Any,
    *,
    path: Path | str = Path("-"),
    schema_only: bool = False,
    delegation_dir: Path | str | None = None,
    strict_delegations: bool = False,
    _seen: frozenset[str] | None = None,
) -> Report:
    """Validate an in-memory receipt against schema, and Ed25519 unless schema_only."""
    schema = load_receipt_schema()
    receipt_path = Path(path)
    child_dir = Path(delegation_dir) if delegation_dir is not None else None
    version = instance.get("version") if isinstance(instance, dict) else None
    if not isinstance(version, str):
        version = None

    validator = Draft7Validator(schema)
    schema_errors = sorted(validator.iter_errors(instance), key=_error_sort_key)
    messages = [_format_error(err) for err in schema_errors]
    checks = _checks_from_instance(instance, schema_errors)
    schema_ok = not schema_errors
    signature_verified: bool | None = None

    if schema_only:
        report = Report(
            path=receipt_path,
            valid=schema_ok,
            errors=messages,
            checks=checks,
            version=version,
            schema_id="oaep/0.1",
            schema_only=True,
            signature_verified=None,
            strict_delegations=strict_delegations,
        )
        report.commitment = _raw_commitment(instance)
        return _with_delegations(
            report,
            instance,
            schema_only=True,
            delegation_dir=child_dir,
            strict_delegations=strict_delegations,
            seen=_seen,
        )

    if schema_ok:
        try:
            verify_receipt_signature(instance)
            signature_verified = True
            checks.append(Check(name="Agent Signature", ok=True, detail="ed25519"))
        except OaepError as exc:
            signature_verified = False
            messages = [*messages, str(exc)]
            checks.append(Check(name="Agent Signature", ok=False, detail=str(exc)))
    else:
        signature_verified = False
        checks.append(
            Check(
                name="Agent Signature",
                ok=False,
                detail="skipped (receipt failed schema)",
            )
        )

    report = Report(
        path=receipt_path,
        valid=schema_ok and bool(signature_verified),
        errors=messages,
        checks=checks,
        version=version,
        schema_id="oaep/0.1",
        schema_only=False,
        signature_verified=signature_verified,
        strict_delegations=strict_delegations,
    )
    report.commitment = _raw_commitment(instance)
    return _with_delegations(
        report,
        instance,
        schema_only=False,
        delegation_dir=child_dir,
        strict_delegations=strict_delegations,
        seen=_seen,
    )


def format_text(report: Report) -> str:
    """Human-readable Level-0 report. Does not say Execution Verified."""
    mark = "✓" if report.valid else "✗"
    if report.schema_only:
        level_line = "Level 0  structural    schema only (no signature, TEE, or zk)"
        ok_line = "Structurally valid" if report.valid else "Structurally invalid"
    else:
        level_line = "Level 0  signed        schema + ed25519 (no TEE or zk)"
        ok_line = "Signed claim is valid" if report.valid else "Signed claim is invalid"
    lines = [
        "OAEP Execution Verification",
        "",
        level_line,
        "",
        f"Receipt              {report.path}",
        f"Schema               {report.schema_id}",
        "",
    ]
    labels = [check.name for check in report.checks]
    labels.extend(f"Delegation [{child.index}]" for child in report.delegations)
    if labels:
        width = max(len(label) for label in labels)
        for check in report.checks:
            flag = "✓" if check.ok else "✗"
            detail = f"  {check.detail}" if check.detail else ""
            lines.append(f"{check.name:<{width}}  {flag}{detail}")
        for child in report.delegations:
            flag = delegation_mark(child.status)
            detail = _delegation_detail(child)
            extra = f"  {detail}" if detail else ""
            lines.append(f"{'Delegation [' + str(child.index) + ']':<{width}}  {flag}{extra}")
        lines.append("")
    if report.warnings:
        lines.append("Warnings")
        for warning in report.warnings:
            lines.append(f"  {warning}")
        lines.append("")
    lines.append(f"{mark}  {ok_line}")
    if not report.valid and report.errors:
        lines.append("")
        lines.append("Errors")
        for message in report.errors:
            lines.append(f"  {message}")
    lines.append("")
    return "\n".join(lines)


def _delegation_detail(child: ChildReport) -> str:
    if child.detail:
        return child.detail
    parts: list[str] = []
    if child.agent:
        parts.append(child.agent)
    if child.path is not None:
        parts.append(str(child.path))
    return "  ".join(parts)


def _with_delegations(
    report: Report,
    instance: Any,
    *,
    schema_only: bool,
    delegation_dir: Path | None,
    strict_delegations: bool,
    seen: frozenset[str] | None,
) -> Report:
    entries = _delegation_entries(instance)
    if not entries:
        return report

    visiting = set(seen or ())
    own = _own_commitment(instance)
    if own is not None:
        visiting.add(own)

    children: list[ChildReport] = []
    warnings = list(report.warnings)
    errors = list(report.errors)
    valid = report.valid

    for index, entry in entries:
        child = _verify_one_delegation(
            index,
            entry,
            parent_path=report.path,
            schema_only=schema_only,
            delegation_dir=delegation_dir,
            strict_delegations=strict_delegations,
            seen=frozenset(visiting),
        )
        children.append(child)
        label = f"delegation [{index}]"
        match child.status:
            case "verified":
                pass
            case "missing":
                warning = f"{label}: {child.detail}"
                warnings.append(warning)
                if strict_delegations:
                    valid = False
                    errors.append(warning)
            case "invalid" | "mismatch":
                valid = False
                errors.append(f"{label}: {child.detail}")
            case _:
                unreachable: Never = child.status
                raise OaepError(f"unhandled delegation status: {unreachable}")

    report.delegations = children
    report.warnings = warnings
    report.errors = errors
    report.valid = valid
    return report


def _verify_one_delegation(
    index: int,
    entry: dict[str, Any],
    *,
    parent_path: Path,
    schema_only: bool,
    delegation_dir: Path | None,
    strict_delegations: bool,
    seen: frozenset[str],
) -> ChildReport:
    agent = entry.get("agent") if isinstance(entry.get("agent"), str) else None
    expected = entry.get("receipt")
    expected_hex = expected if isinstance(expected, str) else None

    if isinstance(expected, dict):
        return ChildReport(
            index=index,
            agent=agent,
            receipt=None,
            status="invalid",
            detail="inline child receipt objects are not supported",
        )

    if expected_hex is not None and hex_key(expected_hex) in seen:
        return ChildReport(
            index=index,
            agent=agent,
            receipt=expected_hex,
            status="invalid",
            detail="delegation cycle",
        )

    child_path = resolve_child_path(
        entry, parent_path=parent_path, delegation_dir=delegation_dir
    )
    if child_path is None:
        return ChildReport(
            index=index,
            agent=agent,
            receipt=expected_hex,
            status="missing",
            detail="child receipt not found beside parent or in --delegation-dir",
        )

    try:
        child_report = verify_path(
            child_path,
            schema_only=schema_only,
            delegation_dir=delegation_dir,
            strict_delegations=strict_delegations,
            _seen=seen,
        )
    except OaepError as exc:
        return ChildReport(
            index=index,
            agent=agent,
            receipt=expected_hex,
            status="invalid",
            path=child_path,
            detail=str(exc),
        )

    computed = child_report.commitment
    matches = (
        computed is not None
        and expected_hex is not None
        and hex_equal(expected_hex, computed)
    )

    if not matches:
        return ChildReport(
            index=index,
            agent=agent,
            receipt=expected_hex,
            status="mismatch",
            path=child_path,
            detail="parent delegations[].receipt does not match SHA-256(JCS(child))",
            commitment_matches=False,
            report=child_report,
        )
    if not child_report.valid:
        return ChildReport(
            index=index,
            agent=agent,
            receipt=expected_hex,
            status="invalid",
            path=child_path,
            detail=_child_invalid_detail(child_report),
            commitment_matches=True,
            report=child_report,
        )
    return ChildReport(
        index=index,
        agent=agent,
        receipt=expected_hex,
        status="verified",
        path=child_path,
        detail=_delegation_ok_detail(agent, child_path),
        commitment_matches=True,
        report=child_report,
    )


def _delegation_ok_detail(agent: str | None, child_path: Path) -> str:
    if agent:
        return f"{agent}  {child_path}"
    return str(child_path)


def _child_invalid_detail(child_report: Report) -> str:
    if child_report.errors:
        return child_report.errors[0]
    return "child Level-0 verify failed"


def _raw_commitment(instance: Any) -> str | None:
    if not isinstance(instance, dict):
        return None
    try:
        return child_receipt_commitment(instance)
    except OaepError:
        return None


def _own_commitment(instance: Any) -> str | None:
    raw = _raw_commitment(instance)
    return hex_key(raw) if raw is not None else None


def _delegation_entries(instance: Any) -> list[tuple[int, dict[str, Any]]]:
    if not isinstance(instance, dict):
        return []
    raw = instance.get("delegations")
    if not isinstance(raw, list):
        return []
    entries: list[tuple[int, dict[str, Any]]] = []
    for index, item in enumerate(raw):
        if isinstance(item, dict):
            entries.append((index, item))
    return entries


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
