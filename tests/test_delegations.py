from pathlib import Path

from oaep.delegations import hash_filenames, resolve_child_path

HASH = "0x" + "ab" * 32


def test_hash_filenames_include_with_and_without_prefix() -> None:
    names = hash_filenames(HASH)
    assert f"{HASH}.json" in names
    assert f"{HASH[2:]}.json" in names


def test_resolve_prefers_path_beside_parent(tmp_path: Path) -> None:
    parent = tmp_path / "parent.json"
    child = tmp_path / "child.json"
    parent.write_text("{}", encoding="utf-8")
    child.write_text("{}", encoding="utf-8")
    found = resolve_child_path(
        {"receipt": HASH, "path": "child.json"},
        parent_path=parent,
        delegation_dir=None,
    )
    assert found == child.resolve()


def test_resolve_hash_name_in_delegation_dir(tmp_path: Path) -> None:
    parent = tmp_path / "parent.json"
    ddir = tmp_path / "kids"
    ddir.mkdir()
    parent.write_text("{}", encoding="utf-8")
    named = ddir / f"{HASH[2:]}.json"
    named.write_text("{}", encoding="utf-8")
    found = resolve_child_path(
        {"receipt": HASH},
        parent_path=parent,
        delegation_dir=ddir,
    )
    assert found == named.resolve()


def test_resolve_missing_returns_none(tmp_path: Path) -> None:
    parent = tmp_path / "parent.json"
    parent.write_text("{}", encoding="utf-8")
    assert (
        resolve_child_path(
            {"receipt": HASH},
            parent_path=parent,
            delegation_dir=None,
        )
        is None
    )
