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

`oaep/0.1` is a draft. Hash functions, signature algorithms, proof payloads, and event `payload` keys are **unstable**. Additive fields may appear without bumping the protocol version. Breaking changes bump the `oaep/x.y` string.

## Evolution

PRD §9: “The exact schema will be determined during protocol design.” Treat these files as the current machine-readable shape, not a frozen standard.

**Level-0** ([PRD §15](../../PRD.md#15-verification-levels)) is a structural check plus signature *presence*: this agent claims this execution occurred. Required receipt fields are only `version`, `execution_id`, `agent`, `task`, `output`, and `signature`. `trace_root`, `proofs`, models, tools, and delegations are optional at Level-0.

This tree is spec-only. It does not implement cryptography, Merkle inclusion, TEE/zk backends, a blockchain, or a hosted verifier.

## See also

- [PRD §8 Execution Events](../../PRD.md#8-execution-events)
- [PRD §9 Execution Receipt](../../PRD.md#9-execution-receipt)
- [PRD §10 Execution Trace](../../PRD.md#10-execution-trace)
- [PRD §15 Verification Levels](../../PRD.md#15-verification-levels)
