# Open Agent Execution Protocol (OAEP)

> Cryptographic receipts for autonomous AI.

| | |
| --- | --- |
| RFP | [Proof an AI Did What It Claims — Verifiable Inference](https://sentient.foundation/product-requests) (Sentient Part Two · 07) |
| Target ecosystem | Sentient |
| Status | Draft |
| Version | 0.1 |
| Repo | [antiserum-ai/oaep](https://github.com/antiserum-ai/oaep) |

Sister of [antiserum](https://github.com/antiserum-ai/antiserum). Different artifact (agent execution, not training-data poison). Same org. Source: author draft, 28 Aug 2026.

---

## 1. Executive Summary

AI agents increasingly perform complex tasks involving models, tools, external data sources, sub-agents, and autonomous decision-making.

Today, users generally have to trust an agent when it claims:

> “I used model X, queried sources A and B, executed tool C, followed policy D, and produced this result.”

There is rarely a portable, independently verifiable way to prove that those actions actually occurred.

Open Agent Execution Protocol (OAEP) is an open protocol for generating cryptographically verifiable execution receipts for AI agents.

An OAEP receipt provides evidence about:

- which agent executed a task
- which model or models participated
- what inputs were committed to
- which tools were invoked
- which agents or sub-agents were delegated work
- which execution environment was used
- what output was produced
- when execution occurred
- which verification mechanisms attest to those claims

OAEP separates execution from trust.

Instead of asking users, agents, or protocols to trust an operator’s description of what happened, OAEP allows them to verify an execution receipt.

The long-term goal is to create a common verification layer for an open economy of autonomous AI agents.

---

## 2. Problem

### 2.1 AI agents are black boxes

Modern agents can execute workflows such as:

```text
User Intent → Planner → Agent → Model → Tool Calls → Sub-Agent → External Data → Model → Result
```

The final result reveals very little about the process that generated it.

An agent may claim that it used a specific model, consulted particular sources, executed a required tool, delegated work to another agent, complied with a policy, ran inside a trusted environment, or performed a required computation.

The user currently has limited ability to verify these claims.

### 2.2 Verifiable inference is only part of the problem

Existing approaches to verifiable AI often focus on proving:

> “Model M executed inference over input X and produced output Y.”

Agentic systems introduce a larger problem. Proving only one inference step does not prove the behavior of the complete system.

What is required is **verifiable agent execution**.

---

## 3. Product Vision

OAEP creates a standard execution receipt for autonomous AI.

The protocol should allow an agent to make a claim such as:

> “Agent A executed task T using Model M, invoked tools X and Y, delegated task Z to Agent B, and produced output O.”

and produce cryptographic evidence supporting that claim.

The verifier should not need to trust the agent operator.

---

## 4. Core Principles

**Open.** The protocol, schemas, SDKs, and reference implementations should be open source.

**Model agnostic.** OAEP should work with open models, proprietary models, local models, and distributed inference systems.

**Agent framework agnostic.** The protocol should not require a specific agent framework. Potential integrations: ROMA, LangGraph, AutoGen, custom agent runtimes, decentralized agent networks.

**Verification agnostic.** Cryptographic commitments, digital signatures, model fingerprints, TEEs, remote attestation, zero-knowledge proofs, deterministic/reproducible execution, consensus-based verification.

**Privacy preserving.** Verification should not require exposing sensitive prompts, private data, model weights, or hidden reasoning.

**Composable.** Execution receipts should be capable of referencing other execution receipts, enabling verification across multi-agent workflows.

---

## 5. Goals

1. Define a standard format for AI execution receipts.
2. Cryptographically bind inputs, outputs, models, agents, tools, and execution metadata.
3. Support verification of individual inference operations.
4. Support verification of complete agent workflows.
5. Support agent-to-agent delegation.
6. Support multiple proof and attestation mechanisms.
7. Provide an SDK for generating and verifying receipts.
8. Provide an initial integration with the Sentient ecosystem.
9. Enable independent verification without trusting the execution operator.

---

## 6. Non-Goals

The initial version of OAEP will not attempt to:

- prove that an AI output is objectively correct
- prove the semantic quality of reasoning
- expose private chain-of-thought
- define a universal agent reputation system
- create a new blockchain
- mandate a specific model runtime
- mandate a specific agent framework
- solve model safety in general

OAEP proves claims about **execution**, not the correctness of the AI’s conclusions.

Dataset poison scanning is [antiserum](https://github.com/antiserum-ai/antiserum), not this repo.

---

## 7. Execution Model

An execution is represented as a graph. Each significant execution event generates a cryptographically committed event. These events form an **execution trace**. The trace is summarized into an **execution receipt**.

---

## 8. Execution Events

An execution trace may contain events including:

```text
TASK_CREATED
AGENT_STARTED
MODEL_INFERENCE_STARTED
MODEL_INFERENCE_COMPLETED
TOOL_CALLED
TOOL_RETURNED
AGENT_DELEGATED
AGENT_RESULT_RECEIVED
POLICY_CHECK
DATA_ACCESSED
OUTPUT_GENERATED
EXECUTION_COMPLETED
```

Each event contains a commitment to its relevant data.

---

## 9. Execution Receipt

A receipt represents a verifiable summary of an agent execution.

```json
{
  "version": "oaep/0.1",
  "execution_id": "0x...",
  "agent": {
    "id": "did:agent:...",
    "version": "1.4.2"
  },
  "task": {
    "commitment": "0x..."
  },
  "models": [
    {
      "identity": "0x...",
      "fingerprint": "0x...",
      "version": "..."
    }
  ],
  "tools": [
    {
      "identity": "0x...",
      "input_commitment": "0x...",
      "output_commitment": "0x..."
    }
  ],
  "delegations": [
    {
      "agent": "did:agent:...",
      "receipt": "0x..."
    }
  ],
  "output": {
    "commitment": "0x..."
  },
  "execution": {
    "environment": "...",
    "started_at": 0,
    "completed_at": 0
  },
  "proofs": [
    {
      "type": "tee",
      "proof": "..."
    }
  ],
  "trace_root": "0x...",
  "signature": "0x..."
}
```

The exact schema will be determined during protocol design.

---

## 10. Execution Trace

Individual events can be committed into a Merkle structure. The receipt contains a `trace_root`, allowing a verifier to prove that a particular event occurred without revealing the entire execution trace.

---

## 11. Agent Identity

OAEP should support cryptographic agent identities (`did:agent:…`). An identity may bind public key, agent version, code hash, policy hash, model configuration, and metadata. Receipts are signed by the executing agent.

---

## 12. Model Identity

OAEP should support cryptographically identifying models via model hashes, model fingerprints, signed model manifests, Sentient Model Fingerprinting, and runtime attestations.

---

## 13. Tool Verification

For each tool call, OAEP may commit to `tool_identity`, `input_hash`, `output_hash`, timestamp, and execution environment. The raw input and output do not necessarily need to be public.

---

## 14. Agent Delegation

Each agent produces its own receipt. The parent receipt references the child receipt. This creates a chain of execution custody across agents.

---

## 15. Verification Levels

| Level | Name | Guarantee |
| --- | --- | --- |
| 0 | Signed execution | This agent claims this execution occurred. |
| 1 | Reproducible execution | The execution can be independently validated. |
| 2 | Trusted execution | Execution occurred inside an attested environment (TDX, SEV-SNP, Nitro, …). |
| 3 | Cryptographic execution proof | The claimed computation was cryptographically verified (zkML, zkVM, …). |
| 4 | Composite verification | Different components use different proof mechanisms in one receipt. |

---

## 16–17. Verification Flow and Result

Verifier checks: agent signature, trace root, model identity, tool commitments, delegation receipts, TEE attestation, cryptographic proofs.

```json
{
  "valid": true,
  "agent_identity": { "verified": true },
  "model_identity": { "verified": true },
  "execution_trace": { "verified": true },
  "tools": { "verified": true },
  "delegations": { "verified": true },
  "attestation": { "type": "tee", "verified": true }
}
```

---

## 18. Architecture

Agent runtime → OAEP instrumentation (model / tool / delegation / policy hooks) → execution trace → receipt builder → attestation and/or proof engine → execution receipt → verifier.

---

## 19. Sentient Integration

- **ROMA** workflows emit OAEP events and a workflow receipt.
- **Sentient Model Fingerprinting** embeds into OAEP model identity.
- **Confidential compute** remote attestation is referenced by the receipt.
- **EvoSkill** lineage: parent skill hash, evolution execution, evaluation, new skill hash, execution receipt.

---

## 20. SDK

Initial SDK: `oaep-sdk`. Candidate languages: TypeScript, Python, Rust.

```typescript
const execution = oaep.start({ agent: agentIdentity, task });
const result = await execution.model.generate({ model, input });
const toolResult = await execution.tool.call({ tool, input });
const receipt = await execution.complete(result);
const verification = await oaep.verify(receipt);
```

---

## 21. CLI

```bash
oaep verify receipt.json
```

```text
OAEP Execution Verification

Agent Identity        ✓
Agent Signature       ✓
Model Fingerprint     ✓
Execution Trace       ✓
Tool Commitments      ✓
Delegation Receipts   ✓
TEE Attestation       ✓

Execution Verified
```

---

## 22. MVP

Demonstrate the complete execution lifecycle without solving every proof mechanism.

**Protocol:** receipt spec, event spec, canonical serialization, commitments, Merkle trace, agent signatures, verification.

**Reference agent:** user task → agent → model → tool → model → result. Every step emits OAEP events.

**Also:** model identity (fingerprint or hash), tool commitments, Agent A → Agent B nested receipts, independent verifier.

---

## 23. MVP Demo

A research agent. User asks it to research topic X using three approved sources and produce a summary. The agent claims an approved model, three sources, sub-agent analysis, and a synthesis. OAEP produces a receipt. A verifier confirms the required workflow actually occurred.

---

## 24. Threat Model

Adversaries may try to falsify traces, claim an unused model, omit tool calls, fabricate tool responses, alter outputs, replay old receipts, impersonate agents, replace agent code, substitute models, forge delegations, or tamper with metadata.

The protocol should document which threats each verification level protects against.

---

## 25. Privacy

Store `prompt_commitment = H(prompt || nonce)`, not the prompt. Selective reveal later if required. Merkle proofs allow selective disclosure of individual events.

---

## 26. Future Extensions

zk agent execution, cryptographically grounded reputation, payments gated on verified receipts, marketplaces that require OAEP, SLA verification, on-chain settlement.

---

## 27. Long-Term Vision

Identity → authorization → execution → verification → reputation → settlement.

OAEP aims to become the execution and verification layer of this stack.

---

## 28. Success Metrics

**Initial:** published spec, SDK, independent verifier, model identity, tool commitments, multi-agent delegation, ROMA adapter, Sentient fingerprint integration, confidential-compute PoC, public repo.

**Later:** OAEP-compatible agents, verified executions, framework integrations, proof backends, third-party verifiers, marketplace/protocol adoption.

---

## 29. Proposed Milestones

1. Protocol specification (v0.1 schema, threat model, commitments)
2. Reference SDK + CLI verifier
3. Agent execution (model/tool hooks, traces, Merkle)
4. Multi-agent verification (delegation, nested receipts)
5. Sentient integration (ROMA, fingerprints, example agent)
6. Strong attestation (at least one of TEE, remote attestation, zkML, zkVM)
7. Public developer release (docs, SDK, verifier, reference agents)

---

## 30. Why OAEP Matters for Open AI

Closed AI providers can establish trust through centralized control. Open AI cannot. Models, agents, compute, tools, and data come from different parties. No single party controls the complete execution environment. Verification infrastructure is a foundational requirement. OAEP is a common mechanism for those independent components to produce verifiable evidence about what occurred.

---

## 31. One-Sentence Pitch

OAEP is an open protocol that gives autonomous AI agents cryptographic receipts proving what models, tools, agents, data, and execution environments actually produced their results.

---

## 32. North Star

Today: **trust the agent.**

OAEP: **verify the agent.**
