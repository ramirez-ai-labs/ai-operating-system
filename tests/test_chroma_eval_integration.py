"""
Sprint 16 — ChromaDB eval integration tests.

Closes the gap between unit-level chroma tests (test_chroma_retrieval.py)
and the eval pipeline. These tests prove that:

  1. The Director OS and Brand OS graphs correctly route retrieval through
     the chroma backend when RETRIEVAL_BACKEND=chroma is set — without
     reloading modules or patching at the graph level.
  2. All eval cases pass when chroma provides the same evidence as the
     keyword baseline (chroma mock backed by local_files).
  3. The is_index_ready() helper correctly reflects index presence.
  4. The chroma eval runners skip gracefully in CI when the index is absent.

Ollama and ChromaDB are mocked in every test — the suite is CI-safe.
"""
from __future__ import annotations

from packages.shared.schemas.director_os import EvidenceItem, WeeklyUpdateRequest

# ---------------------------------------------------------------------------
# Group 1: End-to-end graph routing through the chroma backend
# ---------------------------------------------------------------------------


def test_director_os_graph_routes_through_chroma_when_backend_set(monkeypatch) -> None:
    """When RETRIEVAL_BACKEND=chroma, the Director OS graph invokes chroma retrieval."""
    monkeypatch.setenv("RETRIEVAL_BACKEND", "chroma")

    chroma_invoked: list[bool] = []

    def fake_chroma_retrieve(base_path: str, query: str, limit: int) -> list[EvidenceItem]:
        chroma_invoked.append(True)
        return [
            EvidenceItem(
                source="projects/director_week_14.md",
                line_number=3,
                title="Director Week 14",
                excerpt="Win: shipped the dashboard refresh ahead of schedule.",
            )
        ]

    monkeypatch.setattr(
        "packages.shared.retrieval.chroma._chroma_retrieve", fake_chroma_retrieve
    )

    from director_os.workflows.weekly_update import build_weekly_update

    result = build_weekly_update(
        WeeklyUpdateRequest(
            data_path="data/local_only/projects",
            focus="wins",
            max_documents=3,
        )
    )

    assert chroma_invoked, "chroma._chroma_retrieve was not called — backend routing failed"
    assert result.evidence
    assert result.summary


def test_brand_os_graph_routes_through_chroma_when_backend_set(monkeypatch) -> None:
    """When RETRIEVAL_BACKEND=chroma, the Brand OS graph invokes chroma retrieval."""
    monkeypatch.setenv("RETRIEVAL_BACKEND", "chroma")

    chroma_invoked: list[bool] = []

    def fake_chroma_retrieve(base_path: str, query: str, limit: int) -> list[EvidenceItem]:
        chroma_invoked.append(True)
        return [
            EvidenceItem(
                source="brand/brand_week_15.md",
                line_number=4,
                title="Brand Week 15",
                excerpt="Insight: local-first AI workflows reduce data egress risk.",
            )
        ]

    monkeypatch.setattr(
        "packages.shared.retrieval.chroma._chroma_retrieve", fake_chroma_retrieve
    )

    from brand_os.workflows.content_draft import build_content_draft
    from packages.shared.schemas.brand_os import BrandContentDraftRequest

    result = build_content_draft(
        BrandContentDraftRequest(
            data_path="data/local_only/brand",
            focus="local-first ai",
            max_documents=3,
        )
    )

    assert chroma_invoked, "chroma._chroma_retrieve was not called — backend routing failed"
    assert result.evidence
    assert result.insight_summary


# ---------------------------------------------------------------------------
# Group 2: Full eval pipeline with mocked chroma (all cases must pass)
# ---------------------------------------------------------------------------


def _make_chroma_backed_by_local_files():
    """Return a _chroma_retrieve replacement that delegates to keyword retrieval."""
    from packages.shared.retrieval.local_files import (
        retrieve_relevant_documents as _keyword,
    )

    def _local_files_via_chroma(base_path: str, query: str, limit: int) -> list[EvidenceItem]:
        return _keyword(base_path, query, limit)

    return _local_files_via_chroma


