# OAEP

**Open Agent Execution Protocol.** Cryptographic receipts for autonomous AI.

> Verify the agent. Do not trust the operator’s story.

Sentient RFP: [Part Two · 07, Proof an AI Did What It Claims](https://sentient.foundation/product-requests).

**Product:** [PRD.md](PRD.md)

Sister of [antiserum](https://github.com/antiserum-ai/antiserum). Antiserum scans the mix you train on. OAEP proves what an agent actually ran. Same org, different artifact. No shared runtime.

v0 is the spec. Implementation follows the PRD milestones.

**Protocol `oaep/0.1` schemas** (milestone 1):

- [Receipt schema](docs/schema/oaep-receipt.schema.json) — PRD §9
- [Event schema](docs/schema/oaep-event.schema.json) — PRD §8
- [Schema notes + examples](docs/schema/README.md)

```bash
# later
oaep verify receipt.json
```

## License

MIT. See [LICENSE](LICENSE).
