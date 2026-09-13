"""Open Agent Execution Protocol — Level-0 signed receipts."""

from __future__ import annotations

__version__ = "0.1.0"

from oaep.builder import Execution, start
from oaep.canonical import canonical_dumps, commit, generate_nonce, receipt_signing_payload
from oaep.keys import AgentKey
from oaep.merkle import ProofStep, inclusion_proof, merkle_root_hex, verify_inclusion
from oaep.verify import Report, verify_path, verify_receipt

__all__ = [
    "AgentKey",
    "Execution",
    "ProofStep",
    "Report",
    "__version__",
    "canonical_dumps",
    "commit",
    "generate_nonce",
    "inclusion_proof",
    "merkle_root_hex",
    "receipt_signing_payload",
    "start",
    "verify_inclusion",
    "verify_path",
    "verify_receipt",
]
