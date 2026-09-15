# Verification levels

Source: [PRD §15](../PRD.md#15-verification-levels). Threat mapping: [threat-model.md](threat-model.md).

A verification level is a claim about **what evidence is attached to a receipt**, not a grade of the agent. Higher is stronger only if that level’s mechanism actually verified. A `proofs` field that nobody checked is still Level 0.

v0 of this repo is the spec plus a Level-0 verifier: schema, JCS, and Ed25519. TEE and zk are PRD milestone 6. Do not treat a `type: "tee"` or `type: "zk"` stub as attestation or a proof.

## Table

| Level | Name (PRD §15) | What it proves | What it does not prove |
| --- | --- | --- | --- |
| 0 | Signed execution | The named agent key signed this receipt. The JSON is structurally valid. Commitments, `trace_root`, and metadata are bound to that signature. Tamper after signing is detectable. | That the events happened. That the claimed model, tools, or code ran. TEE or zk anything. Completeness of the trace. That the output is correct. |
| 1 | Reproducible execution | An independent party can re-run the claimed execution (same inputs, model, tools, code) and match the receipt / `trace_root`. | That the original run happened in a trusted environment. Non-deterministic model or tool I/O. Semantic correctness. |
| 2 | Trusted execution | Remote attestation says the instrumented runtime ran inside a named TEE (TDX, SEV-SNP, Nitro, …) with the measured image. | That the TEE is free of side channels or a broken attestation root. That tools outside the enclave told the truth. zk. Output quality. **Not landed.** |
| 3 | Cryptographic execution proof | A checked zkML / zkVM (or equivalent) proof verifies the claimed computation. | That the proved statement is the one the user cares about. TEE. That conclusions are right. **Not landed.** |
| 4 | Composite verification | Each component is verified at the level of *its* attached, checked mechanism. The receipt as a whole is as strong as the weakest mechanism on the claim you are asking about. | A free upgrade of every claim to the highest mechanism present on the receipt. |

PRD one-liners, kept next to the table so they are not read as more than they are:

| Level | PRD guarantee |
| --- | --- |
| 0 | This agent claims this execution occurred. |
| 1 | The execution can be independently validated. |
| 2 | Execution occurred inside an attested environment. |
| 3 | The claimed computation was cryptographically verified. |
| 4 | Different components use different proof mechanisms in one receipt. |

## Level 0 — Signed execution

What a verifier may say after a Level 0 check:

- The receipt matches the v0.1 schema.
- Required Level 0 fields are present (`version`, `execution_id`, `agent`, commitments, `trace_root`, `signature`, and the rest of the required set).
- The signature verifies under the stated agent public key / DID.
- Merkle / commitment structure is internally consistent when the trace is supplied.
- Each **present local** child listed in `delegations` is checked the same way (schema + Ed25519), and `delegations[].receipt` matches `SHA-256(JCS(child))`. Missing children warn unless `--strict-delegations`. Nested verify is still Level 0.

What it must not say:

- “Execution verified” as if the run were observed.
- “Ran in a TEE.”
- “zk-proved.”
- “Used model M” as a fact rather than a signed claim.

A stolen or malicious agent key signs fiction as easily as fact. Level 0 binds the *story* to a key. It does not audit the story.

The sample CLI in PRD §21 (`TEE Attestation ✓`, `Execution Verified`) is the long-term UX. Default `oaep verify` checks schema + Ed25519 and reports **Signed claim is valid**. It must not print “Execution Verified”. Pass `--schema-only` to skip the signature (that is not a signed Level-0 result).

## Level 1 — Reproducible execution

Needs a replay recipe a second party can actually obtain: model identity, committed inputs (or a selective reveal), tool stubs or recorded I/O, and behavior deterministic enough to compare `trace_root` / output commitment.

A proprietary one-shot call you cannot replay is not Level 1. A failed replay is evidence against the receipt. A successful replay still does not prove the first run happened inside any particular machine.

## Level 2 — Trusted execution

Not landed. Milestone 6. A receipt may reserve a `proofs` entry of type `tee`. Until a verifier checks quote, measurement, and policy, that entry is decoration. Report Level 0.

When it lands: attestation is about the enclave image and the quote. It is not a proof of tool honesty outside the boundary, and it is not zk.

## Level 3 — Cryptographic execution proof

Not landed. Milestone 6. An unchecked `proofs: [{ "type": "zk", ... }]` is Level 0.

A valid proof proves the circuit / VM statement. It does not prove the agent reasoned well (PRD §6).

## Level 4 — Composite verification

Example: model inference under zkML, tool glue signed at Level 0, a child agent under TEE. The verifier reports **per claim**, not a single inflated level. “Composite” is not a synonym for “maximum.”

Until L2/L3 backends exist, a receipt that lists several unsigned stubs is still Level 0.

## Shared non-claims (every level)

From PRD §6. OAEP does not:

- prove the output is objectively correct
- prove semantic quality of reasoning
- expose private chain-of-thought
- replace agent reputation, a chain, or a specific runtime

OAEP proves claims about **execution**, at the strength of the attached and *checked* mechanism.

## How a verifier should label a receipt

1. Start at Level 0. Schema + signature + structural consistency.
2. Promote a **claim** only when that claim’s mechanism verifies.
3. Never promote the whole receipt because one field looks like TEE or zk.
4. Print what failed. Do not print “Execution Verified” for Level 0.
