"""Domain spec: the one place a workflow domain describes itself to AI-OS.

A `DomainSpec` has two halves:

- **Model-facing** (`DomainTool`): name, description, and a narrow input
  schema. This is exactly a tool definition, and `to_tool_definition()`
  renders it as one. The router prompt, the MCP server, and (in Phase 9b) the
  planner all derive from it, so a domain is described once.
- **Operator-facing**: request/response models, how to build the domain
  request from an orchestrator request, keyword fallback rules, and how the
  trace detects whether the model path ran. A model never sees these.

The tool input schema is deliberately narrower than the domain request model.
A model may choose *what* to retrieve (`focus`, `data_path`, `max_documents`,
domain context fields). It may not choose provider, model ID, Ollama URL, or
fallback policy — those stay with the operator's request.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import BaseModel, Field, field_validator

from packages.shared.schemas.base import BaseResponse
from packages.shared.schemas.orchestrator import OrchestratorRequest

ALLOWED_DATA_PREFIX = PurePosixPath("data/local_only")


class DomainToolInput(BaseModel):
    """Inputs a model may set when it calls a domain as a tool.

    Domains with extra context fields (candidate name, direct report) subclass
    this. Retrieval enforces the data root again at the filesystem boundary
    (`packages/shared/retrieval/local_files.py`); this validator rejects bad
    paths before a workflow is even selected.
    """

    focus: str | None = Field(
        default=None,
        description="What to retrieve and synthesize, e.g. a project, theme, or person.",
    )
    data_path: str = Field(
        description="Directory under data/local_only containing the source notes.",
    )
    max_documents: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of evidence items to retrieve.",
    )

    @field_validator("data_path")
    @classmethod
    def _data_path_under_allowed_root(cls, value: str) -> str:
        path = PurePosixPath(value.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("data_path must be a relative path without '..'.")
        if path.parts[: len(ALLOWED_DATA_PREFIX.parts)] != ALLOWED_DATA_PREFIX.parts:
            raise ValueError(f"data_path must be under {ALLOWED_DATA_PREFIX}/.")
        # Resolved against the working directory, as retrieval does. Without this
        # check an invented folder passes planning and only fails at execution.
        if not Path(path).is_dir():
            raise ValueError(f"data_path {value!r} is not an existing directory.")
        return value


@dataclass(frozen=True)
class DomainTool:
    """Model-facing half of a domain spec — a tool definition."""

    name: str
    description: str
    input_model: type[DomainToolInput]

    def to_tool_definition(self) -> dict[str, Any]:
        """Render as a tool definition (Anthropic tool use / MCP `tools/list` shape)."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
        }


@dataclass(frozen=True)
class DomainSpec:
    """Everything AI-OS needs to route to, run, expose, and trace one domain."""

    # Routing token the Ollama classifier replies with; also the evals module name.
    domain: str
    workflow_id: str
    # Phrase completing "Use '<domain>' for: ..." in the router prompt and tool description.
    routing_hint: str
    tool: DomainTool

    request_model: type[BaseModel]
    response_model: type[BaseResponse]
    run: Callable[[Any], BaseResponse]
    # (orchestrator request, effective use_model) -> domain request
    build_request: Callable[[OrchestratorRequest, bool], BaseModel]
    # (orchestrator request, result) -> whether model synthesis produced the result
    model_used: Callable[[OrchestratorRequest, BaseResponse], bool]

    api_path: str
    supported_providers: tuple[str, ...]
    # Keyword fallback: lower priority is checked first.
    routing_keywords: tuple[str, ...]
    keyword_priority: int
    # Exactly one domain is the default for unmatched or empty prompts.
    is_default: bool = False

    def request_from_tool_input(
        self,
        tool_input: DomainToolInput,
        operator_settings: Mapping[str, Any],
    ) -> BaseModel:
        """Build the domain request from a model's tool call plus operator settings.

        The two inputs never overlap: tool inputs carry *what* to retrieve,
        operator settings carry provider, model, and fallback policy. Only fields
        the domain request model declares are passed through, so an operator
        setting a domain does not support (e.g. `ollama_model` for a Claude-only
        domain) is dropped rather than rejected.
        """
        fields = self.request_model.model_fields
        values = {key: value for key, value in operator_settings.items() if key in fields}
        values.update(tool_input.model_dump())
        return self.request_model(**values)
