"""GitHub Pages site (issue #15). Docs only; no hosted verifier."""

from __future__ import annotations

import importlib.util
import re
from argparse import ArgumentParser
from pathlib import Path

from oaep.cli import _parser

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_pages.py"
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
INDEX_MD = ROOT / "docs" / "index.md"


def _load():
    spec = importlib.util.spec_from_file_location("build_pages", BUILDER)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cli_flags() -> set[str]:
    flags: set[str] = set()

    def walk(parser: ArgumentParser) -> None:
        for action in parser._actions:
            flags.update(opt for opt in action.option_strings if opt.startswith("--"))
        sub = getattr(parser, "_subparsers", None)
        if sub is None:
            return
        for group in sub._group_actions:
            for child in group.choices.values():
                walk(child)

    walk(_parser())
    return flags


def test_markdown_tables_and_fences() -> None:
    pages = _load()
    html = pages.render_markdown(
        "| Level | Name |\n| --- | --- |\n| 0 | `signed` |\n\n"
        "See [verification-levels.md](verification-levels.md).\n\n"
        "```bash\noaep verify examples/receipt.json\n```\n",
        depth=0,
    )
    assert "<table>" in html
    assert "<code>signed</code>" in html
    assert 'href="verification-levels.html"' in html
    assert "<pre><code" in html
    assert "oaep verify examples/receipt.json" in html


def test_backslash_star_footnotes_are_not_emphasis() -> None:
    pages = _load()
    html = pages.render_markdown(
        r"\* Replay of tool I/O only works if recorded." + "\n",
        depth=0,
    )
    assert "* Replay of tool I/O" in html
    assert "<em>" not in html


def test_repo_markdown_links_go_to_github() -> None:
    pages = _load()
    html = pages.render_markdown(
        "[PRD](../PRD.md#15-verification-levels)\n",
        depth=0,
    )
    assert (
        "https://github.com/antiserum-ai/oaep/blob/main/PRD.md"
        "#15-verification-levels" in html
    )


def test_build_writes_landing_and_deep_docs(tmp_path: Path) -> None:
    pages = _load()
    out = tmp_path / "pages"
    pages.build(out)

    landing = (out / "index.html").read_text(encoding="utf-8")
    assert "Cryptographic receipts for autonomous AI" in landing
    assert "pip install oaep" in landing
    assert "pip install -e" in landing
    assert "git+https://github.com/antiserum-ai/oaep.git" in landing
    assert "oaep verify examples/receipt.json" in landing
    assert "tests/fixtures/delegations/parent.json" in landing
    assert "--delegation-dir" in landing
    assert "--strict-delegations" in landing
    assert "Signed claim is valid" in landing
    assert "Execution Verified" not in landing
    assert "Level 0" in landing
    assert "no TEE or zk" in landing
    assert "verification-levels.html" in landing
    assert "threat-model.html" in landing
    assert "canonical.html" in landing
    assert "oaep-receipt.schema.json" in landing
    assert "sentient.foundation/product-requests" in landing
    assert "PRD.md" in landing
    assert "antiserum" in landing.lower()
    assert "different artifact" in landing
    assert "No API keys" in landing
    assert "does not verify receipts" in landing
    assert 'href="site.css"' in landing
    assert (out / "site.css").is_file()
    assert (out / ".nojekyll").is_file()
    assert (out / "oaep-receipt.schema.json").is_file()
    assert (out / "oaep-event.schema.json").is_file()

    levels = (out / "verification-levels.html").read_text(encoding="utf-8")
    assert "Signed execution" in levels
    assert "<table>" in levels
    assert "Do not treat a" in levels or "signed claim" in levels.lower()

    threat = (out / "threat-model.html").read_text(encoding="utf-8")
    assert "Falsify traces" in threat
    assert "<table>" in threat

    canonical = (out / "canonical.html").read_text(encoding="utf-8")
    assert "RFC 8785" in canonical
    assert "Ed25519" in canonical


def test_landing_flags_exist_on_cli() -> None:
    known = _cli_flags()
    text = INDEX_MD.read_text(encoding="utf-8")
    mentioned = set(re.findall(r"--[a-z][a-z0-9-]+", text))
    invented = mentioned - known - {"--help", "--version"}
    assert not invented, f"landing invents flags: {sorted(invented)}"


def test_landing_does_not_pitch_hosted_product() -> None:
    text = INDEX_MD.read_text(encoding="utf-8").lower()
    assert "no api keys" in text
    assert "does not verify receipts" in text
    assert "sign up" not in text
    assert "dashboard" not in text
    assert "do not read a green level-0 result as" in text
    assert "tee attestation" in text or "tee or zk" in text


def test_pyproject_homepage_is_pages_url() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'Homepage = "https://antiserum-ai.github.io/oaep/"' in text
    assert 'Repository = "https://github.com/antiserum-ai/oaep"' in text


def test_pages_workflow_deploys_without_touching_ci() -> None:
    text = PAGES_WORKFLOW.read_text(encoding="utf-8")
    assert "actions/upload-pages-artifact@" in text
    assert "actions/deploy-pages@" in text
    assert "scripts/build_pages.py" in text
    assert "pages: write" in text
    assert "id-token: write" in text
    assert "branches: [main]" in text
    ci = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "deploy-pages" not in ci
