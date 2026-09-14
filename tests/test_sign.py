import pytest

from oaep.canonical import from_hex
from oaep.errors import OaepError
from oaep.keys import AgentKey
from oaep.sign import sign_receipt, verify_receipt_signature
from oaep.verify import verify_receipt

SEED = bytes.fromhex("ab" * 32)


def _unsigned() -> dict:
    key = AgentKey.from_private_bytes(SEED)
    return {
        "version": "oaep/0.1",
        "execution_id": "0x" + "11" * 32,
        "agent": key.agent_dict(),
        "task": {"commitment": "0x" + "22" * 32},
        "output": {"commitment": "0x" + "33" * 32},
    }


def test_sign_and_verify() -> None:
    key = AgentKey.from_private_bytes(SEED)
    signed = sign_receipt(_unsigned(), key)
    assert len(from_hex(signed["signature"])) == 64
    verify_receipt_signature(signed)
    report = verify_receipt(signed)
    assert report.valid
    assert report.signature_verified is True
    assert report.level_name == "signed"


def test_tamper_fails_signature() -> None:
    key = AgentKey.from_private_bytes(SEED)
    signed = sign_receipt(_unsigned(), key)
    signed["output"] = {"commitment": "0x" + "44" * 32}
    with pytest.raises(OaepError, match="invalid"):
        verify_receipt_signature(signed)
    report = verify_receipt(signed)
    assert not report.valid
    assert report.signature_verified is False


def test_missing_key_fails_closed() -> None:
    receipt = _unsigned()
    receipt["agent"] = {"id": "did:agent:unknown"}
    receipt["signature"] = "0x" + "aa" * 64
    report = verify_receipt(receipt)
    assert not report.valid
    assert report.signature_verified is False
    assert any("unresolved" in err for err in report.errors)


def test_schema_only_skips_signature() -> None:
    receipt = {
        "version": "oaep/0.1",
        "execution_id": "0x01",
        "agent": {"id": "did:agent:example"},
        "task": {"commitment": "0x02"},
        "output": {"commitment": "0x03"},
        "signature": "0x04",
    }
    report = verify_receipt(receipt, schema_only=True)
    assert report.valid
    assert report.signature_verified is None
    assert report.level_name == "structural"
    assert verify_receipt(receipt).valid is False
