from __future__ import annotations

import os
from contextlib import nullcontext
from typing import ContextManager

from langsmith import traceable, tracing_context

DEFAULT_LANGSMITH_PROJECT = "ai-os"


def is_langsmith_tracing_enabled() -> bool:
    """Return whether LangSmith tracing is configured for the current process."""
    tracing_flag = os.getenv("LANGSMITH_TRACING", "").lower()
    return tracing_flag == "true" and bool(os.getenv("LANGSMITH_API_KEY"))


def get_langsmith_project_name() -> str:
    """Return the LangSmith project name, defaulting to a stable AI-OS project."""
    return os.getenv("LANGSMITH_PROJECT", DEFAULT_LANGSMITH_PROJECT)


def get_langsmith_tracing_context() -> ContextManager[object]:
    """Return a real tracing context when enabled, otherwise a no-op context."""
    if not is_langsmith_tracing_enabled():
        return nullcontext()
    return tracing_context(
        enabled=True,
        project_name=get_langsmith_project_name(),
    )


__all__ = [
    "get_langsmith_project_name",
    "get_langsmith_tracing_context",
    "is_langsmith_tracing_enabled",
    "traceable",
]
