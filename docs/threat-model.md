# Threat model

Source: [PRD §24](../PRD.md#24-threat-model). Levels: [verification-levels.md](verification-levels.md).

OAEP’s job is a portable receipt of what an agent claims happened. The adversary is anyone who benefits from a receipt that does not match the real run: the operator, a compromised runtime, a malicious sub-agent, or a third party who tampers with a receipt in transit.

This page maps the §24 list onto mitigations by [verification level](verification-levels.md) (PRD §15). A cell is the **intended** protocol guarantee once that level’s mechanism is implemented and checked.

v0 has no TEE or zk backend. Until those land (PRD milestone 6), read every L2 / L3 / L4 cell as a target, not a shipping claim. Level 0 is signed and structural only.

## Assumptions

- Verifiers check signatures, schema, and commitments themselves. They do not trust the operator’s UI.
- Agent keys can be stolen. Level 0 then fails open for that identity.
- Tools and model hosts outside the attestation / proof boundary can still lie.
- Reproducible replay (L1) needs artifacts a second party can actually obtain.

## Assets

The receipt, the execution trace (`trace_root` and events), agent identity, model identity, tool commitments, delegation chain, output commitment, and any attached attestation or proof.

## Mapping

Legend:

| Mark | Meaning |
| --- | --- |
| — | This level does not address the threat. |
| bind | Signature / schema / Merkle consistency. Detects *post-sign* tamper. The signer can still invent the contents. |
| replay-id | Freshness helpers (`execution_id`, task commitment, timestamps) if the verifier enforces uniqueness and task binding. Not a clock oracle. |
| replay | Independent re-execution can catch a lie that is not reproducible. |
| attest | Checked TEE / remote attestation of the instrumented runtime. **Not landed.** |
| prove | Checked zkML / zkVM (or equivalent) of the claimed computation. **Not landed.** |
| mix | L4: use the mark of the mechanism on *that* component. No free upgrade. |

| Threat (PRD §24) | L0 Signed | L1 Reproducible | L2 TEE | L3 zk | L4 Composite |
| --- | --- | --- | --- | --- | --- |
| Falsify traces | bind | replay | attest | prove | mix |
| Claim an unused model | bind | replay | attest | prove | mix |
| Omit tool calls | — | replay* | attest | prove | mix |
| Fabricate tool responses | bind | replay* | attest† | prove† | mix |
| Alter outputs | bind | replay | attest | prove | mix |
| Replay old receipts | replay-id | replay-id | replay-id + attest | replay-id + prove | mix |
| Impersonate agents | bind | bind | bind + attest | bind | mix |
| Replace agent code | bind | replay | attest | prove | mix |
| Substitute models | bind | replay | attest | prove | mix |
| Forge delegations | bind | bind / replay | attest | prove | mix |
| Tamper with metadata | bind | bind | attest | prove | mix |

\* Replay of tool I/O only works if the tool is deterministic or the original I/O is revealed and re-applied as a fixture.  
† TEE / zk cover the tool result that *entered* the attested or proved boundary. A malicious external API can still return fiction.

## Adversaries

### Falsify traces

Invent events that never ran, or drop / rewrite the Merkle tree.

- **L0:** A valid signature binds `trace_root`. After signing, edits fail the signature. The signer can still commit to a fictional tree. Structural Merkle checks catch an inconsistent tree, not a consistent lie.
- **L1:** Re-run should produce the same root if the recipe is complete and deterministic.
- **L2:** Attestation that the instrumentation inside the enclave emitted the events.
- **L3:** Proof of the execution graph in the circuit / VM.

### Claim an unused model

Receipt lists model M; the run used M′.

- **L0:** Model hash / fingerprint in the receipt is a signed claim.
- **L1:** Replay with M; mismatch if you can obtain M.
- **L2:** Measurement or attested load of weights inside the TEE.
- **L3:** zkML statement about those weights.

### Omit tool calls

Skip a required tool and leave it off the trace (completeness).

- **L0:** Cannot prove absence. A policy hash on the agent identity is still a claim.
- **L1:** Replay may show the missing call *if* the same inputs deterministically require it. Agents that sample tools will not.
- **L2 / L3:** Stronger if every tool hook in the measured / proved runtime is instrumented and the policy is inside the boundary.

### Fabricate tool responses

Write a fake `TOOL_RETURNED` payload.

- **L0:** `output_commitment` is the agent’s claim.
- **L1:** Re-call or replay recorded I/O.
- **L2 / L3:** Bind the bytes that crossed into the enclave / circuit. The tool server itself is outside unless it is also attested.

### Alter outputs

Change the user-visible result after the run, or sign a result that was never produced.

- **L0:** Detects tamper of a signed `output.commitment`. Does not stop the signer from committing to a made-up output.
- **L1–L3:** Same escalation as falsified traces: replay, attest, prove.

### Replay old receipts

Present a previous valid receipt as if it were this task.

- **L0 can help** if the verifier binds `execution_id` + task commitment and rejects duplicates / the wrong task. Timestamps in the receipt are signed claims, not a trusted clock.
- Higher levels add environment / proof binding to that same id. They do not replace a verifier-side replay cache or task binding.

### Impersonate agents

Publish a receipt as agent A without A’s key.

- **L0:** This is the one threat signatures are for. Forgery without the key fails. Stolen keys succeed.
- **L2:** Can additionally bind the key to an enclave measurement (key never left the TEE).
- **L3:** Does not, by itself, beat L0 on identity.

### Replace agent code

Run different code / policy than the identity claims.

- **L0:** `agent.version` / code hash is a claim.
- **L1:** Replay with the published code.
- **L2:** Measurement of the binary.
- **L3:** Proof of that program.

### Substitute models

Runtime swaps the model after identity is declared. Same mitigations as “claim an unused model.” Listed separately in §24 because the swap can happen after an honest identity was advertised.

### Forge delegations

Parent cites a child receipt that is fake, unsigned, or for a different task.

- **L0:** Verifier must load the child receipt, check its signature, and check that the parent’s `delegations[].receipt` matches. A parent can still cite a *real* child from another task unless task binding is checked.
- **L1+:** Child verified at its own level; parent–child task binding replayed / attested / proved.

### Tamper with metadata

Edit environment, timestamps, or other receipt fields.

- **L0:** Post-sign edits break the signature. Pre-sign, the operator can put any metadata.
- **L2:** Attested clock / environment fields, within TEE limits.
- **L3:** Metadata included in the proved statement.

## Residual risks (no level closes these)

- Stolen agent keys (unless the key is TEE-bound and the TEE holds).
- Semantic correctness and “good reasoning” (PRD §6).
- Prompt injection that causes a *real* but unwanted run — the receipt can be honest and still harmful.
- TEE side channels, broken attestation roots, or a dishonest proof system.
- Malicious tools or data sources outside the boundary.
- Privacy: commitments hide payloads until reveal; they do not hide the fact that a tool was named if the receipt lists it.

## Reading rule

A mitigation in the L2 / L3 columns applies only after a verifier **checks** the attestation or proof. A `proofs` array on a Level 0 receipt is not a threat mitigation. Do not advertise TEE or zk coverage in this repo until those backends exist.
