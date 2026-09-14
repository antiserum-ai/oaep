from pathlib import Path

from oaep.verify import load_receipt_schema, verify_path, verify_receipt

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ROOT = Path(__file__).resolve().parents[1]
VALID = FIXTURES / "valid-receipt.json"
VALID_MINIMAL = FIXTURES / "valid-minimal-receipt.json"
INVALID = FIXTURES / "invalid-receipt.json"
TAMPERED = FIXTURES / "tampered-receipt.json"
EXAMPLE = ROOT / "examples" / "receipt.json"
SCHEMA_EXAMPLE = ROOT / "docs" / "schema" / "examples" / "receipt.example.json"
SCHEMA_MINIMAL = ROOT / "docs" / "schema" / "examples" / "receipt.min.json"
LEVEL0_REQUIRED = (
    "version",
    "execution_id",
    "agent",
    "task",
    "output",
    "signature",
)


def test_valid_fixture_is_signed() -> None:
    report = verify_path(VALID)
    assert report.valid
    assert report.errors == []
    assert report.version == "oaep/0.1"
    assert report.level == 0
    assert report.signature_verified is True
    assert all(check.ok for check in report.checks)


def test_example_receipt_is_signed() -> None:
    report = verify_path(EXAMPLE)
    assert report.valid
    assert report.schema_id == "oaep/0.1"
    assert report.signature_verified is True


def test_minimal_level0_receipt_is_valid() -> None:
    report = verify_path(VALID_MINIMAL)
    assert report.valid, report.errors
    omitted = {
        check.name
        for check in report.checks
        if check.ok and check.detail == "omitted"
    }
    assert omitted == {
        "models",
        "tools",
        "delegations",
        "execution",
        "proofs",
        "trace_root",
    }


def test_protocol_schema_examples_are_schema_valid() -> None:
    assert verify_path(SCHEMA_EXAMPLE, schema_only=True).valid
    assert verify_path(SCHEMA_MINIMAL, schema_only=True).valid
    assert not verify_path(SCHEMA_MINIMAL).valid


def test_invalid_fixture_is_structurally_invalid() -> None:
    report = verify_path(INVALID)
    assert not report.valid
    assert report.errors
    failed = {check.name for check in report.checks if not check.ok}
    assert "version" in failed
    assert "signature" in failed
    assert "execution_id" in failed


def test_tampered_receipt_fails_signature() -> None:
    report = verify_path(TAMPERED)
    assert not report.valid
    assert report.signature_verified is False


def test_empty_arrays_are_valid() -> None:
    instance = {
        "version": "oaep/0.1",
        "execution_id": "0x1",
        "agent": {"id": "did:agent:solo", "version": "0.0.1"},
        "task": {"commitment": "0x2"},
        "models": [],
        "tools": [],
        "delegations": [],
        "output": {"commitment": "0x3"},
        "execution": {
            "environment": "test",
            "started_at": 0,
            "completed_at": 1,
        },
        "proofs": [],
        "trace_root": "0x4",
        "signature": "0x5",
    }
    report = verify_receipt(instance, schema_only=True)
    assert report.valid, report.errors


def test_unknown_top_level_fields_are_allowed() -> None:
    instance = {
        "version": "oaep/0.1",
        "execution_id": "0x1",
        "agent": {"id": "did:agent:solo", "version": "0.0.1"},
        "task": {"commitment": "0x2"},
        "models": [],
        "tools": [],
        "delegations": [],
        "output": {"commitment": "0x3"},
        "execution": {
            "environment": "test",
            "started_at": 0,
            "completed_at": 1,
        },
        "proofs": [],
        "trace_root": "0x4",
        "signature": "0x5",
        "future_field": {"ok": True},
    }
    report = verify_receipt(instance, schema_only=True)
    assert report.valid, report.errors


def test_schema_declares_oaep_01() -> None:
    schema = load_receipt_schema()
    assert schema["properties"]["version"]["const"] == "oaep/0.1"
    assert tuple(schema["required"]) == LEVEL0_REQUIRED
    assert "public_key" in schema["$defs"]["agent"]["properties"]


def test_agent_version_is_optional() -> None:
    report = verify_receipt(
        {
            "version": "oaep/0.1",
            "execution_id": "0x1",
            "agent": {"id": "example-agent"},
            "task": {"commitment": "0x2"},
            "output": {"commitment": "0x3"},
            "signature": "0x4",
        },
        schema_only=True,
    )
    assert report.valid, report.errors
