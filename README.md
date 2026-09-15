# OAEP

**Open Agent Execution Protocol.** Cryptographic receipts for autonomous AI.

> Verify the agent. Do not trust the operator’s story.

Sentient RFP: [Part Two · 07, Proof an AI Did What It Claims](https://sentient.foundation/product-requests).

**Product:** [PRD.md](PRD.md)

Sister of [antiserum](https://github.com/antiserum-ai/antiserum). Antiserum scans the mix you train on. OAEP proves what an agent actually ran. Same org, different artifact. No shared runtime.

**Protocol `oaep/0.1`:**

- [Receipt schema](docs/schema/oaep-receipt.schema.json) — PRD §9
- [Event schema](docs/schema/oaep-event.schema.json) — PRD §8
- [Canonical encoding](docs/canonical.md) — JCS, SHA-256 commitments, Ed25519, Merkle
- [Schema notes + examples](docs/schema/README.md)

## Install

Python 3.11+. Local checkout only.

```bash
pip install -e .
```

Dev extras (pytest, ruff):

```bash
pip install -e ".[dev]"
```

## Verify a receipt

`oaep verify` is **Level 0 — signed**. It loads a local receipt JSON, checks it against the packaged `oaep/0.1` schema, and verifies the Ed25519 signature over RFC 8785 JCS of the receipt with `signature` omitted. When `delegations` are listed, it verifies each **present local** child the same way and checks that `delegations[].receipt` is `SHA-256(JCS(child))` (including the child’s signature). It does not fetch receipts or schemas, and it does not verify TEE attestations or zk proofs.

```bash
oaep verify examples/receipt.json
```

Exit `0` when the receipt is a valid signed Level-0 claim, `1` when it is invalid, `2` when the file is missing or not JSON.

```text
OAEP Execution Verification

Level 0  signed        schema + ed25519 (no TEE or zk)

Receipt              examples/receipt.json
Schema               oaep/0.1
…
Agent Signature      ✓  ed25519

✓  Signed claim is valid
```

Schema only (no signature check):

```bash
oaep verify --schema-only docs/schema/examples/receipt.min.json
```

Machine-readable report:

```bash
oaep verify --json examples/receipt.json
```

Invalid fixture (exits 1):

```bash
oaep verify tests/fixtures/invalid-receipt.json
```

Nested child receipts (local files only). The verifier looks beside the parent, at optional `delegations[].path`, and in `--delegation-dir` for `{receipt}.json` or `{receipt without 0x}.json`. Missing children warn and continue; `--strict-delegations` fails.

```bash
oaep verify tests/fixtures/delegations/parent.json
oaep verify --delegation-dir tests/fixtures/delegations tests/fixtures/delegations/parent.json
oaep verify --strict-delegations tests/fixtures/delegations/parent.json
```

## Build a receipt

```python
from oaep import AgentKey, start, verify_receipt

key = AgentKey.generate()
execution = start(agent=key, task=b"research topic X")
execution.model_inference("model-a", b"prompt", b"plan")
execution.tool_call("search", b"query", b"hits")
receipt = execution.complete(b"summary")
assert verify_receipt(receipt).valid
```

Deterministic example (writes the same bytes as `examples/receipt.json`):

```bash
python -m oaep.demo
```

## Schema

Canonical schemas live under [docs/schema/](docs/schema/). Level-0 required receipt fields are `version`, `execution_id`, `agent`, `task`, `output`, and `signature`. `models`, `tools`, `delegations`, `execution`, `proofs`, and `trace_root` are optional for schema-only checks. Produced receipts include `agent.public_key` (`did:agent:ed25519:…`) and a Merkle `trace_root`.

`oaep verify` ships the receipt schema as package data (`src/oaep/schema/oaep-receipt.schema.json`) so verify works after `pip install` without a network fetch. The two copies must stay byte-identical.

## Docs

- [Canonical encoding](docs/canonical.md) — what is hashed and signed
- [Verification levels](docs/verification-levels.md) — Level 0–4: what each proves / does not prove
- [Threat model](docs/threat-model.md) — PRD §24 adversaries mapped to mitigations by level

Level 0 is a signed, structural claim. Do not read TEE or zk into it.

## License

MIT. See [LICENSE](LICENSE).
