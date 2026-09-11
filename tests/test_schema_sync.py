from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "schema" / "oaep-receipt.schema.json"
PACKAGED = ROOT / "src" / "oaep" / "schema" / "oaep-receipt.schema.json"


def test_docs_schema_matches_packaged_copy() -> None:
    assert DOCS.is_file()
    assert PACKAGED.is_file()
    assert DOCS.read_text(encoding="utf-8") == PACKAGED.read_text(encoding="utf-8")
