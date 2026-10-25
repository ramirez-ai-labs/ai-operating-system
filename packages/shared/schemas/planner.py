"""Schemas for the planner/supervisor (Phase 9b).

A plan is a list of domain tool calls. The planner decides *which* domains to
run and *what* each should retrieve; the operator's request decides *how*
(provider, model, fallback policy). Those two never mix: `PlanStep.tool_input`
is validated against the domain's narrow `DomainToolInput`, and operator
settings come only from `PlanRequest`.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from packages.shared.config.models import DEFAULT_CLAUDE_MODEL, DEFAULT_OLLAMA_MODEL
from packages.shared.schemas.orchestrator import DomainResult, WorkflowTrace

PlannerKind = Literal["rules", "ollama", "claude"]

# Fields copied from PlanRequest onto every step's domain request.
OPERATOR_SETTING_FIELDS = (
    "use_model",
    "fallback_to_deterministic",
    "provider",
    "claude_model",
    "ollama_url",
    "ollama_model",
)


class PlanRequest(BaseModel):
    """A goal for the planner, plus the operator's execution settings."""

    goal: str = Field(
        min_length=1,
        max_length=2000,
        description="What the operator wants done, e.g. 'Prep my week: leadership update, "
        "1:1 brief for Priya, and a LinkedIn post on the platform migration'.",
    )
    planner: PlannerKind = Field(
        default="rules",
        description=(
            "How to build the plan. 'rules' is deterministic and needs no model. "
            "'ollama' asks a local model; 'claude' requires ANTHROPIC_API_KEY. "
            "Model planners fall back to 'rules' when unavailable or invalid if "
            "fallback_to_deterministic is True."
        ),
    )
    max_steps: int = Field(
        default=5,
        ge=1,
        le=8,
        description="Upper bound on steps. A model plan with more steps is rejected.",
    )
    use_model: bool = Field(
        default=False,
        description="Enable model-assisted synthesis inside each step's domain workflow.",
    )
    fallback_to_deterministic: bool = Field(
        default=True,
        description="Allow deterministic fallback for the planner and for each step.",
    )
    provider: Literal["ollama", "claude"] = Field(
        default="claude",
        description="Synthesis provider for steps when use_model is True.",
    )
    claude_model: str = Field(
        default=DEFAULT_CLAUDE_MODEL,
        description="Claude model for the 'claude' planner and Claude-backed steps.",
    )
    ollama_url: str = Field(
        default="http://127.0.0.1:11434",
        description="Base URL for the local Ollama server.",
    )
    ollama_model: str = Field(
        default=DEFAULT_OLLAMA_MODEL,
        description="Ollama model for the 'ollama' planner and Ollama-backed steps.",
    )

    def operator_settings(self) -> dict[str, Any]:
        """Settings applied to every step's domain request, never set by a planner."""
        return {name: getattr(self, name) for name in OPERATOR_SETTING_FIELDS}


class PlanStep(BaseModel):
    """One domain tool call in a plan."""

    step_id: int
    workflow_id: str
    tool_name: str
    tool_input: dict[str, Any]
    rationale: str


class Plan(BaseModel):
    """The planner's output: which domains to run, with what inputs."""

    goal: str
    steps: list[PlanStep]
    planner_requested: PlannerKind
    # "rules", "ollama/<model>", or "claude/<model>" — the planner that produced the steps.
    planner_used: str
    # Set when a model planner was requested but the rules planner produced the plan.
    fallback_reason: str | None = None
    notes: list[str] = Field(default_factory=list)


class StepResult(BaseModel):
    """Outcome of one plan step. Failed steps keep their error instead of disappearing."""

    step_id: int
    workflow_id: str
    status: Literal["ok", "error"]
    error: str | None = None
    trace: WorkflowTrace | None = None
    result: DomainResult | None = None


class PlanResponse(BaseModel):
    """Merged result of a plan run."""

    goal: str
    status: Literal["ok", "partial", "error"]
    plan: Plan
    steps: list[StepResult]
    validation_summary: str
    # Token usage of the planner call itself (empty for the rules planner).
    planner_usage: dict[str, int] = Field(default_factory=dict)
