import pytest

from oaep.canonical import to_hex
from oaep.errors import OaepError
from oaep.merkle import inclusion_proof, merkle_root, merkle_root_hex, verify_inclusion


def _events(n: int) -> list[dict]:
    return [
        {
            "version": "oaep/0.1",
            "type": "TASK_CREATED",
            "execution_id": "0x" + "aa" * 32,
            "seq": i,
            "commitment": "0x" + f"{i:02x}" * 32,
            "payload": {"i": i},
        }
        for i in range(n)
    ]


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 8])
def test_inclusion_matches_root(n: int) -> None:
    events = _events(n)
    root = merkle_root(events)
    for index in range(n):
        proof = inclusion_proof(events, index)
        assert verify_inclusion(events[index], proof, root)
        assert verify_inclusion(events[index], proof, to_hex(root))


def test_wrong_event_fails_inclusion() -> None:
    events = _events(3)
    root = merkle_root_hex(events)
    proof = inclusion_proof(events, 0)
    assert not verify_inclusion(events[1], proof, root)


def test_empty_tree_rejected() -> None:
    with pytest.raises(OaepError, match="empty"):
        merkle_root([])
