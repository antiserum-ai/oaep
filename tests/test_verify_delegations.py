import json
from pathlib import Path

from oaep.builder import start
from oaep.canonical import child_receipt_commitment, hex_key
from oaep.keys import AgentKey
from oaep.verify import _verify_one_delegation, verify_path, verify_receipt

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "delegations"
PARENT = FIXTURES / "parent.json"
CHILD = FIXTURES / "child.json"
TAMPERED = FIXTURES / "tampered-child.json"
CHILD_SEED = bytes.fromhex("c1" * 32)
PARENT_SEED = bytes.fromhex("d1" * 32)


def _signed_pair(
    tmp_path: Path, *, child_path_hint: str | None = "child.json"
) -> tuple[Path, Path, dict, dict]:
    child_ex = start(
        agent=AgentKey.from_private_bytes(CHILD_SEED),
        task=b"child",
        clock=lambda: 2,
        task_nonce=bytes.fromhex("51" * 32),
        start_nonce=bytes.fromhex("52" * 32),
    )
    child = child_ex.complete(b"child-out")
    parent_ex = start(
        agent=AgentKey.from_private_bytes(PARENT_SEED),
        task=b"parent",
        clock=lambda: 3,
        task_nonce=bytes.fromhex("61" * 32),
        start_nonce=bytes.fromhex("62" * 32),
    )
    parent_ex.add_delegation(
        child["agent"]["id"], child, path=child_path_hint
    )
    parent = parent_ex.complete(b"parent-out")
    child_file = tmp_path / "child.json"
    parent_file = tmp_path / "parent.json"
    child_file.write_text(json.dumps(child), encoding="utf-8")
    parent_file.write_text(json.dumps(parent), encoding="utf-8")
    return parent_file, child_file, parent, child


def test_fixture_parent_and_child_verify() -> None:
    child_report = verify_path(CHILD)
    assert child_report.valid
    assert child_report.signature_verified is True
    report = verify_path(PARENT)
    assert report.valid, report.errors
    assert report.warnings == []
    assert len(report.delegations) == 1
    child = report.delegations[0]
    assert child.status == "verified"
    assert child.commitment_matches is True
    assert child.path == CHILD.resolve()
    assert child.report is not None
    assert child.report.valid


def test_tampered_child_fails(tmp_path: Path) -> None:
    dest = tmp_path / "pair"
    dest.mkdir()
    (dest / "parent.json").write_text(PARENT.read_text(encoding="utf-8"), encoding="utf-8")
    (dest / "child.json").write_text(TAMPERED.read_text(encoding="utf-8"), encoding="utf-8")
    report = verify_path(dest / "parent.json")
    assert not report.valid
    child = report.delegations[0]
    assert child.status == "mismatch"
    assert child.commitment_matches is False
    assert child.report is not None
    assert child.report.signature_verified is False


def test_tampered_signed_child_fails_signature(tmp_path: Path) -> None:
    parent_file, child_file, parent, child = _signed_pair(tmp_path)
    broken = dict(child)
    broken["output"] = {"commitment": "0x" + "ee" * 32}
    child_file.write_text(json.dumps(broken), encoding="utf-8")
    report = verify_path(parent_file)
    assert not report.valid
    assert report.delegations[0].status == "mismatch"
    assert child_receipt_commitment(broken) != parent["delegations"][0]["receipt"]


def test_missing_child_warns_and_continues(tmp_path: Path) -> None:
    _parent_file, child_file, parent, _child = _signed_pair(tmp_path)
    child_file.unlink()
    lone = tmp_path / "lone-parent.json"
    lone.write_text(json.dumps(parent), encoding="utf-8")
    report = verify_path(lone)
    assert report.valid
    assert report.delegations[0].status == "missing"
    assert report.warnings
    assert "not found" in report.warnings[0]


def test_strict_delegations_fails_on_missing(tmp_path: Path) -> None:
    _parent_file, child_file, parent, _child = _signed_pair(tmp_path)
    child_file.unlink()
    lone = tmp_path / "lone-parent.json"
    lone.write_text(json.dumps(parent), encoding="utf-8")
    report = verify_path(lone, strict_delegations=True)
    assert not report.valid
    assert report.delegations[0].status == "missing"
    assert any("not found" in err for err in report.errors)


def test_delegation_dir_hash_mapping(tmp_path: Path) -> None:
    parent_file, child_file, parent, child = _signed_pair(
        tmp_path, child_path_hint=None
    )
    child_file.unlink()
    ddir = tmp_path / "kids"
    ddir.mkdir()
    digest = parent["delegations"][0]["receipt"]
    mapped = ddir / f"{digest[2:]}.json"
    mapped.write_text(json.dumps(child), encoding="utf-8")
    report = verify_path(parent_file, delegation_dir=ddir)
    assert report.valid, report.errors
    assert report.delegations[0].status == "verified"
    assert report.delegations[0].path == mapped.resolve()


def test_in_memory_parent_without_child_is_valid() -> None:
    child = {"version": "oaep/0.1", "execution_id": "0x" + "ee" * 32}
    key = AgentKey.from_private_bytes(PARENT_SEED)
    execution = start(
        agent=key,
        task=b"t",
        clock=lambda: 1,
        task_nonce=bytes(32),
        start_nonce=bytes(32),
    )
    execution.add_delegation("did:agent:child", child)
    receipt = execution.complete(b"out")
    report = verify_receipt(receipt)
    assert report.valid, report.errors
    assert report.delegations[0].status == "missing"


def test_schema_only_still_binds_child_hash() -> None:
    report = verify_path(PARENT, schema_only=True)
    assert report.valid
    assert report.signature_verified is None
    assert report.delegations[0].status == "verified"
    assert report.delegations[0].commitment_matches is True


def test_inline_child_object_is_not_supported() -> None:
    key = AgentKey.from_private_bytes(PARENT_SEED)
    receipt = {
        "version": "oaep/0.1",
        "execution_id": "0x" + "11" * 32,
        "agent": key.agent_dict(),
        "task": {"commitment": "0x" + "22" * 32},
        "delegations": [{"agent": "did:agent:child", "receipt": {"version": "oaep/0.1"}}],
        "output": {"commitment": "0x" + "33" * 32},
        "signature": "0x" + "aa" * 64,
    }
    report = verify_receipt(receipt, schema_only=True)
    assert not report.valid
    assert any(
        child.status == "invalid" and "inline" in child.detail
        for child in report.delegations
    )


def test_delegation_cycle_is_invalid(tmp_path: Path) -> None:
    digest = "0x" + "ab" * 32
    child = _verify_one_delegation(
        0,
        {"agent": "did:agent:child", "receipt": digest, "path": "child.json"},
        parent_path=tmp_path / "parent.json",
        schema_only=False,
        delegation_dir=None,
        strict_delegations=False,
        seen=frozenset({hex_key(digest)}),
    )
    assert child.status == "invalid"
    assert "cycle" in child.detail
