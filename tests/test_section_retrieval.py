"""Retrieval returns lines each domain can actually turn into sections.

Before this fix, a weak or missing focus made Brand OS and Interview OS fail
validation with "must include at least one populated section": stopwords such
as "the" dominated keyword scoring, and only Director OS's three section
labels got a ranking boost. Validators are unchanged — the fix is in what
retrieval hands them.
"""

from __future__ import annotations

import pytest

from packages.shared.domains import DOMAINS
from packages.shared.graphs import brand_os, director_os, interview_os, one_on_one_os
from packages.shared.graphs.interview_os import _matches_interview_section
from packages.shared.retrieval import local_files
from packages.shared.retrieval.local_files import (
    DEFAULT_SECTION_LABELS,
    _line_score,
    _normalize_keywords,
)
from packages.shared.schemas.base import EvidenceItem
from packages.shared.schemas.interview_os import InterviewBriefRequest, InterviewBriefResponse
from packages.shared.validation.interview_os import validate_interview_brief


def test_stopwords_and_punctuation_are_dropped_from_queries() -> None:
    assert _normalize_keywords("a LinkedIn post on the platform migration") == [
        "linkedin",
        "post",
        "platform",
        "migration",
    ]
    assert _normalize_keywords("1:1 with Priya, about blockers.") == ["1:1", "priya", "blockers"]


def _labels(*labels: str) -> tuple[str, ...]:
    return tuple(label.lower() for label in labels)


def test_only_the_calling_domains_labels_are_boosted() -> None:
    director = _labels(*director_os.SECTION_LABELS)
    one_on_one = _labels(*one_on_one_os.SECTION_LABELS)

    base = _line_score("Owner: platform team", [], 0, director)
    assert _line_score("Risk: vendor delay", [], 0, director) == base + 2
    # Metadata labels are not section labels and get no boost.
    assert _line_score("Status: Blocked awaiting review", [], 0, director) == base
    # Another domain's label is not boosted for Director OS...
    assert _line_score("Action: send the RFC", [], 0, director) == base
    # ...but is for the domain that extracts it.
    assert _line_score("Action: send the RFC", [], 0, one_on_one) == base + 2


def test_default_labels_preserve_original_director_behavior() -> None:
    assert DEFAULT_SECTION_LABELS == director_os.SECTION_LABELS


@pytest.mark.parametrize(
    "graph", [brand_os, director_os, interview_os, one_on_one_os], ids=lambda g: g.__name__
)
def test_every_domain_graph_declares_section_labels(graph) -> None:
    assert graph.SECTION_LABELS
    assert all(label.endswith(":") for label in graph.SECTION_LABELS)


@pytest.mark.parametrize(
    ("workflow_id", "focus"),
    [
        ("brand_os.content_draft", "a LinkedIn post on the platform migration"),
        ("brand_os.content_draft", None),
        ("interview_os.brief", None),
        ("interview_os.brief", "interview prep for Alex Chen"),
        ("one_on_one_os.brief", None),
        ("one_on_one_os.brief", "1:1 brief for Priya"),
        ("director_os.weekly_update", None),
    ],
)
def test_weak_or_missing_focus_still_produces_a_grounded_brief(workflow_id, focus) -> None:
    spec = DOMAINS[workflow_id]
    request = spec.request_from_tool_input(spec.tool.input_model(focus=focus), {})
    result = spec.run(request)  # raised "must include at least one populated section" before
    assert any(result.section_counts.values())


def test_plain_questions_count_as_interview_key_questions() -> None:
    def matches(line: str, section: str, prefixes: tuple[str, ...], keywords=()) -> bool:
        return _matches_interview_section(
            lowered_excerpt=line.lower(),
            section_name=section,
            allowed_prefixes=prefixes,
            keywords=keywords,
        )

    question = "What happened, what was your role, and what did you change afterward?"
    assert matches(question, "key_questions", ("Question:", "Q:"))
    # A line another section claims by label stays in that section.
    assert not matches("Concern: unclear ownership?", "key_questions", ("Question:", "Q:"))
    # The "?" rule applies to key_questions only.
    assert not matches(question, "talking_points", ("Talking Point:",))


def test_interview_brief_with_no_focus_and_few_documents_is_grounded() -> None:
    # This used to fail: file order outranked labeled lines, so the top 3 were
    # the guide's intro text.
    spec = DOMAINS["interview_os.brief"]
    request = spec.request_from_tool_input(spec.tool.input_model(max_documents=3), {})
    assert any(spec.run(request).section_counts.values())


@pytest.mark.parametrize("request_", [None, InterviewBriefRequest()], ids=["no-request", "unset"])
def test_interview_empty_brief_error_says_how_to_fix_the_request(request_) -> None:
    with pytest.raises(ValueError, match="Set focus, candidate_name, or role"):
        validate_interview_brief(_empty_interview_brief(), request_)


def _empty_interview_brief() -> InterviewBriefResponse:
    evidence = EvidenceItem(source="guide.md", line_number=1, title="Guide", excerpt="Date: today")
    return InterviewBriefResponse(
        candidate_summary="Brief.",
        key_questions=[],
        talking_points=[],
        red_flags=[],
        evidence=[evidence],
    )


def test_interview_empty_brief_error_does_not_ask_for_fields_already_set() -> None:
    request = InterviewBriefRequest(focus="system design", candidate_name="Ana", role="SRE")
    with pytest.raises(ValueError) as exc:
        validate_interview_brief(_empty_interview_brief(), request)
    message = str(exc.value)
    assert "Set focus, candidate_name, or role" not in message
    assert "max_documents" in message


def test_section_labels_outrank_file_order_with_many_notes(tmp_path, monkeypatch) -> None:
    # File order used to add up to +len(files) to every line, so past a handful
    # of notes it buried labeled lines from older files under unlabeled ones.
    monkeypatch.setattr(local_files, "ALLOWED_LOCAL_DATA_ROOT", tmp_path.resolve())
    for index in range(12):
        (tmp_path / f"note_{index:02d}.md").write_text("Date: 2026-10-01\n", encoding="utf-8")
    # The last file in sort order gets the lowest file priority.
    (tmp_path / "note_11.md").write_text(
        "Date: 2026-10-01\nAction: send the RFC\n", encoding="utf-8"
    )

    top = local_files.retrieve_relevant_documents(
        str(tmp_path), None, limit=1, section_labels=("Action:",)
    )

    assert [item.excerpt for item in top] == ["Action: send the RFC"]


def test_file_order_still_breaks_ties(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(local_files, "ALLOWED_LOCAL_DATA_ROOT", tmp_path.resolve())
    (tmp_path / "a.md").write_text("Action: from a\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("Action: from b\n", encoding="utf-8")

    top = local_files.retrieve_relevant_documents(
        str(tmp_path), None, limit=1, section_labels=("Action:",)
    )

    assert [item.source for item in top] == ["a.md"]
