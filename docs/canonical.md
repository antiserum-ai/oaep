# oaep/0.1 encoding

This is the encoding `oaep/0.1` uses for hashing and signing. JSON Schema still accepts any `0x`-prefixed hex so older fixtures remain structurally valid. Values **produced** by this package follow the lengths below.

There is no network fetch of schemas, receipts, or keys.

## Canonical JSON

Receipts and events are canonicalized with [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785) JSON Canonicalization Scheme (JCS) before they are hashed or signed.

- UTF-8 bytes, no insignificant whitespace.
- Object keys sorted by UTF-16 code units.
- Arrays keep element order.
- Strings use RFC 8785 escapes (`\"`, `\\`, `\b \t \n \f \r`, other C0 as `\u00xx`).
- Integers in the I-JSON range (`|n| ≤ 2^53 − 1`) as decimal. **Floats are rejected.**
- Lone Unicode surrogates are rejected.

Python: `oaep.canonical_dumps(value) -> bytes`. `oaep.commit(preimage, nonce)`.

## SHA-256 and hex

Hash: SHA-256.

Hex in produced values: `0x` + lowercase hex. A SHA-256 digest is 32 bytes (`0x` + 64 hex chars).

`oaep.canonical` implements JCS, hex, SHA-256, and `commit`.

## Commitments

For task, output, and tool I/O:

```text
commit(preimage, nonce) = SHA-256(preimage || nonce)
```

`preimage` and `nonce` are bytes (`str` is UTF-8). Typical nonce length is 32 bytes.

The receipt stores only the digest. The preimage (prompt, tool I/O) stays off the receipt (PRD §25).

Empty or omitted optional receipt fields are not hashed. They are absent from the signed object.

Event `commitment` uses the same construction: `commit(JCS(payload), event_nonce)` where `event_id` is that nonce as hex.

`execution_id` is `commit(JCS({agent, task}), start_nonce)`.

## Signatures

Algorithm: **Ed25519**.

The signed bytes are `canonical_dumps(receipt without the top-level signature key)`.

- Public key: 32 bytes (`0x` + 64 hex) on `agent.public_key`, and/or `did:agent:ed25519:` + hex (no `0x`).
- Signature: 64 bytes (`0x` + 128 hex) in `receipt.signature`.

A stolen agent key still signs fiction. Level 0 binds the claim to a key; it does not prove the run happened.

## Merkle `trace_root`

Domain-separated (RFC 6962 style):

```text
leaf = SHA-256(0x00 || JCS(event))
node = SHA-256(0x01 || left || right)
```

An odd last node is **promoted** (not hashed with itself). An empty event list has no root.

`oaep.inclusion_proof(events, index)` / `oaep.verify_inclusion(event, proof, root)`.

## What this is not

Not TEE, zk, a blockchain, or a hosted verifier. `--schema-only` skips the signature check and is not a signed Level-0 result.
