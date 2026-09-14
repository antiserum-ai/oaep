"""Ed25519 agent keys and did:agent:ed25519 identifiers."""

from __future__ import annotations

from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from oaep.canonical import from_hex, to_hex
from oaep.errors import OaepError

DID_PREFIX = "did:agent:ed25519:"
PUBLIC_KEY_SIZE = 32
PRIVATE_KEY_SIZE = 32
SIGNATURE_SIZE = 64


class AgentKey:
    """Ed25519 signing key for an OAEP agent."""

    def __init__(self, private_key: Ed25519PrivateKey) -> None:
        self._private = private_key

    @classmethod
    def generate(cls) -> AgentKey:
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def from_private_bytes(cls, seed: bytes) -> AgentKey:
        if len(seed) != PRIVATE_KEY_SIZE:
            raise OaepError("Ed25519 private seed must be 32 bytes")
        return cls(Ed25519PrivateKey.from_private_bytes(seed))

    def public_bytes(self) -> bytes:
        return self._private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    def public_hex(self) -> str:
        return to_hex(self.public_bytes())

    def agent_id(self) -> str:
        return DID_PREFIX + self.public_bytes().hex()

    def agent_dict(self, version: str | None = None) -> dict[str, str]:
        agent = {"id": self.agent_id(), "public_key": self.public_hex()}
        if version is not None:
            agent["version"] = version
        return agent

    def sign(self, message: bytes) -> bytes:
        return self._private.sign(message)


def public_key_from_agent(agent: dict[str, Any]) -> bytes:
    """Resolve a 32-byte Ed25519 public key from ``public_key`` or ``id``."""
    if not isinstance(agent, dict):
        raise OaepError("agent must be a JSON object")
    raw = _raw_public_key(agent)
    if len(raw) != PUBLIC_KEY_SIZE:
        raise OaepError("Ed25519 public key must be 32 bytes")
    return raw


def verify_ed25519(public_key: bytes, signature: bytes, message: bytes) -> None:
    if len(public_key) != PUBLIC_KEY_SIZE:
        raise OaepError("Ed25519 public key must be 32 bytes")
    if len(signature) != SIGNATURE_SIZE:
        raise OaepError("Ed25519 signature must be 64 bytes")
    key = Ed25519PublicKey.from_public_bytes(public_key)
    key.verify(signature, message)


def _raw_public_key(agent: dict[str, Any]) -> bytes:
    public_key = agent.get("public_key")
    if isinstance(public_key, str) and public_key.startswith("0x"):
        return from_hex(public_key)
    ident = agent.get("id")
    if isinstance(ident, str) and ident.startswith(DID_PREFIX):
        hexpart = ident[len(DID_PREFIX) :]
        if not hexpart:
            raise OaepError("did:agent:ed25519 identifier is missing the key")
        try:
            return bytes.fromhex(hexpart)
        except ValueError as exc:
            raise OaepError("did:agent:ed25519 identifier is not hex") from exc
    raise OaepError("agent public key unresolved")
