"""Deterministic research-agent receipt used as the repo example."""

from __future__ import annotations

import json
import sys
from typing import Any

from oaep.builder import start
from oaep.keys import AgentKey

# Public demo seed. Not a secret. Do not use in production.
DEMO_SEED = bytes.fromhex("0a" * 32)
DEMO_CLOCK_START = 1_789_131_241


class _StepClock:
    def __init__(self, start: int) -> None:
        self._now = start

    def __call__(self) -> int:
        now = self._now
        self._now += 1
        return now


def demo_key() -> AgentKey:
    return AgentKey.from_private_bytes(DEMO_SEED)


class _SeqNonce:
    def __init__(self, start: int = 3) -> None:
        self._n = start

    def __call__(self) -> bytes:
        n = self._n
        self._n += 1
        return n.to_bytes(32, "big")


def build_research_receipt() -> dict[str, Any]:
    """User asked for a summary from three approved sources (PRD §23 shape)."""
    clock = _StepClock(DEMO_CLOCK_START)
    execution = start(
        agent=demo_key(),
        task="Research topic X using three approved sources and produce a summary.",
        agent_version="1.4.2",
        environment="local-dev",
        clock=clock,
        nonce=_SeqNonce(),
        task_nonce=bytes.fromhex("11" * 32),
        start_nonce=bytes.fromhex("22" * 32),
    )
    execution.model_inference(
        identity="sentient-research-8b-q4",
        input_data="plan the research workflow",
        output="search three sources then synthesize",
        version="sentient-research-8b-q4",
        fingerprint="sentient-fp-example",
    )
    for name in ("source-a", "source-b", "source-c"):
        execution.tool_call(
            identity=f"approved:{name}",
            input_data=f"query {name}",
            output=f"excerpt from {name}",
        )
    return execution.complete("Summary of topic X from three approved sources.")


def main() -> None:
    json.dump(build_research_receipt(), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
