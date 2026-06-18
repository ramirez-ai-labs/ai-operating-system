"""
Contract tests for BaseResponse and BaseRequest.

Verifies that:
  - All four domain response schemas inherit from BaseResponse
  - evidence and provider_usage are enforced by the base class
  - section_counts raises NotImplementedError when not overridden
  - All four domain responses implement section_counts correctly
"""
from __future__ import annotations

import pytest

from packages.shared.schemas.base import BaseRequest, BaseResponse, EvidenceItem, GroundedItem
from packages.shared.schemas.brand_os import BrandContentDraftResponse
from packages.shared.schemas.director_os import WeeklyUpdateResponse
from packages.shared.schemas.interview_os import InterviewBriefResponse
from packages.shared.schemas.one_on_one_os import OneOnOneResponse

_EVIDENCE = [EvidenceItem(source="a.md", line_number=1, title="A", excerpt="Win: done.")]
_ITEM = GroundedItem(text="Win: done.", source="a.md", line_number=1)


def test_all_response_schemas_inherit_base_response() -> None:
    for cls in (
        WeeklyUpdateResponse,
        BrandContentDraftResponse,
        InterviewBriefResponse,
        OneOnOneResponse,
    ):
        assert issubclass(cls, BaseResponse), f"{cls.__name__} must inherit BaseResponse"


def test_base_response_enforces_evidence_field() -> None:
    with pytest.raises(Exception):
        BaseResponse()  # type: ignore[call-arg]  # evidence is required


def test_base_response_provider_usage_defaults_to_empty_dict() -> None:
    class ConcreteResponse(BaseResponse):
        @property
        def section_counts(self) -> dict[str, int]:
            return {}

    r = ConcreteResponse(evidence=_EVIDENCE)
    assert r.provider_usage == {}


def test_base_response_section_counts_raises_when_not_overridden() -> None:
    r = BaseResponse(evidence=_EVIDENCE)
    with pytest.raises(NotImplementedError):
        _ = r.section_counts


def test_weekly_update_response_section_counts() -> None:
    r = WeeklyUpdateResponse(
        summary="ok",
        wins=[_ITEM],
        risks=[],
        next_steps=[_ITEM, _ITEM],
        evidence=_EVIDENCE,
    )
    assert r.section_counts == {"wins": 1, "risks": 0, "next_steps": 2}


def test_brand_content_draft_response_section_counts() -> None:
    r = BrandContentDraftResponse(
        insight_summary="ok",
        post_outline=[_ITEM],
        podcast_angles=[_ITEM, _ITEM],
        repo_improvements=[],
        evidence=_EVIDENCE,
    )
    assert r.section_counts == {"post_outline": 1, "podcast_angles": 2, "repo_improvements": 0}


def test_interview_brief_response_section_counts() -> None:
    r = InterviewBriefResponse(
        candidate_summary="ok",
        key_questions=[_ITEM],
        talking_points=[],
        red_flags=[_ITEM],
        evidence=_EVIDENCE,
    )
    assert r.section_counts == {"key_questions": 1, "talking_points": 0, "red_flags": 1}


def test_one_on_one_response_section_counts() -> None:
    r = OneOnOneResponse(
        meeting_summary="ok",
        action_items=[_ITEM],
        talking_points=[_ITEM],
        blockers=[],
        kudos=[_ITEM],
        evidence=_EVIDENCE,
    )
    assert r.section_counts == {
        "action_items": 1,
        "talking_points": 1,
        "blockers": 0,
        "kudos": 1,
    }


def test_base_request_common_fields_have_sensible_defaults() -> None:
    r = BaseRequest(data_path="data/local_only/projects")
    assert r.use_model is False
    assert r.provider == "claude"
    assert r.fallback_to_deterministic is True
    assert r.max_documents == 5
