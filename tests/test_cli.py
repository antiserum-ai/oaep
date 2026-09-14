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
