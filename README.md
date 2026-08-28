# OAEP

Open attested execution proof. A local receipt that this output came from this model and this code.

Sister of [antiserum](https://github.com/antiserum-ai/antiserum). Different artifact. Same local-first promise: no login, no hosted judge, no API keys to verify.

**Product:** [PRD.md](PRD.md)

v0 is not implemented yet. The repo is the spec.

```
# later
oaep prove  --model ./weights --code ./server --in prompt.txt --out receipt.json
oaep verify receipt.json
```

Sentient RFP: [Part Two · 07, Proof an AI Did What It Claims](https://sentient.foundation/product-requests).

## License

MIT. See [LICENSE](LICENSE).