def test_director_os_eval_cases_all_pass_with_chroma_evidence(monkeypatch) -> None:
    """
    All Director OS eval cases should pass when chroma provides keyword-equivalent
    evidence — proving the eval pipeline is chroma-compatible end-to-end.
    """
    monkeypatch.setenv("RETRIEVAL_BACKEND", "chroma")
    monkeypatch.setattr(
        "packages.shared.retrieval.chroma._chroma_retrieve",
        _make_chroma_backed_by_local_files(),
    )

    from packages.shared.evaluations.director_os import (
        load_director_os_eval_cases,
        run_local_director_os_evaluations,
    )

    cases = load_director_os_eval_cases()
    results = run_local_director_os_evaluations(cases)

    failed = [r["case_id"] for r in results if not r["passed"]]
    assert not failed, f"Director OS chroma eval cases failed: {failed}"


def test_brand_os_eval_cases_all_pass_with_chroma_evidence(monkeypatch) -> None:
    """
    All Brand OS eval cases should pass when chroma provides keyword-equivalent
    evidence — proving the eval pipeline is chroma-compatible for Brand OS.
    """
    monkeypatch.setenv("RETRIEVAL_BACKEND", "chroma")
    monkeypatch.setattr(
        "packages.shared.retrieval.chroma._chroma_retrieve",
        _make_chroma_backed_by_local_files(),
    )

    from packages.shared.evaluations.brand_os import (
        load_brand_os_eval_cases,
        run_local_brand_os_evaluations,
    )

    cases = load_brand_os_eval_cases()
    results = run_local_brand_os_evaluations(cases)

    failed = [r["case_id"] for r in results if not r["passed"]]
    assert not failed, f"Brand OS chroma eval cases failed: {failed}"


# ---------------------------------------------------------------------------
# Group 3: is_index_ready() helper
# ---------------------------------------------------------------------------


def test_is_index_ready_returns_false_when_path_absent(monkeypatch, tmp_path) -> None:
    """is_index_ready() should return False when the ChromaDB directory does not exist."""
    monkeypatch.setattr(
        "packages.shared.retrieval.chroma.CHROMA_DB_PATH",
        str(tmp_path / "nonexistent"),
    )

    from packages.shared.retrieval.chroma import is_index_ready

    assert not is_index_ready()


def test_is_index_ready_returns_true_when_index_present(monkeypatch, tmp_path) -> None:
    """is_index_ready() should return True when the ChromaDB directory exists and is non-empty."""
    index_dir = tmp_path / "chroma"
    index_dir.mkdir()
    (index_dir / "chroma.sqlite3").write_bytes(b"fake")

    monkeypatch.setattr(
        "packages.shared.retrieval.chroma.CHROMA_DB_PATH",
        str(index_dir),
    )

    from packages.shared.retrieval.chroma import is_index_ready

    assert is_index_ready()


# ---------------------------------------------------------------------------
# Group 4: Runner skip logic (ci_mode=True when index is absent)
# ---------------------------------------------------------------------------


def test_director_os_chroma_runner_skips_in_ci_when_index_absent(monkeypatch) -> None:
    """Director OS chroma runner returns 0 in CI mode when the index is not built."""
    monkeypatch.setattr(
        "packages.shared.retrieval.chroma.is_index_ready",
        lambda: False,
    )

    import importlib

    runner = importlib.import_module("scripts.run_director_os_evals_chroma")
    importlib.reload(runner)

    exit_code = runner.run_evals(ci_mode=True)
    assert exit_code == 0


def test_brand_os_chroma_runner_skips_in_ci_when_index_absent(monkeypatch) -> None:
    """Brand OS chroma runner returns 0 in CI mode when the index is not built."""
    monkeypatch.setattr(
        "packages.shared.retrieval.chroma.is_index_ready",
        lambda: False,
    )

    import importlib

    runner = importlib.import_module("scripts.run_brand_os_evals_chroma")
    importlib.reload(runner)

    exit_code = runner.run_evals(ci_mode=True)
    assert exit_code == 0
