# OAEP JSON Schema

Protocol version: **`oaep/0.1`**.

Machine-readable drafts of the execution receipt ([PRD §9](../../PRD.md#9-execution-receipt)) and the execution-event envelope ([PRD §8](../../PRD.md#8-execution-events), [§10](../../PRD.md#10-execution-trace)).

| File | What |
| --- | --- |
| [oaep-receipt.schema.json](oaep-receipt.schema.json) | Receipt object from PRD §9 |
| [oaep-event.schema.json](oaep-event.schema.json) | Event envelope + PRD §8 type enum |
| [examples/](examples/) | Fixtures that satisfy the schemas |
| [check_schemas.py](check_schemas.py) | Stdlib smoke test (optional `jsonschema`) |

Schemas are JSON Schema **draft-07** so common validators (`jsonschema`, Ajv, and similar) can load them from disk. `$id` URLs are identifiers, not a hosted verifier — do not fetch receipts or schemas over the network to verify.

```bash
python3 docs/schema/check_schemas.py
```

## Versioning

The receipt and event `version` field is the string `oaep/0.1`. That tag is the **protocol** version. It is not the JSON Schema `$schema` draft URI.

`oaep/0.1` is a draft. Proof payloads and event `payload` keys may still grow additively. Hash (SHA-256), canonical JSON (RFC 8785 JCS), Ed25519, and Merkle leaf encoding are specified in [docs/canonical.md](../canonical.md). Breaking changes bump the `oaep/x.y` string.

## Evolution

PRD §9: “The exact schema will be determined during protocol design.” Treat these files as the current machine-readable shape, not a frozen standard.

**Level-0** ([PRD §15](../../PRD.md#15-verification-levels), [canonical.md](../canonical.md)) is schema plus a checked Ed25519 signature: this agent claims this execution occurred. Required receipt fields are only `version`, `execution_id`, `agent`, `task`, `output`, and `signature`. `trace_root`, `proofs`, models, tools, and delegations are optional at schema-only Level-0.

`oaep verify` loads a packaged copy of `oaep-receipt.schema.json` from `src/oaep/schema/`. Those two files must stay byte-identical. Do not invent a second required set in the package.

This tree does not implement TEE/zk backends, a blockchain, or a hosted verifier.

## See also

- [Canonical encoding](../canonical.md)
- [PRD §8 Execution Events](../../PRD.md#8-execution-events)
- [PRD §9 Execution Receipt](../../PRD.md#9-execution-receipt)
- [PRD §10 Execution Trace](../../PRD.md#10-execution-trace)
- [PRD §15 Verification Levels](../../PRD.md#15-verification-levels)
