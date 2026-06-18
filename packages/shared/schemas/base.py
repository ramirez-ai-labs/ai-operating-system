from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """Minimal evidence payload returned from local retrieval."""

    source: str
    line_number: int
    title: str
    excerpt: str


class GroundedItem(BaseModel):
    """Output item tied to a specific supporting evidence location."""

    text: str
    source: str
    line_number: int


class BaseRequest(BaseModel):
    """Common fields shared by all AI-OS domain request schemas.

    Domain request classes inherit from this to get the standard field set.
    Fields that are domain-specific (e.g. candidate_name, direct_report)
    are added in the concrete subclass.
    """

    data_path: str
    focus: str | None = None
    max_documents: int = Field(default=5, ge=1, le=20)
    use_model: bool = False
    provider: str = "claude"
    claude_model: str = "claude-haiku-4-5-20251001"
    fallback_to_deterministic: bool = True


class BaseResponse(BaseModel):
    """Contract all AI-OS domain response schemas must satisfy.

    Inheriting from BaseResponse enforces:
      - evidence: list[EvidenceItem]   (required, populated by retrieve_evidence)
      - provider_usage: dict[str, int] (optional, populated by model providers)

    Concrete response classes MUST also override section_counts with a
    @property that returns {section_name: len(section_list), ...}.
    Forgetting to override raises NotImplementedError at runtime when
    _build_trace calls result.section_counts.
    """

    evidence: list[EvidenceItem]
    provider_usage: dict[str, int] = Field(default_factory=dict)

    @property
    def section_counts(self) -> dict[str, int]:
        raise NotImplementedError(
            f"{type(self).__name__} must implement section_counts. "
            "Add a @property returning {section_name: len(items), ...}."
        )
