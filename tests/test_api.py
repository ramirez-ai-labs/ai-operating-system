from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    """The API should expose a minimal health check for local smoke tests."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_director_os_weekly_update_endpoint_returns_grounded_response() -> None:
    """The Director OS endpoint should return the public weekly-update shape."""
    response = client.post(
        "/director-os/weekly-update",
        json={
            "data_path": "data/local_only/projects",
            "focus": "leadership update",
            "max_documents": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]
    assert body["wins"]
    assert body["evidence"]


def test_director_os_weekly_update_endpoint_returns_400_for_missing_data_path() -> None:
    """The Director OS endpoint should surface retrieval failures as HTTP 400 errors."""
    response = client.post(
        "/director-os/weekly-update",
        json={
            "data_path": "data/local_only/missing-projects",
            "focus": "leadership update",
            "max_documents": 5,
        },
    )

    assert response.status_code == 400
    assert "data path does not exist" in response.json()["detail"].lower()


def test_director_os_weekly_update_endpoint_returns_422_for_invalid_max_documents() -> None:
    """FastAPI should reject Director OS requests that violate schema bounds."""
    response = client.post(
        "/director-os/weekly-update",
        json={
            "data_path": "data/local_only/projects",
            "focus": "leadership update",
            "max_documents": 0,
        },
    )

    assert response.status_code == 422
    assert "max_documents" in str(response.json()["detail"]).lower()


def test_director_os_weekly_update_endpoint_returns_422_for_wrong_field_type() -> None:
    """FastAPI should reject Director OS payloads with invalid field types."""
    response = client.post(
        "/director-os/weekly-update",
        json={
            "data_path": "data/local_only/projects",
            "focus": "leadership update",
            "max_documents": "five",
        },
    )

    assert response.status_code == 422
    assert "max_documents" in str(response.json()["detail"]).lower()


def test_brand_os_content_draft_endpoint_returns_grounded_response() -> None:
    """The Brand OS endpoint should return the public content-draft shape."""
    response = client.post(
        "/brand-os/content-draft",
        json={
            "data_path": "data/local_only/brand",
            "focus": "podcast discussion theme",
            "max_documents": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["insight_summary"]
    assert body["post_outline"]
    assert body["evidence"]


def test_brand_os_content_draft_endpoint_returns_400_for_missing_data_path() -> None:
    """The Brand OS endpoint should surface retrieval failures as HTTP 400 errors."""
    response = client.post(
        "/brand-os/content-draft",
        json={
            "data_path": "data/local_only/missing-brand",
            "focus": "podcast discussion theme",
            "max_documents": 5,
        },
    )

    assert response.status_code == 400
    assert "data path does not exist" in response.json()["detail"].lower()


def test_brand_os_content_draft_endpoint_returns_422_for_invalid_max_documents() -> None:
    """FastAPI should reject Brand OS requests that violate schema bounds."""
    response = client.post(
        "/brand-os/content-draft",
        json={
            "data_path": "data/local_only/brand",
            "focus": "podcast discussion theme",
            "max_documents": 0,
        },
    )

    assert response.status_code == 422
    assert "max_documents" in str(response.json()["detail"]).lower()


def test_brand_os_content_draft_endpoint_returns_422_for_wrong_field_type() -> None:
    """FastAPI should reject Brand OS payloads with invalid field types."""
    response = client.post(
        "/brand-os/content-draft",
        json={
            "data_path": "data/local_only/brand",
            "focus": "podcast discussion theme",
            "max_documents": "five",
        },
    )

    assert response.status_code == 422
    assert "max_documents" in str(response.json()["detail"]).lower()


def test_orchestrate_routes_to_director_os() -> None:
    """The orchestrator endpoint should route leadership prompts into Director OS."""
    response = client.post(
        "/orchestrate",
        json={
            "prompt": "Prepare my leadership weekly update",
            "data_path": "data/local_only/projects",
            "max_documents": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_workflow"] == "director_os.weekly_update"
    assert "leadership" in body["rationale"].lower()
    assert body["trace"]["section_counts"]["wins"] >= 1


def test_orchestrate_routes_to_brand_os() -> None:
    """The orchestrator endpoint should route podcast/content prompts into Brand OS."""
    response = client.post(
        "/orchestrate",
        json={
            "prompt": "Turn this work into a podcast and LinkedIn content draft",
            "data_path": "data/local_only/brand",
            "max_documents": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_workflow"] == "brand_os.content_draft"
    assert "podcast" in body["rationale"].lower()
    assert body["trace"]["section_counts"]["podcast_angles"] >= 1


def test_orchestrate_honors_explicit_director_workflow() -> None:
    """The orchestrator should bypass keyword routing when Director OS is explicit."""
    response = client.post(
        "/orchestrate",
        json={
            "workflow": "director_os.weekly_update",
            "prompt": "Turn this into a podcast",
            "data_path": "data/local_only/projects",
            "max_documents": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_workflow"] == "director_os.weekly_update"
    assert "explicitly requested" in body["rationale"].lower()


def test_orchestrate_honors_explicit_brand_workflow() -> None:
    """The orchestrator should bypass keyword routing when Brand OS is explicit."""
    response = client.post(
        "/orchestrate",
        json={
            "workflow": "brand_os.content_draft",
            "prompt": "Prepare my leadership weekly update",
            "data_path": "data/local_only/brand",
            "max_documents": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_workflow"] == "brand_os.content_draft"
    assert "explicitly requested" in body["rationale"].lower()


def test_orchestrate_prefers_brand_keywords_for_ambiguous_prompt() -> None:
    """Ambiguous prompts currently prefer Brand OS when Brand keywords appear first."""
    response = client.post(
        "/orchestrate",
        json={
            "prompt": "Prepare a leadership podcast update for this week's work",
            "data_path": "data/local_only/brand",
            "max_documents": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["selected_workflow"] == "brand_os.content_draft"
    assert "podcast" in body["rationale"].lower()


def test_orchestrate_returns_400_for_unknown_explicit_workflow() -> None:
    """Unsupported explicit workflow ids should fail as client-facing 400 errors."""
    response = client.post(
        "/orchestrate",
        json={
            "workflow": "engineering_os.repo_review",
            "data_path": "data/local_only/projects",
        },
    )

    assert response.status_code == 400
    assert "unsupported workflow" in response.json()["detail"].lower()


def test_orchestrate_returns_400_for_brand_request_with_missing_data_path() -> None:
    """Brand OS routing failures should surface as HTTP 400 errors from the API layer."""
    response = client.post(
        "/orchestrate",
        json={
            "prompt": "Turn this work into a podcast and LinkedIn content draft",
            "data_path": "data/local_only/missing-brand",
            "max_documents": 5,
        },
    )

    assert response.status_code == 400
    assert "data path does not exist" in response.json()["detail"].lower()


def test_orchestrate_returns_422_for_invalid_max_documents() -> None:
    """FastAPI should reject orchestrator requests that violate schema bounds."""
    response = client.post(
        "/orchestrate",
        json={
            "prompt": "Prepare my leadership weekly update",
            "data_path": "data/local_only/projects",
            "max_documents": 0,
        },
    )

    assert response.status_code == 422
    assert "max_documents" in str(response.json()["detail"]).lower()


def test_orchestrate_returns_422_for_wrong_field_type() -> None:
    """FastAPI should reject orchestrator payloads with invalid field types."""
    response = client.post(
        "/orchestrate",
        json={
            "prompt": "Prepare my leadership weekly update",
            "data_path": "data/local_only/projects",
            "max_documents": "five",
        },
    )

    assert response.status_code == 422
    assert "max_documents" in str(response.json()["detail"]).lower()
