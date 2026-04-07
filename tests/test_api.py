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
