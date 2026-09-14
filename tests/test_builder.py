import json
from pathlib import Path

from oaep import verify_inclusion, verify_receipt
from oaep.builder import start
from oaep.demo import build_research_receipt
from oaep.keys import AgentKey
from oaep.merkle import inclusion_proof

SEED = bytes.fromhex("cd" * 32)


def test_round_trip_build_and_verify() -> None:
    key = AgentKey.from_private_bytes(SEED)
    execution = start(
        agent=key,
        task=b"task",
        agent_version="0.0.1",
        environment="test",
        clock=lambda: 10,
        task_nonce=bytes.fromhex("11" * 32),
        start_nonce=bytes.fromhex("22" * 32),
    )
    execution.model_inference("model-a", b"in", b"out", version="1")
    execution.tool_call("search", b"q", b"hits")
    child = {"version": "oaep/0.1", "execution_id": "0x" + "ee" * 32}
    execution.add_delegation("did:agent:child", child)
    receipt = execution.complete(b"result")
    report = verify_receipt(receipt)
    assert report.valid, report.errors
    assert receipt["trace_root"].startswith("0x")
    assert len(receipt["models"]) == 1
    assert len(receipt["tools"]) == 1
    assert len(receipt["delegations"]) == 1
    proof = inclusion_proof(execution.events, 0)
    assert verify_inclusion(execution.events[0], proof, receipt["trace_root"])


def test_demo_receipt_verifies() -> None:
    receipt = build_research_receipt()
    assert verify_receipt(receipt).valid
    assert len(receipt["tools"]) == 3
    assert receipt["agent"]["id"].startswith("did:agent:ed25519:")
    assert build_research_receipt() == receipt


def test_complete_is_idempotent() -> None:
    key = AgentKey.from_private_bytes(SEED)
    execution = start(
        agent=key,
        task=b"t",
        clock=lambda: 1,
        task_nonce=bytes(32),
        start_nonce=bytes(32),
    )
    first = execution.complete(b"out")
    second = execution.complete(b"other")
    assert first == second


def test_example_receipt_matches_demo() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "receipt.json"
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == build_research_receipt()
