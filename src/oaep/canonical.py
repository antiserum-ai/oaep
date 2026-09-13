"""RFC 8785 JCS, SHA-256, and OAEP hex/commitment helpers.

Encoding spec: docs/canonical.md.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

from oaep.errors import OaepError

SHA256_SIZE = 32
NONCE_SIZE = 32
IJSON_INT_MAX = 2**53 - 1
_C0_TWO_CHAR = {
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


def as_bytes(value: bytes | str) -> bytes:
    """UTF-8 encode ``str``; pass ``bytes`` through."""
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    raise OaepError(f"expected bytes or str, got {type(value).__name__}")


def to_hex(data: bytes) -> str:
    """``0x`` + lowercase hex."""
    if not isinstance(data, (bytes, bytearray)):
        raise OaepError("to_hex requires bytes")
    return "0x" + bytes(data).hex()


def from_hex(value: str) -> bytes:
    """Decode ``0x``-prefixed hex (either case). Odd length is an error."""
    if not isinstance(value, str) or not value.startswith("0x"):
        raise OaepError("hex value must be a 0x-prefixed string")
    hexpart = value[2:]
    if not hexpart:
        raise OaepError("hex value is empty")
    if len(hexpart) % 2:
        raise OaepError(f"hex value has odd length: {value}")
    try:
        return bytes.fromhex(hexpart)
    except ValueError as exc:
        raise OaepError(f"invalid hex: {value}") from exc


def sha256_digest(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def sha256_hex(data: bytes | str) -> str:
    return to_hex(sha256_digest(as_bytes(data)))


def generate_nonce(n: int = NONCE_SIZE) -> bytes:
    if n < 1:
        raise OaepError("nonce length must be positive")
    return os.urandom(n)


def commit(preimage: bytes | str, nonce: bytes | str) -> str:
    """``SHA-256(preimage || nonce)`` as ``0x`` + 64 lowercase hex chars."""
    return to_hex(sha256_digest(as_bytes(preimage) + as_bytes(nonce)))


def canonical_dumps(value: Any) -> bytes:
    """RFC 8785 JCS bytes (UTF-8). Floats are rejected."""
    return _serialize(value).encode("utf-8")


def receipt_signing_payload(receipt: dict[str, Any]) -> bytes:
    """Canonical JSON of the receipt with the top-level ``signature`` omitted."""
    if not isinstance(receipt, dict):
        raise OaepError("receipt must be a JSON object")
    body = {key: receipt[key] for key in receipt if key != "signature"}
    return canonical_dumps(body)


def _serialize(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        if abs(value) > IJSON_INT_MAX:
            raise OaepError("integer exceeds I-JSON range for canonical JSON")
        return str(value)
    if isinstance(value, str):
        return _serialize_string(value)
    if isinstance(value, list):
        return "[" + ",".join(_serialize(item) for item in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value.keys(), key=_utf16_sort_key)
        parts: list[str] = []
        for key in keys:
            if not isinstance(key, str):
                raise OaepError("canonical JSON object keys must be strings")
            parts.append(_serialize_string(key) + ":" + _serialize(value[key]))
        return "{" + ",".join(parts) + "}"
    raise OaepError(f"cannot canonicalize {type(value).__name__}")


def _serialize_string(text: str) -> str:
    _reject_lone_surrogates(text)
    out = ['"']
    for char in text:
        if char == '"':
            out.append('\\"')
        elif char == "\\":
            out.append("\\\\")
        elif char in _C0_TWO_CHAR:
            out.append(_C0_TWO_CHAR[char])
        elif ord(char) < 0x20:
            out.append(f"\\u{ord(char):04x}")
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def _utf16_sort_key(name: str) -> bytes:
    _reject_lone_surrogates(name)
    return name.encode("utf-16-be")


def _reject_lone_surrogates(text: str) -> None:
    for char in text:
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            raise OaepError("lone Unicode surrogate is not allowed in canonical JSON")
