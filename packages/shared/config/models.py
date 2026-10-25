"""Single source of truth for model IDs.

Every default model ID in the codebase (request schemas, providers, agents,
eval runners) resolves through this module, which reads `config/models.yaml`.
Changing the default model is a one-line edit to that file, not a grep across
a dozen call sites.

The file is read once at import time. A missing or malformed file fails loudly
rather than silently falling back to a hardcoded ID, because a silent fallback
would reintroduce the drift this module exists to prevent.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

MODELS_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "models.yaml"


@lru_cache(maxsize=1)
def load_models_config(path: Path = MODELS_CONFIG_PATH) -> dict[str, Any]:
    """Parse `config/models.yaml` and return it as a dict."""
    if not path.is_file():
        raise FileNotFoundError(
            f"Model config not found at {path}. AI-OS reads default model IDs "
            "from config/models.yaml; run from a source checkout."
        )
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"{path} must contain a YAML mapping at the top level.")
    return config


def default_model(provider: str) -> str:
    """Return the configured default model ID for a provider ('claude' or 'ollama')."""
    providers = load_models_config().get("providers", {})
    try:
        return providers[provider]["default_model"]
    except KeyError as exc:
        raise KeyError(
            f"config/models.yaml has no providers.{provider}.default_model entry."
        ) from exc


DEFAULT_CLAUDE_MODEL = default_model("claude")
DEFAULT_OLLAMA_MODEL = default_model("ollama")
