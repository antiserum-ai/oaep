"""oaep command-line interface."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from oaep import __version__
from oaep.errors import OaepError
from oaep.keys import AgentKey
from oaep.verify import format_text, verify_path

EXIT_VALID = 0
EXIT_INVALID = 1
EXIT_USAGE = 2

DEFAULT_KEY_DIRNAME = ".oaep"
DEFAULT_PRIVATE_NAME = "agent.key"
DEFAULT_PUBLIC_NAME = "agent.pub"

VERIFY_EXIT_CODE_HELP = (
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

KEYGEN_EXIT_CODE_HELP = (
    "Exit codes:\n"
    "  0  key written\n"
    "  2  usage, refused overwrite, or write error\n"
    "\n"
    "Writes a local Ed25519 seed to --private and the did:agent:ed25519\n"
    "identity to --public. Defaults: ~/.oaep/agent.key and ~/.oaep/agent.pub.\n"
    "Refuses to overwrite existing files unless --force. Local files only.\n"
    "Does not upload keys or fetch anything."
)

EXIT_CODE_HELP = (
    "Exit codes:\n"
    "  0  success (verify: valid Level-0 receipt; keygen: key written)\n"
    "  1  receipt is invalid (verify only)\n"
    "  2  usage, missing file, not JSON, or refused overwrite\n"
    "\n"
    "Commands stay local. They do not fetch receipts, schemas, or keys,\n"
    "and they do not upload a generated key."
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
            "Open Agent Execution Protocol. Verify a local execution receipt "
            "or generate a local AgentKey. Does not download receipts, "
            "schemas, or keys, and does not upload a generated key."
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
    _add_keygen(sub)
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
        epilog=VERIFY_EXIT_CODE_HELP,
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


def default_private_path() -> Path:
    return Path.home() / DEFAULT_KEY_DIRNAME / DEFAULT_PRIVATE_NAME


def default_public_path() -> Path:
    return Path.home() / DEFAULT_KEY_DIRNAME / DEFAULT_PUBLIC_NAME


def _add_keygen(sub: argparse._SubParsersAction) -> None:
    keygen_p = sub.add_parser(
        "keygen",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help="generate a local Ed25519 AgentKey (no network)",
        description=(
            "Generate a local Ed25519 agent keypair and write the private "
            "seed plus did:agent:ed25519 identity to disk. Uses "
            "AgentKey.generate(). Local files only. No network."
        ),
        epilog=KEYGEN_EXIT_CODE_HELP,
    )
    keygen_p.add_argument(
        "--private",
        type=Path,
        metavar="PATH",
        help="private seed file (default: ~/.oaep/agent.key)",
    )
    keygen_p.add_argument(
        "--public",
        type=Path,
        metavar="PATH",
        help=(
            "public identity file (default: ~/.oaep/agent.pub, or the "
            "sibling .pub of --private)"
        ),
    )
    keygen_p.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing key files",
    )
    keygen_p.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="print JSON instead of the text summary",
    )
    keygen_p.set_defaults(func=_cmd_keygen)


def _key_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.private is None:
        private = default_private_path()
    else:
        private = args.private.expanduser()
    if args.public is not None:
        public = args.public.expanduser()
    elif args.private is not None:
        public = private.with_suffix(".pub")
    else:
        public = default_public_path()
    return private, public


def _refuse_overwrite(paths: list[Path], force: bool) -> None:
    if force:
        return
    for path in paths:
        if path.exists():
            raise OaepError(f"refusing to overwrite {path} (pass --force)")


def _prepare_parent(path: Path) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)


def _write_file(path: Path, data: str, *, mode: int, force: bool) -> None:
    _prepare_parent(path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if not force:
        flags |= os.O_EXCL
    try:
        fd = os.open(path, flags, mode)
    except FileExistsError as exc:
        raise OaepError(f"refusing to overwrite {path} (pass --force)") from exc
    try:
        os.write(fd, data.encode("utf-8"))
        os.fchmod(fd, mode)
    finally:
        os.close(fd)


def _format_keygen_text(payload: dict[str, str]) -> str:
    return (
        "OAEP Agent Key\n"
        "\n"
        f"Agent ID     {payload['id']}\n"
        f"Public key   {payload['public_key']}\n"
        f"Private      {payload['private_path']}\n"
        f"Public       {payload['public_path']}\n"
    )


def _cmd_keygen(args: argparse.Namespace) -> int:
    private_path, public_path = _key_paths(args)
    private_path = private_path.resolve()
    public_path = public_path.resolve()
    if private_path == public_path:
        raise OaepError("private and public paths must differ")
    _refuse_overwrite([private_path, public_path], args.force)
    key = AgentKey.generate()
    _write_file(private_path, key.private_hex() + "\n", mode=0o600, force=args.force)
    _write_file(public_path, key.agent_id() + "\n", mode=0o644, force=args.force)
    payload = {
        "id": key.agent_id(),
        "public_key": key.public_hex(),
        "private_path": str(private_path),
        "public_path": str(public_path),
    }
    if args.as_json:
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    else:
        sys.stdout.write(_format_keygen_text(payload))
    return EXIT_VALID
