"""
Retrieval backend selector for AI-OS.

This is the single import point for all callers (Director OS graph,
Brand OS graph, etc.). It reads the RETRIEVAL_BACKEND environment
variable and dispatches to the appropriate implementation.

Supported backends:
    local_files  — keyword scorer (default; no external deps, safe for CI)
    chroma       — ChromaDB semantic search (requires: Ollama running +
                   nomic-embed-text pulled + ingest run completed)

Switching backends is a single .env change. No graph logic is affected.
"""
from __future__ import annotations

import logging
import os

from packages.shared.schemas.director_os import EvidenceItem

logger = logging.getLogger(__name__)

_BACKEND_LOCAL = "local_files"
_BACKEND_CHROMA = "chroma"
_VALID_BACKENDS = {_BACKEND_LOCAL, _BACKEND_CHROMA}


def retrieve_relevant_documents(
    base_path: str,
    query: str | None,
    limit: int,
) -> list[EvidenceItem]:
    """
    Route a retrieval request to the configured backend.

    Director OS and Brand OS graphs call this instead of importing
    local_files directly so that backend selection stays out of workflow
    logic and is entirely a deployment-time concern.
    """
    backend = os.getenv("RETRIEVAL_BACKEND", _BACKEND_LOCAL).strip().lower()

    if backend not in _VALID_BACKENDS:
        # Misconfigured env var should not silently break retrieval.
        # Warn and fall through to the safe default rather than raise.
        logger.warning(
            "Unknown RETRIEVAL_BACKEND='%s'. Valid options: %s. "
            "Falling back to local_files.",
            backend,
            ", ".join(sorted(_VALID_BACKENDS)),
        )
        backend = _BACKEND_LOCAL

    if backend == _BACKEND_CHROMA:
        from packages.shared.retrieval.chroma import (
            retrieve_relevant_documents as _chroma,
        )
        logger.debug("Retrieval backend: chroma (semantic)")
        return _chroma(base_path, query, limit)

    from packages.shared.retrieval.local_files import (
        retrieve_relevant_documents as _local,
    )
    logger.debug("Retrieval backend: local_files (keyword)")
    return _local(base_path, query, limit)
