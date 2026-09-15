"""oaep command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from oaep import __version__
from oaep.errors import OaepError
from oaep.verify import format_text, verify_path

EXIT_VALID = 0
EXIT_INVALID = 1
EXIT_USAGE = 2

EXIT_CODE_HELP = (
    "Exit codes:\n"
    "  0  receipt is valid at Level 0\n"
    "  1  receipt is invalid\n"
    "  2  usage, missing file, or not JSON\n"
    "\n"
    "Default Level 0 checks the local receipt against the packaged oaep/0.1\n"
    "schema and verifies the Ed25519 agent signature. Child receipts listed\n"
    "in delegations are verified the same way when a local file is present\n"
    "(beside the parent, delegations[].path, or --delegation-dir). Missing\n"
    "children warn and continue; --strict-delegations fails. It does not\n"
    "fetch receipts or schemas, and it does not verify TEE attestations or\n"
    "zk proofs. Pass --schema-only to skip the signature check."
)


def entry() -> None:
    sys.exit(main())


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except OaepError as exc:
        print(f"oaep: {exc}", file=sys.stderr)
        return EXIT_USAGE


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oaep",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Open Agent Execution Protocol. Verify a local execution receipt. "
            "Does not download receipts or schemas."
        ),
        epilog=EXIT_CODE_HELP,
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _add_verify(sub)
    return parser


def _add_verify(sub: argparse._SubParsersAction) -> None:
    verify_p = sub.add_parser(
        "verify",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help="verify a local receipt JSON (schema + Ed25519)",
        description=(
            "Load a local OAEP receipt JSON and validate it against the "
            "packaged oaep/0.1 receipt schema (PRD §9 / docs/schema). "
            "Then verify the Ed25519 signature over the canonical receipt "
            "(docs/canonical.md). When delegations are listed, verify each "
            "present local child the same way and check "
            "delegations[].receipt = SHA-256(JCS(child)). Local files only. "
            "No network. No TEE or zk."
        ),
        epilog=EXIT_CODE_HELP,
    )
    verify_p.add_argument(
        "path",
        type=Path,
        help="path to a local receipt JSON file",
    )
    verify_p.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="print the JSON report instead of the text summary",
    )
    verify_p.add_argument(
        "--schema-only",
        action="store_true",
        help="schema check only; do not verify the agent signature",
    )
    verify_p.add_argument(
        "--delegation-dir",
        type=Path,
        metavar="DIR",
        help=(
            "local directory mapping delegations[].receipt (hash) to a "
            "{hash}.json or {hash without 0x}.json child file"
        ),
    )
    verify_p.add_argument(
        "--strict-delegations",
        action="store_true",
        help="fail when a listed child receipt file is missing (default: warn)",
    )
    verify_p.set_defaults(func=_cmd_verify)


def _cmd_verify(args: argparse.Namespace) -> int:
    report = verify_path(
        args.path,
        schema_only=args.schema_only,
        delegation_dir=args.delegation_dir,
        strict_delegations=args.strict_delegations,
    )
    if args.as_json:
        sys.stdout.write(json.dumps(report.to_json_obj(), indent=2) + "\n")
    else:
        sys.stdout.write(format_text(report))
    return EXIT_VALID if report.valid else EXIT_INVALID
