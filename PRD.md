# OAEP — Verifiable Inference

Working name: **OAEP** (Open Attested Execution Proof). Repo: `antiserum-ai/oaep`.
Drafted 28 Aug 2026 (EST) by Antiserum PM after a ChatGPT highlight share that only named `OAEP_PRD.md`. The original file body was not in the share. This PRD is written from Sentient Foundation Part Two · 07 and Antiserum’s local-first rules. Replace sections if the original markdown lands.

**One line:** A local receipt that this output came from this model and this code, on hardware nobody swapped.

Grant track. Not investment. Sister of [antiserum](https://github.com/antiserum-ai/antiserum), not a feature inside it.

---

## Why this exists

When a model denies a loan, reads a scan, or drops a resume, the operator says “a model decided.” You cannot see which model ran, or whether the careful one they advertised is the one they used. Sentient named that hole as [Part Two · 07, Proof an AI Did What It Claims](https://sentient.foundation/product-requests).

It is now possible to generate a cryptographic receipt that an output came from a specific model and the exact code claimed, on hardware no one can secretly swap. OAEP is that receipt, as a public repo you can clone and run. The proof the world relies on cannot itself be a black box.

Antiserum answers “is this mix safe to learn from?” OAEP answers “did this run do what they said?” Same immune-system idea, different artifact. Do not merge the codebases.

---

## Who it is for

- Researchers and indie labs who already ship open models and need a paste-into-a-model-card proof.
- Anyone consuming an inference API who should not have to take the host’s word.
- Sentient / open-AI builders who need Part Two · 07 as a repo, not a whitepaper.

Not: a hosted “trust us” notary. Not a marketplace. Not a login.

---

## Sentient bars (every product they fund)

| Bar | How OAEP earns it |
| --- | --- |
| Open | MIT. Spec, prover, verifier, and receipt schema in this repo. A stranger can verify without asking us. |
| Yours to keep | Run the prover on your machine or your enclave. No account. Open weights and open code cannot be revoked. |
| Accessible | v0 verifier is a laptop CLI. Proving may need an enclave or a small GPU; say so honestly. Do not require a datacenter to *check* a receipt. |
| Good for humanity | The decisions that bend a life become auditable. |
| Private by default | The sensitive prompt need not leave the box. A receipt can commit to input hashes, not plaintext. |
| Empowering, not extractive | No rent on the proof. No phone-home. |

---

## v0 (must ship)

A stranger can:

1. Run a tiny reference model (or a recorded fixture) through `oaep prove`.
2. Get a **deterministic receipt**: model identity (hash / signed artifact), code identity (git / image digest), input commitment, output, proof, prover version.
3. Run `oaep verify receipt.json` on another machine with no network and get the same yes/no.
4. Paste the receipt into a model card or an Antiserum-style “what ran” note.

v0 proof system: pick the weakest honest scheme that still binds model+code+output. Candidate order (decide in-repo, do not pretend TEE if we do not have one):

1. **Reproducible local rerun** — same bytes in, same output, hashed. Honest, limited (nondeterministic sampling, GPU noise).
2. **Attested enclave** — Sentient Enclaves / a documented TEE, optional extra.
3. **SNARK / folding** — later. Do not block v0 on a proving system that does not run.

Receipt schema lives in `docs/receipt.md`. Unknown fields ignored. Same discipline as Antiserum’s feed: a machine can match it.

---

## Not v0

- Hosted judge, login, marketplace, remote “latest” fetch
- Proving a closed API you do not control
- Weight-level backdoor inversion (Antiserum #21 / Neural Cleanse)
- Dataset poison scanning (that is `antiserum-ai/antiserum`)
- OML fingerprinting / monetization (Sentient Part Three · 03, different RFP)
- Images / audio as first-class artifacts
- “We verified the model is aligned”

A clean OAEP receipt means: this output is bound to this model bytes and this code bytes. It does **not** mean the model is safe, unbiased, or unpoisoned. Point at Antiserum for the mix.

---

## How it sits next to Antiserum

```
mix  --antiserum scan-->  corpus receipt
model+code+input  --oaep prove-->  inference receipt
```

Same org, same local-first promise, different repo. Shared language (receipt, hash, version, no keys). No shared runtime.

---

## Grant ask (if this is the Sentient application)

Track: grant. Amount: decide before Typeform (Antiserum is asking $50k on 05; do not collide the two asks without a sentence).

Unlock:

1. A public reference prove/verify that a stranger can run in one command.
2. A receipt schema other tools can emit.
3. One honest path from “I ran it on my laptop” to “an enclave attested this,” still offline-verifiable.

Without a grant this stays a spec. With it, Part Two · 07 is a repo someone else will use.

---

## Success

- `oaep verify` on a fixture receipt exits 0 with no network.
- A second machine gets the same verdict from the same file.
- README states the non-claims in one screen.
- No API key in the happy path.

---

## Open

- Expand OAEP if the original ChatGPT file used a different phrase.
- v0 proof backend (rerun vs TEE).
- Whether receipts embed Antiserum `dataset_hash` when the operator also scanned the mix.
