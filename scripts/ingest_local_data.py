#!/usr/bin/env python3
"""
Index local project data into ChromaDB for semantic retrieval.

Scans all markdown files under the configured data root, generates
dense embeddings via Ollama nomic-embed-text, and stores them in a
persistent ChromaDB collection at data/chroma/.

The collection is rebuilt from scratch on every run. This is
intentionally simple: data/local_only/ is small, ingest takes seconds,
and idempotent rebuilds avoid stale-document edge cases.

Usage:
    # Default: index data/local_only/, Ollama at localhost
    python scripts/ingest_local_data.py

    # Custom data root or Ollama location
    python scripts/ingest_local_data.py --data-root data/local_only
    python scripts/ingest_local_data.py --ollama-url http://10.0.0.1:11434
    python scripts/ingest_local_data.py --ollama-model nomic-embed-text

Prerequisites:
    pip install chromadb
    ollama pull nomic-embed-text
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# Must match the constants in chroma.py so the ingest and retrieval paths
# agree on where the index lives and what the collection is called.
CHROMA_DB_PATH = str((Path("data") / "chroma").resolve())
COLLECTION_NAME = "ai-os-docs"

# Lines starting with these patterns are heading or list-structure noise.
# Skipping them improves embedding quality — the model should see content,
# not markdown scaffolding.
_SKIP_PREFIXES = ("#",)


def _load_dotenv() -> None:
    """
    Load .env into os.environ using setdefault so existing shell exports
    always take precedence. Called only from main() and __main__ so that
    importing this module in tests never mutates the process environment.
    """
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main(
    data_root: str = "data/local_only",
    ollama_url: str = "http://127.0.0.1:11434",
    ollama_model: str = "nomic-embed-text",
) -> int:
    """Run ingestion. Returns exit code (0 = success, 1 = failure)."""
    _load_dotenv()
    try:
        import chromadb  # noqa: PLC0415
    except ImportError:
        logger.error(
            "chromadb is not installed. Run: pip install 'chromadb>=0.5.0,<1.0.0'"
        )
        return 1

    root = Path(data_root).resolve()
    if not root.exists():
        logger.error("Data root does not exist: %s", root)
        return 1

    # Verify Ollama is reachable before doing any file work.
    if not _check_ollama(ollama_url, ollama_model):
        logger.error(
            "Cannot reach Ollama at %s with model '%s'. "
            "Start Ollama and run: ollama pull %s",
            ollama_url,
            ollama_model,
            ollama_model,
        )
        return 1

    md_files = sorted(root.rglob("*.md"))
    if not md_files:
        logger.error("No markdown files found under %s", root)
        return 1

    logger.info("Found %d markdown file(s) under %s", len(md_files), root)

    # Build documents and metadata from each file's content lines.
    documents, metadatas, ids = _extract_documents(md_files, root)

    if not documents:
        logger.error("No indexable lines found. Check that markdown files have content.")
        return 1

    logger.info(
        "Extracted %d indexable lines from %d file(s)", len(documents), len(md_files)
    )

    # Generate embeddings in batches to avoid overwhelming Ollama on large
    # datasets. Batch size of 32 balances throughput against memory pressure.
    logger.info("Generating embeddings via %s/%s...", ollama_url, ollama_model)
    embeddings = _embed_batch(documents, ollama_model, ollama_url, batch_size=32)

    if len(embeddings) != len(documents):
        logger.error(
            "Embedding count mismatch: expected %d, got %d",
            len(documents),
            len(embeddings),
        )
        return 1

    # Persist the index. Delete and recreate the collection each run so
    # there are no stale documents after source files change.
    chroma_path = Path(CHROMA_DB_PATH)
    chroma_path.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(chroma_path))
    try:
        client.delete_collection(COLLECTION_NAME)
        logger.info("Cleared existing collection '%s'", COLLECTION_NAME)
    except Exception:
        # Collection does not exist yet on the first run — that is fine.
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        # cosine distance is better than the default l2 for text embeddings
        # because it is invariant to document length differences.
        metadata={"hnsw:space": "cosine"},
    )

    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )

    logger.info(
        "Indexed %d document chunks into ChromaDB at %s", len(documents), chroma_path
    )
    logger.info(
        "Set RETRIEVAL_BACKEND=chroma in .env to activate semantic retrieval."
    )
    return 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_documents(
    md_files: list[Path],
    root: Path,
) -> tuple[list[str], list[dict], list[str]]:
    """
    Convert markdown files into indexable line-level chunks.

    Each content line becomes one ChromaDB document. Line-level chunking
    preserves the grounding story: every EvidenceItem returned during
    retrieval maps back to one specific line in one specific file.
    """
    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    for file_path in md_files:
        text = file_path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        title = file_path.stem.replace("_", " ").replace("-", " ").title()
        # Resolve and stringify consistently with chroma.py so metadata
        # filters match at query time.
        data_root_key = str(file_path.parent.resolve())
        relative_path = str(file_path.relative_to(root))

        for line_number, raw_line in enumerate(text.splitlines(), start=1):
            cleaned = raw_line.strip("- ").strip()
            if not cleaned:
                continue
            if cleaned.startswith(_SKIP_PREFIXES):
                continue

            doc_id = f"{relative_path}::{line_number}"
            documents.append(cleaned[:500])
            metadatas.append(
                {
                    "data_root": data_root_key,
                    "relative_path": relative_path,
                    "line_number": line_number,
                    "title": title,
                    "file_name": file_path.name,
                }
            )
            ids.append(doc_id)

    return documents, metadatas, ids


def _embed_batch(
    texts: list[str],
    model: str,
    ollama_url: str,
    batch_size: int = 32,
) -> list[list[float]]:
    """
    Generate embeddings for a list of texts, processing in batches.

    Ollama processes embeddings one at a time (no native batch endpoint),
    so we loop and log progress every batch_size items.
    """
    embeddings: list[list[float]] = []
    total = len(texts)

    for i, text in enumerate(texts):
        embedding = _embed(text, model, ollama_url)
        embeddings.append(embedding)
        if (i + 1) % batch_size == 0 or (i + 1) == total:
            logger.info("  Embedded %d / %d lines", i + 1, total)

    return embeddings


def _embed(text: str, model: str, ollama_url: str) -> list[float]:
    """Call Ollama /api/embeddings and return the embedding vector."""
    payload = json.dumps({"model": model, "prompt": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{ollama_url}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["embedding"]


def _check_ollama(ollama_url: str, model: str) -> bool:
    """
    Verify Ollama is reachable and the embedding model is available.

    A fast check: send a short probe embedding and confirm we get a
    non-empty vector back. This surfaces missing models early rather
    than partway through a long ingest run.
    """
    try:
        vector = _embed("ping", model, ollama_url)
        return len(vector) > 0
    except (urllib.error.URLError, KeyError, json.JSONDecodeError):
        return False


if __name__ == "__main__":
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

    sys.exit(
        main(
            data_root=args.data_root,
            ollama_url=args.ollama_url,
            ollama_model=args.ollama_model,
        )
    )
