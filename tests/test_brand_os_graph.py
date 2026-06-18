from packages.shared.graphs.brand_os import run_content_draft_graph
from packages.shared.schemas.brand_os import BrandContentDraftRequest, BrandContentDraftResponse
from packages.shared.schemas.director_os import EvidenceItem, GroundedItem


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


def test_brand_os_graph_uses_model_when_requested(monkeypatch) -> None:
    """When use_model=True, the graph should call the provider and return its response."""
    from packages.shared.graphs import brand_os as graph_module

    fake_evidence = [
        EvidenceItem(
            source="brand_week_x.md",
            line_number=3,
            title="Brand Week X",
            excerpt="Insight: local-first AI makes grounded content drafts tractable.",
        )
    ]

    def fake_retrieve_relevant_documents(*, base_path, query, limit):
        return fake_evidence

    fake_response = BrandContentDraftResponse(
        insight_summary="Claude-synthesized brand insight about local-first workflows.",
        post_outline=[
            GroundedItem(
                text="Insight: local-first AI makes grounded content drafts tractable.",
                source="brand_week_x.md",
                line_number=3,
            )
        ],
        podcast_angles=[],
        repo_improvements=[],
        evidence=fake_evidence,
    )

    class FakeProvider:
        def generate_brand_content_draft(self, focus, evidence):
            return fake_response

        def get_last_usage(self):
            return {"input_tokens": 100, "output_tokens": 50}

    monkeypatch.setattr(
        graph_module, "retrieve_relevant_documents", fake_retrieve_relevant_documents
    )
    monkeypatch.setattr(graph_module, "_build_provider", lambda request: FakeProvider())

    result = run_content_draft_graph(
        BrandContentDraftRequest(
            data_path="data/local_only/brand",
            focus="local-first ai",
            max_documents=5,
            use_model=True,
        )
    )

    assert result.insight_summary == "Claude-synthesized brand insight about local-first workflows."
    assert len(result.post_outline) == 1


def test_brand_os_graph_falls_back_to_deterministic_on_model_error(monkeypatch) -> None:
    """When the model raises ValueError and fallback_to_deterministic=True, the graph succeeds."""
    from packages.shared.graphs import brand_os as graph_module

    def fake_retrieve_relevant_documents(*, base_path, query, limit):
        return [
            EvidenceItem(
                source="brand_week_x.md",
                line_number=3,
                title="Brand Week X",
                excerpt="Insight: local-first AI makes grounded content drafts tractable.",
            )
        ]

    class FailingProvider:
        def generate_brand_content_draft(self, focus, evidence):
            raise ValueError("ANTHROPIC_API_KEY is not set.")

        def get_last_usage(self):
            return {}

    monkeypatch.setattr(
        graph_module, "retrieve_relevant_documents", fake_retrieve_relevant_documents
    )
    monkeypatch.setattr(graph_module, "_build_provider", lambda request: FailingProvider())

    result = run_content_draft_graph(
        BrandContentDraftRequest(
            data_path="data/local_only/brand",
            focus="local-first ai",
            max_documents=5,
            use_model=True,
            fallback_to_deterministic=True,
        )
    )

    assert result.insight_summary
    assert result.evidence


def test_brand_os_graph_validate_response_triggers_fallback_on_empty_sections(
    monkeypatch,
) -> None:
    """validate_response must fall back to deterministic when model returns empty sections."""
    from packages.shared.graphs import brand_os as graph_module

    def fake_retrieve(*, base_path, query, limit):
        return [
            EvidenceItem(
                source="brand_week_x.md",
                line_number=3,
                title="Brand Week X",
                excerpt="Insight: local-first AI makes grounded content drafts tractable.",
            )
        ]

    class EmptySectionsProvider:
        def generate_brand_content_draft(self, focus, evidence):
            return BrandContentDraftResponse(
                insight_summary="ok",
                post_outline=[],
                podcast_angles=[],
                repo_improvements=[],
                evidence=evidence,
            )

        def get_last_usage(self):
            return {"input_tokens": 10, "output_tokens": 5}

    monkeypatch.setattr(graph_module, "retrieve_relevant_documents", fake_retrieve)
    monkeypatch.setattr(graph_module, "_build_provider", lambda req: EmptySectionsProvider())

    result = run_content_draft_graph(
        BrandContentDraftRequest(
            data_path="data/local_only/brand",
            use_model=True,
            fallback_to_deterministic=True,
        )
    )
    # Deterministic fallback must populate at least post_outline from the Insight: prefix.
    assert result.post_outline, "Expected deterministic fallback to populate post_outline"


def test_brand_os_graph_validate_response_raises_when_fallback_disabled(monkeypatch) -> None:
    """validate_response must raise when fallback is disabled and model output is invalid."""
    from packages.shared.graphs import brand_os as graph_module

    def fake_retrieve(*, base_path, query, limit):
        return [
            EvidenceItem(
                source="brand_week_x.md",
                line_number=3,
                title="Brand Week X",
                excerpt="Insight: local-first AI makes grounded content drafts tractable.",
            )
        ]

    class EmptySectionsProvider:
        def generate_brand_content_draft(self, focus, evidence):
            return BrandContentDraftResponse(
                insight_summary="ok",
                post_outline=[],
                podcast_angles=[],
                repo_improvements=[],
                evidence=evidence,
            )

        def get_last_usage(self):
            return {}

    monkeypatch.setattr(graph_module, "retrieve_relevant_documents", fake_retrieve)
    monkeypatch.setattr(graph_module, "_build_provider", lambda req: EmptySectionsProvider())

    try:
        run_content_draft_graph(
            BrandContentDraftRequest(
                data_path="data/local_only/brand",
                use_model=True,
                fallback_to_deterministic=False,
            )
        )
    except ValueError as exc:
        assert "populated section" in str(exc)
    else:
        raise AssertionError("Expected ValueError when fallback disabled and model output invalid.")


def test_brand_os_graph_raises_when_fallback_disabled_and_model_fails(monkeypatch) -> None:
    """When fallback_to_deterministic=False and the model fails, the error should propagate."""
    from packages.shared.graphs import brand_os as graph_module

    def fake_retrieve_relevant_documents(*, base_path, query, limit):
        return [
            EvidenceItem(
                source="brand_week_x.md",
                line_number=3,
                title="Brand Week X",
                excerpt="Insight: local-first AI makes grounded content drafts tractable.",
            )
        ]

    class FailingProvider:
        def generate_brand_content_draft(self, focus, evidence):
            raise ValueError("ANTHROPIC_API_KEY is not set.")

        def get_last_usage(self):
            return {}

    monkeypatch.setattr(
        graph_module, "retrieve_relevant_documents", fake_retrieve_relevant_documents
    )
    monkeypatch.setattr(graph_module, "_build_provider", lambda request: FailingProvider())

    try:
        run_content_draft_graph(
            BrandContentDraftRequest(
                data_path="data/local_only/brand",
                focus="local-first ai",
                max_documents=5,
                use_model=True,
                fallback_to_deterministic=False,
            )
        )
    except ValueError as exc:
        assert "anthropic_api_key" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError when fallback is disabled and model fails.")
