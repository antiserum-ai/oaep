---
title: OAEP — cryptographic receipts for autonomous AI
---

# Cryptographic receipts for autonomous AI

**Open Agent Execution Protocol.** An agent signs a receipt of what it claims ran. Anyone with the file can check the schema and the Ed25519 signature. They do not have to trust the operator’s story.

> Verify the agent. Do not trust the operator’s story.

```bash
oaep verify examples/receipt.json
```

This site is public documentation. It does not verify receipts, accept uploads, or take API keys. Verify stays on your machine.

<div class="constraints">

## Level 0 — signed claim, not TEE or zk

`oaep verify` is **Level 0 — signed**. It checks the packaged `oaep/0.1` schema and the Ed25519 signature over RFC 8785 JCS of the receipt with `signature` omitted. That binds the JSON to an agent key. It does not prove the events happened, that a claimed model or tool ran, or anything about TEE attestation or zk proofs.

A stolen or malicious agent key signs fiction as easily as fact. Do not read a green Level-0 result as “execution verified.”

Full table: [verification-levels.md](verification-levels.md). Threat mapping: [threat-model.md](threat-model.md).

</div>

## Sister note

Sister of [antiserum](https://github.com/antiserum-ai/antiserum) ([pages](https://antiserum-ai.github.io/antiserum/)). Antiserum scans the mix you train on. OAEP proves what an agent actually ran. Same org, different artifact. No shared runtime.

## Install

Python 3.11+. Prefer PyPI:

```bash
pip install oaep
```

That exposes the `oaep` command (`python3 -m oaep` also works). No API keys. PyPI is the install source only. Verify stays offline — no network at runtime, no telemetry.

Contributors, from this repo (editable, with test tools):

```bash
pip install -e ".[dev]"
```

A git install without cloning:

```bash
pip install "oaep @ git+https://github.com/antiserum-ai/oaep.git"
```

Release and trusted-publisher steps: [CONTRIBUTING.md](../CONTRIBUTING.md).

## Verify a receipt

Local file only. The verifier does not fetch receipts or schemas.

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

Schema only (no signature check — not a signed Level-0 result):

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

### Nested local delegation

When `delegations` are listed, the verifier checks each **present local** child the same way (schema + Ed25519) and that `delegations[].receipt` is `SHA-256(JCS(child))` (including the child’s signature). It looks beside the parent, at optional `delegations[].path`, and in `--delegation-dir` for `{receipt}.json` or `{receipt without 0x}.json`. Missing children warn and continue; `--strict-delegations` fails. Nested verify is still Level 0. No network fetch.

```bash
oaep verify tests/fixtures/delegations/parent.json
oaep verify --delegation-dir tests/fixtures/delegations tests/fixtures/delegations/parent.json
oaep verify --strict-delegations tests/fixtures/delegations/parent.json
```

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Receipt is valid at Level 0 |
| 1 | Receipt is invalid |
| 2 | Usage, missing file, or not JSON |

`oaep verify --help` prints the same contract. `--version` reports the package version.

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

## Sentient and the PRD

OAEP answers [Sentient RFP Part Two · 07, Proof an AI Did What It Claims](https://sentient.foundation/product-requests). The product document is [PRD.md](../PRD.md). Protocol tag: `oaep/0.1`.

## Deep docs

| Doc | What it is |
| --- | --- |
| [verification-levels.md](verification-levels.md) | Level 0–4: what each proves / does not prove |
| [threat-model.md](threat-model.md) | PRD §24 adversaries mapped to mitigations by level |
| [canonical.md](canonical.md) | JCS, SHA-256 commitments, Ed25519, Merkle |
| [oaep-receipt.schema.json](oaep-receipt.schema.json) | Receipt object (PRD §9). Local file; no hosted registry. |
| [oaep-event.schema.json](oaep-event.schema.json) | Event envelope (PRD §8) |
| [schema notes](schema/README.md) | Versioning and Level-0 required fields |
| [PRD.md](../PRD.md) | Product requirements |
| [README](https://github.com/antiserum-ai/oaep/blob/main/README.md) | Full CLI contract on `main` |

`oaep verify` ships the receipt schema as package data so verify works after `pip install` without a network fetch.

## What this is not

A signed receipt is a claim bound to a key. It is not a TEE quote, not a zk proof, not a hosted verifier, and not proof that the output is correct. Dataset poison scanning is [antiserum](https://github.com/antiserum-ai/antiserum), not this repo.

Source: [github.com/antiserum-ai/oaep](https://github.com/antiserum-ai/oaep). MIT.
