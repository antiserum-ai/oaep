"""Level-0 receipt signatures (Ed25519 over RFC 8785 JCS)."""

from __future__ import annotations

from typing import Any

from cryptography.exceptions import InvalidSignature

from oaep.canonical import from_hex, receipt_signing_payload, to_hex
from oaep.errors import OaepError
from oaep.keys import AgentKey, SIGNATURE_SIZE, public_key_from_agent, verify_ed25519


def sign_receipt(receipt: dict[str, Any], key: AgentKey) -> dict[str, Any]:
    """Return a copy of ``receipt`` with ``signature`` set."""
    payload = receipt_signing_payload(receipt)
    signed = dict(receipt)
    signed["signature"] = to_hex(key.sign(payload))
    return signed


def verify_receipt_signature(receipt: dict[str, Any]) -> None:
    """Raise ``OaepError`` if the Level-0 signature does not verify."""
    if not isinstance(receipt, dict):
        raise OaepError("receipt must be a JSON object")
    signature_hex = receipt.get("signature")
    if not isinstance(signature_hex, str):
        raise OaepError("signature is missing")
    try:
        signature = from_hex(signature_hex)
    except OaepError as exc:
        raise OaepError(f"signature: {exc}") from exc
    if len(signature) != SIGNATURE_SIZE:
        raise OaepError("Ed25519 signature must be 64 bytes")
    public_key = public_key_from_agent(receipt.get("agent") or {})
    payload = receipt_signing_payload(receipt)
    try:
        verify_ed25519(public_key, signature, payload)
    except InvalidSignature as exc:
        raise OaepError("agent signature is invalid") from exc
