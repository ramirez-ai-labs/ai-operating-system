"""
Tests for Sprint 5 — ChromaDB semantic retrieval backend.

All tests run without a live Ollama instance or a pre-built ChromaDB
index. Ollama and ChromaDB interactions are mocked so the suite stays
fast and CI-safe.

Test strategy:
  - backend.py routing: confirm the dispatcher respects RETRIEVAL_BACKEND
    and falls back gracefully on unknown values
  - chroma.py fallback: confirm the public retrieve_relevant_documents
    falls back to keyword retrieval when the index is missing, chromadb
    is unavailable, or Ollama is unreachable
  - chroma.py result parsing: confirm _parse_results maps ChromaDB output
    to EvidenceItem correctly
  - ingest helpers: confirm _extract_documents handles skip logic and
    normalises metadata consistently
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from packages.shared.schemas.director_os import EvidenceItem

# ---------------------------------------------------------------------------
# backend.py — dispatcher routing
# ---------------------------------------------------------------------------


def test_backend_defaults_to_local_files(monkeypatch) -> None:
    """RETRIEVAL_BACKEND unset → keyword retrieval, not ChromaDB."""
    monkeypatch.delenv("RETRIEVAL_BACKEND", raising=False)

    called_with: list[str] = []

    def fake_local(base_path, query, limit):
        called_with.append("local_files")
        return []

    with patch("packages.shared.retrieval.local_files.retrieve_relevant_documents", fake_local):
        from packages.shared.retrieval import backend
        backend.retrieve_relevant_documents(
            base_path="data/local_only/projects", query="test", limit=3
        )

    assert called_with == ["local_files"]


def test_backend_routes_to_chroma_when_env_set(monkeypatch) -> None:
    """RETRIEVAL_BACKEND=chroma → ChromaDB retrieval is called."""
    monkeypatch.setenv("RETRIEVAL_BACKEND", "chroma")

    called_with: list[str] = []

    def fake_chroma(base_path, query, limit):
        called_with.append("chroma")
        return []

    with patch("packages.shared.retrieval.chroma.retrieve_relevant_documents", fake_chroma):
        import importlib

        from packages.shared.retrieval import backend
        importlib.reload(backend)  # reload to pick up the new env var
        backend.retrieve_relevant_documents(
            base_path="data/local_only/projects", query="test", limit=3
        )

    assert "chroma" in called_with


def test_backend_unknown_value_falls_back_to_local(monkeypatch, caplog) -> None:
    """An unrecognised RETRIEVAL_BACKEND value warns and falls back to local_files."""
    monkeypatch.setenv("RETRIEVAL_BACKEND", "elasticsearch")

    results: list = []

    def fake_local(base_path, query, limit):
        results.append("local_files")
        return []

    with patch("packages.shared.retrieval.local_files.retrieve_relevant_documents", fake_local):
        import importlib
        import logging

        from packages.shared.retrieval import backend
        importlib.reload(backend)

        with caplog.at_level(logging.WARNING):
            backend.retrieve_relevant_documents(
                base_path="data/local_only/projects", query="test", limit=3
            )

    assert "local_files" in results
    assert any("elasticsearch" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# chroma.py — fallback behaviour
# ---------------------------------------------------------------------------


def test_chroma_falls_back_when_index_missing(monkeypatch, tmp_path) -> None:
    """
    When the ChromaDB index directory does not exist, chroma.py should
    log a warning and delegate to keyword retrieval — not raise.
    """
    # Point the module at a non-existent path
    monkeypatch.setattr(
        "packages.shared.retrieval.chroma.CHROMA_DB_PATH",
        str(tmp_path / "does_not_exist"),
    )

    from packages.shared.retrieval.chroma import retrieve_relevant_documents

    # Should not raise — must produce results via keyword fallback
    results = retrieve_relevant_documents(
        base_path="data/local_only/projects",
        query="leadership update",
        limit=3,
    )

    assert isinstance(results, list)
    # keyword fallback against real sample data should return at least one item
    assert len(results) >= 1


def test_chroma_falls_back_when_chromadb_not_importable(monkeypatch) -> None:
    """
    When chromadb is not installed, the public function should fall back
    to keyword retrieval rather than propagating an ImportError.
    """
    import builtins
    real_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "chromadb":
            raise ImportError("chromadb not installed (simulated)")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=blocked_import):
        import importlib

        from packages.shared.retrieval import chroma
        importlib.reload(chroma)

        results = chroma.retrieve_relevant_documents(
            base_path="data/local_only/projects",
            query="leadership",
            limit=3,
        )

    assert isinstance(results, list)


def test_chroma_falls_back_when_ollama_unreachable(monkeypatch, tmp_path) -> None:
    """
    When Ollama is offline, _embed raises URLError. The public function
    should catch this and fall back to keyword retrieval.
    """
    import urllib.error

    # Create the chroma path so the "missing index" check passes
    fake_chroma_path = tmp_path / "chroma"
    fake_chroma_path.mkdir()
    monkeypatch.setattr(
        "packages.shared.retrieval.chroma.CHROMA_DB_PATH",
        str(fake_chroma_path),
    )

    def fail_embed(text, model, url):
        raise urllib.error.URLError("Connection refused (simulated Ollama offline)")

    monkeypatch.setattr("packages.shared.retrieval.chroma._embed", fail_embed)

    # Also mock chromadb so the import check passes
    mock_chroma = MagicMock()
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_collection.count.return_value = 5
    mock_client.get_collection.return_value = mock_collection
    mock_chroma.PersistentClient.return_value = mock_client

    with patch.dict("sys.modules", {"chromadb": mock_chroma}):
        import importlib

        from packages.shared.retrieval import chroma
        importlib.reload(chroma)

        results = chroma.retrieve_relevant_documents(
            base_path="data/local_only/projects",
            query="leadership",
            limit=3,
        )

    assert isinstance(results, list)


def test_chroma_falls_back_when_path_not_ingested(monkeypatch, tmp_path, caplog) -> None:
    """
    When the collection has docs globally but none for the requested data_root,
    the public function should warn and fall back to keyword retrieval rather
    than returning empty results silently.
    """
    import logging

    fake_chroma_path = tmp_path / "chroma"
    fake_chroma_path.mkdir()
    monkeypatch.setattr(
        "packages.shared.retrieval.chroma.CHROMA_DB_PATH", str(fake_chroma_path)
    )

    def fake_embed(text, model, url):
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr("packages.shared.retrieval.chroma._embed", fake_embed)

    mock_chroma = MagicMock()
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_collection.count.return_value = 10  # global collection has docs
    mock_collection.get.return_value = {"ids": []}  # none for this data root
    mock_client.get_collection.return_value = mock_collection
    mock_chroma.PersistentClient.return_value = mock_client

    with patch.dict("sys.modules", {"chromadb": mock_chroma}):
        import importlib

        from packages.shared.retrieval import chroma
        importlib.reload(chroma)

        with caplog.at_level(logging.WARNING):
            results = chroma.retrieve_relevant_documents(
                base_path="data/local_only/brand",
                query="local-first ai",
                limit=3,
            )

    assert isinstance(results, list)
    warning_text = " ".join(r.message for r in caplog.records).lower()
    assert "not ingested" in warning_text or "no documents" in warning_text


# ---------------------------------------------------------------------------
# chroma.py — result parsing
# ---------------------------------------------------------------------------


def test_parse_results_maps_to_evidence_items() -> None:
    """_parse_results should convert ChromaDB output to EvidenceItem objects."""
    from packages.shared.retrieval.chroma import _parse_results

    fake_results = {
        "documents": [["Win: shipped the dashboard refresh.", "Risk: vendor delay pending."]],
        "metadatas": [
            [
                {
                    "relative_path": "director_week_14.md",
                    "line_number": 3,
                    "title": "Director Week 14",
                    "file_name": "director_week_14.md",
                },
                {
                    "relative_path": "director_week_14.md",
                    "line_number": 5,
                    "title": "Director Week 14",
                    "file_name": "director_week_14.md",
                },
            ]
        ],
    }

    items = _parse_results(fake_results)

    assert len(items) == 2
    assert all(isinstance(item, EvidenceItem) for item in items)
    assert items[0].source == "director_week_14.md"
    assert items[0].line_number == 3
    assert items[0].excerpt == "Win: shipped the dashboard refresh."
    assert items[1].line_number == 5


def test_parse_results_skips_empty_documents() -> None:
    """Empty document strings should be filtered out silently."""
    from packages.shared.retrieval.chroma import _parse_results

    fake_results = {
        "documents": [["Valid line.", "", "Another valid line."]],
        "metadatas": [
            [
                {"relative_path": "a.md", "line_number": 1, "title": "A"},
                {"relative_path": "a.md", "line_number": 2, "title": "A"},
                {"relative_path": "a.md", "line_number": 3, "title": "A"},
            ]
        ],
    }

    items = _parse_results(fake_results)

    assert len(items) == 2
    assert items[0].excerpt == "Valid line."
    assert items[1].excerpt == "Another valid line."


# ---------------------------------------------------------------------------
# ingest helpers
# ---------------------------------------------------------------------------


def test_extract_documents_skips_headings(tmp_path) -> None:
    """Markdown headings should not become ChromaDB documents."""
    md_file = tmp_path / "week.md"
    md_file.write_text(
        "# Director Week 14\n"
        "Win: shipped the dashboard refresh.\n"
        "Risk: vendor delay pending.\n"
        "\n"
        "Next: sync with platform lead.\n",
        encoding="utf-8",
    )

    from packages.shared.retrieval.ingest import extract_documents

    docs, metadatas, ids = extract_documents([md_file], tmp_path)

    texts = [d for d in docs]
    assert not any(t.startswith("#") for t in texts), "Headings must be excluded"
    assert any("Win:" in t for t in texts)
    assert any("Risk:" in t for t in texts)
    assert any("Next:" in t for t in texts)


def test_extract_documents_normalises_metadata(tmp_path) -> None:
    """
    data_root in metadata must be the resolved absolute path so it
    matches the filter used in chroma._chroma_retrieve.
    """
    md_file = tmp_path / "week.md"
    md_file.write_text("Win: test line.\n", encoding="utf-8")

    from packages.shared.retrieval.ingest import extract_documents

    _, metadatas, _ = extract_documents([md_file], tmp_path)

    assert len(metadatas) == 1
    assert metadatas[0]["data_root"] == str(tmp_path.resolve())
    assert metadatas[0]["relative_path"] == "week.md"
    assert metadatas[0]["line_number"] == 1


def test_extract_documents_empty_file_produces_no_chunks(tmp_path) -> None:
    """Empty files should be silently skipped — no empty documents in the index."""
    empty_file = tmp_path / "empty.md"
    empty_file.write_text("", encoding="utf-8")

    from packages.shared.retrieval.ingest import extract_documents

    docs, _, _ = extract_documents([empty_file], tmp_path)

    assert docs == []
