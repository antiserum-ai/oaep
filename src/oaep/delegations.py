"""Local (no-network) resolution of nested delegation child receipts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Never

from oaep.errors import OaepError

DelegationStatus = Literal["verified", "invalid", "missing", "mismatch"]


def delegation_mark(status: DelegationStatus) -> str:
    match status:
        case "verified":
            return "✓"
        case "invalid" | "mismatch":
            return "✗"
        case "missing":
            return "⚠"
        case _:
            unreachable: Never = status
            raise OaepError(f"unhandled delegation status: {unreachable}")


def hash_filenames(receipt_hex: str) -> list[str]:
    """Filenames ``--delegation-dir`` and the parent directory map hash → file."""
    if not isinstance(receipt_hex, str) or not receipt_hex:
        return []
    raw = receipt_hex.strip()
    names = [f"{raw}.json", f"{raw.lower()}.json"]
    if raw.lower().startswith("0x") and len(raw) > 2:
        rest = raw[2:]
        names.extend([f"{rest}.json", f"{rest.lower()}.json"])
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def resolve_child_path(
    entry: dict[str, Any],
    *,
    parent_path: Path,
    delegation_dir: Path | None,
) -> Path | None:
    """Locate a child receipt on disk. Never fetches over the network.

    Order: optional ``path`` on the entry (absolute, then beside the parent,
    then under ``--delegation-dir``), then ``{receipt}.json`` /
    ``{receipt without 0x}.json`` beside the parent, then the same names
    under ``--delegation-dir``.
    """
    candidates: list[Path] = []
    hint = entry.get("path")
    parent_dir = _parent_dir(parent_path)

    if isinstance(hint, str) and hint:
        hinted = Path(hint)
        if hinted.is_absolute():
            candidates.append(hinted)
        else:
            if parent_dir is not None:
                candidates.append(parent_dir / hinted)
            candidates.append(Path(hint))
            if delegation_dir is not None:
                candidates.append(delegation_dir / hinted)

    receipt = entry.get("receipt")
    names = hash_filenames(receipt) if isinstance(receipt, str) else []
    search_dirs: list[Path] = []
    if parent_dir is not None:
        search_dirs.append(parent_dir)
    if delegation_dir is not None:
        search_dirs.append(delegation_dir)
    for directory in search_dirs:
        for name in names:
            candidates.append(directory / name)

    seen: set[Path] = set()
    for cand in candidates:
        resolved = _existing_file(cand)
        if resolved is None or resolved in seen:
            continue
        seen.add(resolved)
        return resolved
    return None


def _parent_dir(parent_path: Path) -> Path | None:
    if parent_path.name == "-" and str(parent_path) == "-":
        return None
    parent = parent_path.parent
    if str(parent_path) == "-" or parent_path.as_posix() == "-":
        return None
    return parent


def _existing_file(path: Path) -> Path | None:
    try:
        if path.is_file():
            return path.resolve()
    except OSError:
        return None
    return None
