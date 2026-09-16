import json
import stat
from pathlib import Path

import pytest

from oaep import cli as cli_mod
from oaep.canonical import from_hex
from oaep.cli import EXIT_INVALID, EXIT_USAGE, EXIT_VALID, main
from oaep.errors import OaepError
from oaep.keys import DID_PREFIX, PRIVATE_KEY_SIZE, AgentKey
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


def _key_paths(tmp_path: Path) -> tuple[Path, Path]:
    return tmp_path / "agent.key", tmp_path / "agent.pub"


def test_keygen_writes_keypair(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    private, public = _key_paths(tmp_path)
    assert main(["keygen", "--private", str(private), "--public", str(public)]) == (
        EXIT_VALID
    )
    out = capsys.readouterr().out
    assert private.is_file()
    assert public.is_file()
    seed = from_hex(private.read_text(encoding="utf-8").strip())
    assert len(seed) == PRIVATE_KEY_SIZE
    key = AgentKey.from_private_bytes(seed)
    ident = public.read_text(encoding="utf-8").strip()
    assert ident.startswith(DID_PREFIX)
    assert ident == key.agent_id()
    assert ident in out
    assert key.public_hex() in out
    assert str(private) in out
    assert key.private_hex() not in out
    assert stat.S_IMODE(private.stat().st_mode) == 0o600


def test_keygen_refuses_overwrite(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    private, public = _key_paths(tmp_path)
    assert main(["keygen", "--private", str(private)]) == EXIT_VALID
    original = private.read_bytes()
    capsys.readouterr()
    assert main(["keygen", "--private", str(private)]) == EXIT_USAGE
    err = capsys.readouterr().err
    assert "refusing to overwrite" in err
    assert "--force" in err
    assert private.read_bytes() == original


def test_keygen_force_overwrites(tmp_path: Path) -> None:
    private, public = _key_paths(tmp_path)
    assert main(["keygen", "--private", str(private)]) == EXIT_VALID
    first = private.read_bytes()
    assert main(["keygen", "--private", str(private), "--force"]) == EXIT_VALID
    assert private.read_bytes() != first
    assert public.is_file()


def test_keygen_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    private, public = _key_paths(tmp_path)
    assert main(["keygen", "--json", "--private", str(private)]) == EXIT_VALID
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"].startswith(DID_PREFIX)
    assert payload["public_key"].startswith("0x")
    assert payload["private_path"] == str(private.resolve())
    assert payload["public_path"] == str(public.resolve())
    assert "private_key" not in payload
    seed = from_hex(private.read_text(encoding="utf-8").strip())
    assert AgentKey.from_private_bytes(seed).agent_id() == payload["id"]


def test_keygen_defaults_to_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli_mod.Path, "home", classmethod(lambda cls: tmp_path))
    assert main(["keygen"]) == EXIT_VALID
    private = tmp_path / ".oaep" / "agent.key"
    public = tmp_path / ".oaep" / "agent.pub"
    assert private.is_file()
    assert public.is_file()
    out = capsys.readouterr().out
    assert DID_PREFIX in out
    assert str(private) in out


def test_keygen_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["keygen", "--help"])
    assert exc.value.code == EXIT_VALID
    out = capsys.readouterr().out
    assert "--force" in out
    assert "--json" in out
    assert "--private" in out
    assert "~/.oaep/agent.key" in out
    assert "did:agent:ed25519" in out
    assert "  0  key written" in out
    assert "  2  usage, refused overwrite" in out


def test_root_help_lists_keygen(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == EXIT_VALID
    out = capsys.readouterr().out
    assert "keygen" in out
    assert "verify" in out


def test_keygen_unknown_option_exits_usage() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["keygen", "--not-a-flag"])
    assert exc.value.code == EXIT_USAGE


def test_keygen_same_paths_exits_usage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "same.key"
    assert main(["keygen", "--private", str(path), "--public", str(path)]) == (
        EXIT_USAGE
    )
    err = capsys.readouterr().err
    assert "must differ" in err
    assert not path.exists()
