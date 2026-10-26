"""Semantic (Chroma) retrieval returns lines the calling domain can use.

Two defects made the Chroma path unusable for evals on a real index:

- Citations were relative to the ingest root (`projects/week.md`), not to the
  queried data path (`week.md`) as keyword retrieval cites them.
- `section_labels` only reached the keyword fallback. Semantic ranking alone
  could fill a domain's evidence with lines none of its sections extract.

No live Ollama or ChromaDB index is needed: the collection is faked.
"""

from __future__ import annotations

from pathlib import Path

from packages.shared.retrieval import chroma, local_files
from packages.shared.retrieval.ingest import extract_documents
from packages.shared.schemas.director_os import EvidenceItem

PROJECTS = "data/local_only/projects"


def _evidence(excerpt: str, line_number: int = 1) -> EvidenceItem:
    return EvidenceItem(source="a.md", line_number=line_number, title="A", excerpt=excerpt)


def test_chroma_citations_match_keyword_citations_for_nested_folders(
    tmp_path, monkeypatch
) -> None:
    # Ingest indexes the whole local data root; domains query a subfolder.
    monkeypatch.setattr(local_files, "ALLOWED_LOCAL_DATA_ROOT", tmp_path.resolve())
    projects = tmp_path / "projects"
    projects.mkdir()
    (projects / "week.md").write_text("Win: shipped the dashboard.\n", encoding="utf-8")
    documents, metadatas, _ = extract_documents(sorted(tmp_path.rglob("*.md")), tmp_path)

    semantic = chroma._parse_results(
        {"documents": [documents], "metadatas": [metadatas]}, projects.resolve()
    )
    keyword = local_files.retrieve_relevant_documents(str(projects), None, limit=5)

    assert [(e.source, e.line_number) for e in semantic] == [
        (e.source, e.line_number) for e in keyword
    ]
    assert semantic[0].source == "week.md"


def test_section_lines_come_first_and_keep_semantic_order() -> None:
    ranked = [
        _evidence("Date: 2026-10-01", 1),
        _evidence("Action: send the RFC", 2),
        _evidence("Intro text", 3),
        _evidence("action: book the review", 4),
    ]

    preferred = chroma._prefer_section_lines(ranked, ("Action:",))

    assert [e.line_number for e in preferred] == [2, 4, 1, 3]


class _FakeCollection:
    def __init__(self, rows: list[tuple[str, int]]) -> None:
        self.rows = rows
        self.n_results: int | None = None

    def count(self) -> int:
        return 100

    def get(self, **_: object) -> dict:
        return {"ids": ["x"]}

    def query(self, n_results: int, **_: object) -> dict:
        self.n_results = n_results
        root = str(Path(PROJECTS).resolve())
        rows = self.rows[:n_results]
        return {
            "documents": [[text for text, _ in rows]],
            "metadatas": [
                [
                    {"data_root": root, "file_name": "week.md", "line_number": n, "title": "W"}
                    for _, n in rows
                ]
            ],
        }


def _fake_index(monkeypatch, tmp_path, rows: list[tuple[str, int]]) -> _FakeCollection:
    collection = _FakeCollection(rows)
    client = type("Client", (), {"get_collection": lambda self, name: collection})()
    monkeypatch.setattr(chroma, "CHROMA_DB_PATH", str(tmp_path))
    monkeypatch.setattr(chroma, "_embed", lambda text, model, url: [0.1])
    monkeypatch.setattr(chroma, "_get_chroma_client", lambda: client)
    return collection


# In semantic order: the domain's only usable line ranks third.
_ROWS = [("Date: 2026-10-01", 1), ("Owner: platform team", 2), ("Action: send the RFC", 3)]


def test_chroma_considers_more_candidates_and_prefers_section_lines(
    tmp_path, monkeypatch
) -> None:
    collection = _fake_index(monkeypatch, tmp_path, _ROWS)

    evidence = chroma._chroma_retrieve(PROJECTS, "rfc", 2, ("Action:",))

    assert collection.n_results == 2 * chroma._LABEL_CANDIDATE_FACTOR
    assert [e.excerpt for e in evidence] == ["Action: send the RFC", "Date: 2026-10-01"]


def test_chroma_without_labels_keeps_semantic_ranking(tmp_path, monkeypatch) -> None:
    collection = _fake_index(monkeypatch, tmp_path, _ROWS)

    evidence = chroma._chroma_retrieve(PROJECTS, "rfc", 2)

    assert collection.n_results == 2
    assert [e.line_number for e in evidence] == [1, 2]


def test_public_retrieve_passes_section_labels_to_chroma(monkeypatch) -> None:
    calls: list[tuple] = []

    def fake(base_path, query, limit, section_labels=None):
        calls.append((base_path, query, limit, section_labels))
        return []

    monkeypatch.setattr(chroma, "_chroma_retrieve", fake)

    chroma.retrieve_relevant_documents(PROJECTS, "rfc", 4, ("Action:",))

    assert calls == [(PROJECTS, "rfc", 4, ("Action:",))]
