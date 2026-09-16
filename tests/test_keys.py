from oaep.canonical import from_hex
from oaep.keys import PRIVATE_KEY_SIZE, PUBLIC_KEY_SIZE, AgentKey


def test_generate_roundtrip_private_bytes() -> None:
    key = AgentKey.generate()
    seed = key.private_bytes()
    assert len(seed) == PRIVATE_KEY_SIZE
    assert len(key.public_bytes()) == PUBLIC_KEY_SIZE
    loaded = AgentKey.from_private_bytes(seed)
    assert loaded.agent_id() == key.agent_id()
    assert loaded.public_hex() == key.public_hex()
    assert from_hex(key.private_hex()) == seed
