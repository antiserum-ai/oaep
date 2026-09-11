# OAEP

**Open Agent Execution Protocol.** Cryptographic receipts for autonomous AI.

> Verify the agent. Do not trust the operator’s story.

Sentient RFP: [Part Two · 07, Proof an AI Did What It Claims](https://sentient.foundation/product-requests).

**Product:** [PRD.md](PRD.md)

Sister of [antiserum](https://github.com/antiserum-ai/antiserum). Antiserum scans the mix you train on. OAEP proves what an agent actually ran. Same org, different artifact. No shared runtime.

**Protocol `oaep/0.1` schemas** (milestone 1):

- [Receipt schema](docs/schema/oaep-receipt.schema.json) — PRD §9
- [Event schema](docs/schema/oaep-event.schema.json) — PRD §8
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

`oaep verify` is **Level 0 — structural**. It loads a local receipt JSON and checks it against the packaged `oaep/0.1` receipt schema (the same file as `docs/schema/oaep-receipt.schema.json`). It does not fetch receipts or schemas, and it does not verify signatures, TEE attestations, or zk proofs.

```bash
oaep verify examples/receipt.json
```

Exit `0` when the receipt is structurally valid, `1` when it is invalid, `2` when the file is missing or not JSON.

```text
OAEP Execution Verification

Level 0  structural    schema only (no signature, TEE, or zk)

Receipt              examples/receipt.json
Schema               oaep/0.1
…
✓  Structurally valid
```

Machine-readable report:

```bash
oaep verify --json examples/receipt.json
```

Invalid fixture (exits 1):

```bash
oaep verify tests/fixtures/invalid-receipt.json
```

## Schema

Canonical schemas live under [docs/schema/](docs/schema/). Level-0 required receipt fields are `version`, `execution_id`, `agent`, `task`, `output`, and `signature`. `models`, `tools`, `delegations`, `execution`, `proofs`, and `trace_root` are optional.

`oaep verify` ships that receipt schema as package data (`src/oaep/schema/oaep-receipt.schema.json`) so verify works after `pip install` without a network fetch. The two copies must stay byte-identical.

## Docs

- [Verification levels](docs/verification-levels.md) — Level 0–4: what each proves / does not prove
- [Threat model](docs/threat-model.md) — PRD §24 adversaries mapped to mitigations by level

Level 0 is a signed, structural claim. Do not read TEE or zk into it.

## License

MIT. See [LICENSE](LICENSE).
