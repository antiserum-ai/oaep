"""Merkle tree over canonical event leaves (PRD §10).

Domain-separated like RFC 6962: leaf = SHA-256(0x00 || JCS(event)),
node = SHA-256(0x01 || left || right). An odd last node is promoted
without hashing it with itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Never, Sequence

from oaep.canonical import canonical_dumps, from_hex, sha256_digest, to_hex
from oaep.errors import OaepError

LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"
Side = Literal["left", "right"]


@dataclass(frozen=True)
class ProofStep:
    sibling: str
    side: Side


def leaf_hash(event: dict[str, Any]) -> bytes:
    if not isinstance(event, dict):
        raise OaepError("event must be a JSON object")
    return sha256_digest(LEAF_PREFIX + canonical_dumps(event))


def node_hash(left: bytes, right: bytes) -> bytes:
    return sha256_digest(NODE_PREFIX + left + right)


def merkle_root(events: Sequence[dict[str, Any]]) -> bytes:
    if not events:
        raise OaepError("cannot compute trace_root of an empty event list")
    layer = [leaf_hash(event) for event in events]
    while len(layer) > 1:
        layer = _next_layer(layer)
    return layer[0]


def merkle_root_hex(events: Sequence[dict[str, Any]]) -> str:
    return to_hex(merkle_root(events))


def inclusion_proof(events: Sequence[dict[str, Any]], index: int) -> list[ProofStep]:
    if index < 0 or index >= len(events):
        raise OaepError(f"event index {index} is out of range")
    layer = [leaf_hash(event) for event in events]
    idx = index
    proof: list[ProofStep] = []
    while len(layer) > 1:
        nxt: list[bytes] = []
        i = 0
        while i < len(layer):
            if i + 1 < len(layer):
                left = layer[i]
                right = layer[i + 1]
                if idx == i:
                    proof.append(ProofStep(sibling=to_hex(right), side="right"))
                    idx = len(nxt)
                elif idx == i + 1:
                    proof.append(ProofStep(sibling=to_hex(left), side="left"))
                    idx = len(nxt)
                nxt.append(node_hash(left, right))
                i += 2
            else:
                if idx == i:
                    idx = len(nxt)
                nxt.append(layer[i])
                i += 1
        layer = nxt
    return proof


def verify_inclusion(
    event: dict[str, Any],
    proof: Sequence[ProofStep],
    root: bytes | str,
) -> bool:
    node = leaf_hash(event)
    for step in proof:
        sibling = from_hex(step.sibling)
        match step.side:
            case "left":
                node = node_hash(sibling, node)
            case "right":
                node = node_hash(node, sibling)
            case _:
                unreachable: Never = step.side
                raise OaepError(f"unhandled proof side: {unreachable}")
    root_bytes = from_hex(root) if isinstance(root, str) else root
    return node == root_bytes


def _next_layer(layer: list[bytes]) -> list[bytes]:
    nxt: list[bytes] = []
    i = 0
    while i < len(layer):
        if i + 1 < len(layer):
            nxt.append(node_hash(layer[i], layer[i + 1]))
            i += 2
        else:
            nxt.append(layer[i])
            i += 1
    return nxt
