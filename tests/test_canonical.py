import pytest

from oaep.canonical import (
    IJSON_INT_MAX,
    canonical_dumps,
    child_receipt_commitment,
    commit,
    from_hex,
    hex_equal,
    receipt_signing_payload,
    sha256_digest,
    to_hex,
)
from oaep.errors import OaepError


def test_key_sort_and_no_whitespace() -> None:
    assert canonical_dumps({"b": 1, "a": 2}) == b'{"a":2,"b":1}'


def test_literals_and_array_order() -> None:
    assert canonical_dumps([None, True, False]) == b"[null,true,false]"


def test_rfc8785_string_escapes() -> None:
    assert canonical_dumps("\n") == b'"\\n"'
    assert canonical_dumps("\t") == b'"\\t"'
    assert canonical_dumps("\x0f") == b'"\\u000f"'
    assert canonical_dumps('"') == b'"\\""'
    assert canonical_dumps("\\") == b'"\\\\"'
    assert canonical_dumps("€") == b'"\xe2\x82\xac"'


def test_bool_is_not_int() -> None:
    assert canonical_dumps({"ok": True}) == b'{"ok":true}'


def test_rejects_float() -> None:
    with pytest.raises(OaepError, match="cannot canonicalize"):
        canonical_dumps(1.5)


def test_rejects_oversize_int() -> None:
    with pytest.raises(OaepError, match="I-JSON"):
        canonical_dumps(IJSON_INT_MAX + 1)


def test_commit_is_sha256_concat() -> None:
    digest = from_hex(commit(b"pre", b"nonce"))
    assert len(digest) == 32
    assert to_hex(digest) == commit("pre", b"nonce")
    assert commit(b"pre", b"nonce") != commit(b"pre", b"other")


def test_receipt_signing_payload_omits_signature() -> None:
    receipt = {"version": "oaep/0.1", "a": 1, "signature": "0xab"}
    assert canonical_dumps({"a": 1, "version": "oaep/0.1"}) == receipt_signing_payload(
        receipt
    )


def test_hex_roundtrip() -> None:
    raw = bytes.fromhex("deadbeef")
    assert from_hex(to_hex(raw)) == raw
    assert from_hex("0xDEAD") == bytes.fromhex("dead")


def test_child_receipt_commitment_is_sha256_of_jcs() -> None:
    child = {"version": "oaep/0.1", "signature": "0xab", "z": 1}
    digest = child_receipt_commitment(child)
    assert digest == to_hex(sha256_digest(canonical_dumps(child)))
    assert hex_equal(digest, digest.upper().replace("0X", "0x"))
    mutated = dict(child)
    mutated["z"] = 2
    assert child_receipt_commitment(mutated) != digest
