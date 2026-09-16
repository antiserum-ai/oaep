# Contributing

The repo is the protocol. Fork it, add a fixture or a test, send a pull request.

PyPI is distribution only. The CLI stays fully offline: no network at runtime, no telemetry, no API keys in the package.

## Dev loop

```bash
python3 -m pip install -e ".[dev]"
make ci
oaep verify examples/receipt.json
```

`make ci` is `make lint` plus `make test` (ruff, then pytest). That is what the pull-request workflow runs.

Keep the stack small. Level-0 verify stays local: it does not fetch receipts or schemas.

## Release (PyPI)

PyPI is the install source only. The CLI stays offline. There is no telemetry.

1. Keep `__version__` in `src/oaep/__init__.py` in sync with the tag you will push. Do not bump it unless the release needs a new version.
2. Tag `vX.Y.Z` (must match `__version__`) and push it. `.github/workflows/publish.yml` builds the sdist and wheel and uploads them with trusted publishing (OIDC). No API token in the repo.

The first published version is **0.1.0**. After the pending publisher exists, tag `v0.1.0`.

### One-time PyPI trusted-publisher setup

The project name is not reserved on PyPI until the first successful upload. A maintainer with a PyPI account clicks once:

1. Sign in at https://pypi.org
2. Open [Publishing](https://pypi.org/manage/account/publishing/) (account sidebar — pending publisher; the project does not exist yet)
3. Under GitHub, add:
   - PyPI project name: `oaep`
   - Owner: `antiserum-ai`
   - Repository name: `oaep`
   - Workflow name: `publish.yml` (filename only)
   - Environment name: `pypi`
4. Click Add.

Until that pending publisher exists, the publish workflow will fail on upload. Do not put a long-lived PyPI token in the repo.

After the first upload, the pending publisher becomes a normal publisher. Later `vX.Y.Z` tags publish the same way. Docs: [Creating a PyPI project with a Trusted Publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).
