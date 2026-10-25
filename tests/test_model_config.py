import subprocess
import sys
from pathlib import Path

import pytest

from packages.shared.agents.researcher import ResearcherAgent
from packages.shared.agents.writer import WriterAgent
from packages.shared.config.models import (
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_OLLAMA_MODEL,
    load_models_config,
)
from packages.shared.providers.claude_provider import DEFAULT_MODEL
from packages.shared.schemas.brand_os import BrandContentDraftRequest
from packages.shared.schemas.director_os import WeeklyUpdateRequest
from packages.shared.schemas.interview_os import InterviewBriefRequest
from packages.shared.schemas.one_on_one_os import OneOnOneRequest
from packages.shared.schemas.orchestrator import OrchestratorRequest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_defaults_match_models_yaml() -> None:
    providers = load_models_config()["providers"]
    assert DEFAULT_CLAUDE_MODEL == providers["claude"]["default_model"]
    assert DEFAULT_OLLAMA_MODEL == providers["ollama"]["default_model"]


@pytest.mark.parametrize("provider", ["claude", "ollama"])
def test_default_model_is_registered_validated_and_marked_default(provider: str) -> None:
    config = load_models_config()
    default_id = config["providers"][provider]["default_model"]
    entries = {entry["id"]: entry for entry in config["models"][provider]}

    assert default_id in entries
    assert entries[default_id]["status"] == "default"
    # The default must be backed by committed live eval results.
    assert entries[default_id]["validated"] is True
    assert [e["id"] for e in entries.values() if e["status"] == "default"] == [default_id]


def test_every_request_schema_defaults_to_configured_claude_model() -> None:
    requests = [
        WeeklyUpdateRequest(),
        BrandContentDraftRequest(data_path="data/local_only/brand"),
        InterviewBriefRequest(data_path="data/local_only/interviews"),
        OneOnOneRequest(data_path="data/local_only/one_on_one"),
        OrchestratorRequest(),
    ]
    for request in requests:
        assert request.claude_model == DEFAULT_CLAUDE_MODEL, type(request).__name__


def test_ollama_defaults_use_configured_model() -> None:
    assert WeeklyUpdateRequest().ollama_model == DEFAULT_OLLAMA_MODEL
    assert OrchestratorRequest().ollama_model == DEFAULT_OLLAMA_MODEL


def test_provider_and_agents_default_to_configured_claude_model() -> None:
    assert DEFAULT_MODEL == DEFAULT_CLAUDE_MODEL
    assert ResearcherAgent().model == DEFAULT_CLAUDE_MODEL
    assert WriterAgent().model == DEFAULT_CLAUDE_MODEL


def test_missing_config_file_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="models.yaml"):
        load_models_config.__wrapped__(tmp_path / "models.yaml")


def test_mcp_server_import_defers_heavy_workflow_dependencies() -> None:
    # Regression guard for the MCP connect timeout: importing the server must
    # not load LangGraph or ChromaDB, so `initialize` is answered before a
    # client's connect timeout even on a cold start.
    code = (
        "import sys, apps.mcp.server; "
        "loaded = [m for m in ('langgraph', 'chromadb', 'langsmith') if m in sys.modules]; "
        "print(','.join(loaded))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == ""
