# OAEP

**Open Agent Execution Protocol.** Cryptographic receipts for autonomous AI.

> Verify the agent. Do not trust the operator’s story.

Sentient RFP: [Part Two · 07, Proof an AI Did What It Claims](https://sentient.foundation/product-requests).

**Product:** [PRD.md](PRD.md)

Sister of [antiserum](https://github.com/antiserum-ai/antiserum). Antiserum scans the mix you train on. OAEP proves what an agent actually ran. Same org, different artifact. No shared runtime.

v0 is the spec. Implementation follows the PRD milestones.

```bash
# later
oaep verify receipt.json
```

## Docs

- [Verification levels](docs/verification-levels.md) — Level 0–4: what each proves / does not prove
- [Threat model](docs/threat-model.md) — PRD §24 adversaries mapped to mitigations by level

Level 0 is a signed, structural claim. Do not read TEE or zk into it.

## License

MIT. See [LICENSE](LICENSE).
