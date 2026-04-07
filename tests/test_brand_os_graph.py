from packages.shared.graphs.brand_os import run_content_draft_graph
from packages.shared.schemas.brand_os import BrandContentDraftRequest
from packages.shared.schemas.director_os import EvidenceItem


def test_brand_os_graph_runs_end_to_end() -> None:
    """The graph-backed Brand OS workflow should return the same public response shape."""
    result = run_content_draft_graph(
        BrandContentDraftRequest(
            data_path="data/local_only/brand",
            focus="local-first ai workflow",
            max_documents=5,
        )
    )
    assert result.insight_summary
    assert result.post_outline
    assert result.evidence


def test_brand_os_graph_rejects_missing_local_notes() -> None:
    """The graph should still fail clearly when the local Brand data path is missing."""
    try:
        run_content_draft_graph(
            BrandContentDraftRequest(
                data_path="data/local_only/missing-brand",
                focus="podcast",
            )
        )
    except ValueError as exc:
        assert "data path does not exist" in str(exc).lower()
    else:
        raise AssertionError("Expected Brand OS graph to reject a missing data path.")


def test_brand_os_graph_routes_prefixed_evidence_into_matching_sections(monkeypatch) -> None:
    """The graph should keep Insight, Podcast, and Improve lines in their own sections."""
    from packages.shared.graphs import brand_os as graph_module

    def fake_retrieve_relevant_documents(*, base_path, query, limit):
        return [
            EvidenceItem(
                source="brand_week_x.md",
                line_number=3,
                title="Brand Week X",
                excerpt="Insight: retrieval changes made draft quality easier to trust.",
            ),
            EvidenceItem(
                source="brand_week_x.md",
                line_number=4,
                title="Brand Week X",
                excerpt="Podcast: discuss local-first operators and grounded AI workflows.",
            ),
            EvidenceItem(
                source="brand_week_x.md",
                line_number=5,
                title="Brand Week X",
                excerpt="Improve: add a visible validation summary to the content trace.",
            ),
        ]

    monkeypatch.setattr(
        graph_module,
        "retrieve_relevant_documents",
        fake_retrieve_relevant_documents,
    )

    result = run_content_draft_graph(
        BrandContentDraftRequest(
            data_path="data/local_only/brand",
            focus="trace quality",
            max_documents=5,
        )
    )

    assert [item.text for item in result.post_outline] == [
        "Insight: retrieval changes made draft quality easier to trust."
    ]
    assert [item.text for item in result.podcast_angles] == [
        "Podcast: discuss local-first operators and grounded AI workflows."
    ]
    assert [item.text for item in result.repo_improvements] == [
        "Improve: add a visible validation summary to the content trace."
    ]
