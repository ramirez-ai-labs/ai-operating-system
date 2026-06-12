#!/usr/bin/env python3
"""
CLI entry point for indexing local project data into ChromaDB.

All ingest logic lives in packages/shared/retrieval/ingest.py so it
can be imported and tested directly. This script handles argument
parsing, .env loading, and delegates to ingest.run().

Usage:
    python scripts/ingest_local_data.py
    python scripts/ingest_local_data.py --data-root data/local_only
    python scripts/ingest_local_data.py --ollama-url http://10.0.0.1:11434
    python scripts/ingest_local_data.py --ollama-model nomic-embed-text

Prerequisites:
    pip install chromadb
    ollama pull nomic-embed-text
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

# Load .env so the script honours OLLAMA_URL without a shell export.
# setdefault means existing shell exports always take precedence, and this
# block runs only when the script is executed — not when ingest.py is imported.
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from packages.shared.retrieval.ingest import run  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Index local markdown files into ChromaDB for semantic retrieval."
    )
    parser.add_argument(
        "--data-root",
        default=os.getenv("DATA_ROOT", "data/local_only"),
        help="Directory to index (default: data/local_only)",
    )
    parser.add_argument(
        "--ollama-url",
        default=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
        help="Ollama base URL (default: http://127.0.0.1:11434)",
    )
    parser.add_argument(
        "--ollama-model",
        default=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        help="Embedding model name (default: nomic-embed-text)",
    )
    args = parser.parse_args()
    sys.exit(run(
        data_root=args.data_root,
        ollama_url=args.ollama_url,
        ollama_model=args.ollama_model,
    ))


if __name__ == "__main__":
    main()
