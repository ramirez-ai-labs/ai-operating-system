"""Domain registry: the single list of workflow domains AI-OS can route to.

The registry is built once at import from the explicit list below and is
read-only afterwards. The Chief of Staff router, the FastAPI routes, and the
standalone MCP server all read from it instead of naming domains by hand.

Adding a domain: create its spec module in this package, then add its `SPEC`
to `_REGISTERED` — one reviewable line. Registration order is the order
domains appear in the router prompt and in tool listings.

Importing this package loads only Pydantic schemas. Each spec imports its
workflow (and therefore LangGraph) on first call.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from packages.shared.domains import brand_os, director_os, interview_os, one_on_one_os
from packages.shared.domains.spec import DomainSpec, DomainTool, DomainToolInput

__all__ = [
    "DOMAINS",
    "DomainSpec",
    "DomainTool",
    "DomainToolInput",
    "default_domain",
    "domain_for_routing_token",
    "get_domain",
    "keyword_routing_order",
    "tool_definitions",
]

_REGISTERED: tuple[DomainSpec, ...] = (
    director_os.SPEC,
    brand_os.SPEC,
    interview_os.SPEC,
    one_on_one_os.SPEC,
)


def _validate(specs: tuple[DomainSpec, ...]) -> None:
    """Fail at import if the registry is inconsistent, not at request time."""

    def _unique(values: list[Any], label: str) -> None:
        duplicates = sorted({str(v) for v in values if values.count(v) > 1})
        if duplicates:
            raise ValueError(f"Duplicate domain {label} in registry: {', '.join(duplicates)}")

    _unique([s.domain for s in specs], "name")
    _unique([s.workflow_id for s in specs], "workflow_id")
    _unique([s.tool.name for s in specs], "tool name")
    _unique([s.api_path for s in specs], "api_path")
    _unique([s.keyword_priority for s in specs], "keyword_priority")

    defaults = [s.domain for s in specs if s.is_default]
    if len(defaults) != 1:
        raise ValueError(f"Registry needs exactly one default domain, found: {defaults}")

    for spec in specs:
        if not spec.workflow_id.startswith(f"{spec.domain}."):
            raise ValueError(
                f"workflow_id {spec.workflow_id!r} must start with domain {spec.domain!r}."
            )


_validate(_REGISTERED)

DOMAINS: Mapping[str, DomainSpec] = MappingProxyType(
    {spec.workflow_id: spec for spec in _REGISTERED}
)


def get_domain(workflow_id: str) -> DomainSpec:
    """Look up a domain by workflow id; unknown ids fail fast."""
    try:
        return DOMAINS[workflow_id]
    except KeyError:
        raise ValueError(
            "Unsupported workflow. Current supported workflows: "
            f"{', '.join(DOMAINS)}."
        ) from None


def domain_for_routing_token(token: str) -> DomainSpec | None:
    """Map a router classification token (e.g. 'brand_os') to its domain."""
    return next((spec for spec in DOMAINS.values() if spec.domain == token), None)


def default_domain() -> DomainSpec:
    """The domain used when a prompt is empty or matches nothing."""
    return next(spec for spec in DOMAINS.values() if spec.is_default)


def keyword_routing_order() -> list[DomainSpec]:
    """Domains in the order the keyword fallback router checks them."""
    return sorted(DOMAINS.values(), key=lambda spec: spec.keyword_priority)


def tool_definitions() -> list[dict[str, Any]]:
    """Every domain rendered as a model-facing tool definition, in registration order."""
    return [spec.tool.to_tool_definition() for spec in DOMAINS.values()]
