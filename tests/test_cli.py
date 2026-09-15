import json
from pathlib import Path

import pytest

from oaep.cli import EXIT_INVALID, EXIT_USAGE, EXIT_VALID, main
from oaep.errors import OaepError
from oaep.verify import verify_path

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ROOT = Path(__file__).resolve().parents[1]
VALID = FIXTURES / "valid-receipt.json"
INVALID = FIXTURES / "invalid-receipt.json"
SCHEMA_MIN = ROOT / "docs" / "schema" / "examples" / "receipt.min.json"
DELEG_PARENT = FIXTURES / "delegations" / "parent.json"
DELEG_TAMPERED = FIXTURES / "delegations" / "tampered-child.json"


def test_verify_valid_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["verify", str(VALID)]) == EXIT_VALID
    out = capsys.readouterr().out
    assert "Signed claim is valid" in out
    assert "Level 0" in out
    assert "ed25519" in out
    assert "oaep/0.1" in out


def test_verify_invalid_exits_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["verify", str(INVALID)]) == EXIT_INVALID
    out = capsys.readouterr().out
    assert "Signed claim is invalid" in out
    assert "Errors" in out


def test_verify_schema_only_unsigned(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["verify", "--schema-only", str(SCHEMA_MIN)]) == EXIT_VALID
    out = capsys.readouterr().out
    assert "Structurally valid" in out
    assert "schema only" in out
    assert main(["verify", str(SCHEMA_MIN)]) == EXIT_INVALID


def test_verify_missing_exits_usage(capsys: pytest.CaptureFixture[str]) -> None:
    missing = FIXTURES / "does-not-exist.json"
    assert main(["verify", str(missing)]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert "receipt not found" in err


def test_verify_not_json_exits_usage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    junk = tmp_path / "junk.json"
    junk.write_text("this is not json", encoding="utf-8")
    assert main(["verify", str(junk)]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert "not valid JSON" in err


def test_verify_json_flag(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["verify", "--json", str(VALID)]) == EXIT_VALID
    out = capsys.readouterr().out
    assert '"valid": true' in out
    assert '"level": 0' in out
    assert '"signature_verified": true' in out


def test_verify_path_raises_on_missing() -> None:
    with pytest.raises(OaepError, match="receipt not found"):
        verify_path(FIXTURES / "nope.json")


def test_verify_nested_parent_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["verify", str(DELEG_PARENT)]) == EXIT_VALID
    out = capsys.readouterr().out
    assert "Delegation [0]" in out
    assert "✓" in out
    assert "Signed claim is valid" in out


def test_verify_nested_json_lists_child(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["verify", "--json", str(DELEG_PARENT)]) == EXIT_VALID
    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True
    assert payload["delegations"][0]["status"] == "verified"
    assert payload["delegations"][0]["commitment_matches"] is True


def test_verify_strict_delegations_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lone = tmp_path / "parent.json"
    lone.write_text(DELEG_PARENT.read_text(encoding="utf-8"), encoding="utf-8")
    assert main(["verify", str(lone)]) == EXIT_VALID
    out = capsys.readouterr().out
    assert "⚠" in out
    assert "Warnings" in out
    assert main(["verify", "--strict-delegations", str(lone)]) == EXIT_INVALID
    out = capsys.readouterr().out
    assert "Signed claim is invalid" in out


def test_verify_delegation_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    parent_obj = json.loads(DELEG_PARENT.read_text(encoding="utf-8"))
    child_text = (FIXTURES / "delegations" / "child.json").read_text(encoding="utf-8")
    digest = parent_obj["delegations"][0]["receipt"]
    parent = tmp_path / "parent.json"
    parent.write_text(DELEG_PARENT.read_text(encoding="utf-8"), encoding="utf-8")
    ddir = tmp_path / "kids"
    ddir.mkdir()
    (ddir / f"{digest[2:]}.json").write_text(child_text, encoding="utf-8")
    assert main(["verify", "--delegation-dir", str(ddir), str(parent)]) == EXIT_VALID
    out = capsys.readouterr().out
    assert "Signed claim is valid" in out


def test_verify_tampered_child_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dest = tmp_path / "pair"
    dest.mkdir()
    (dest / "parent.json").write_text(
        DELEG_PARENT.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (dest / "child.json").write_text(
        DELEG_TAMPERED.read_text(encoding="utf-8"), encoding="utf-8"
    )
    assert main(["verify", str(dest / "parent.json")]) == EXIT_INVALID
    out = capsys.readouterr().out
    assert "Delegation [0]" in out
    assert "Signed claim is invalid" in out
