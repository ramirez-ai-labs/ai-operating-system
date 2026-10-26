"""Suite-wide test isolation."""

from __future__ import annotations

import urllib.error
import urllib.request

import pytest

_OLLAMA_PORT = ":11434"


@pytest.fixture(autouse=True)
def _no_live_ollama(monkeypatch):
    """Fail every request to a local Ollama as if it were not running.

    The router, planner, Director OS provider, and chroma embeddings all call
    Ollama when it is reachable, so a developer machine with Ollama running got
    different results from CI. Tests that exercise an Ollama path patch
    `urllib.request.urlopen` themselves, which overrides this for their scope.
    """
    real_urlopen = urllib.request.urlopen

    def urlopen(url, *args, **kwargs):
        full_url = getattr(url, "full_url", url)
        if _OLLAMA_PORT in str(full_url):
            raise urllib.error.URLError("Ollama is disabled in the test suite")
        return real_urlopen(url, *args, **kwargs)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
