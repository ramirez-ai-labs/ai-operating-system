from packages.shared.observability.langsmith import (
    DEFAULT_LANGSMITH_PROJECT,
    get_langsmith_project_name,
    is_langsmith_tracing_enabled,
)


def test_langsmith_tracing_disabled_without_env(monkeypatch) -> None:
    """LangSmith should stay off unless tracing and an API key are both configured."""
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    assert not is_langsmith_tracing_enabled()


def test_langsmith_tracing_enabled_with_required_env(monkeypatch) -> None:
    """Tracing should turn on only when both required env vars are present."""
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-key")
    assert is_langsmith_tracing_enabled()


def test_langsmith_project_name_defaults_when_missing(monkeypatch) -> None:
    """The repo should use a stable default project name when none is configured."""
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    assert get_langsmith_project_name() == DEFAULT_LANGSMITH_PROJECT
