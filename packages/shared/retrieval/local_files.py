from __future__ import annotations

from pathlib import Path

from packages.shared.schemas.director_os import EvidenceItem

ALLOWED_LOCAL_DATA_ROOT = (Path.cwd() / "data" / "local_only").resolve()

# Function words that appear in almost every line. Counting them let a focus
# like "a post on the platform migration" rank lines by how often they say
# "the", crowding out the lines that actually match the topic.
_STOPWORDS = frozenset(
    {
        "the", "and", "for", "with", "about", "from", "into", "onto", "over",
        "this", "that", "these", "those", "our", "your", "their", "its",
        "are", "was", "were", "has", "have", "had", "but", "not", "all", "any",
        "can", "will", "would", "should", "what", "when", "who", "how",
        "you", "her", "his", "him", "she", "they", "them", "than", "then",
        "there", "here", "also", "just", "get", "out",
    }
)

# Section labels boosted when a caller does not pass its own. These are
# Director OS's labels, the only ones retrieval used to know about.
DEFAULT_SECTION_LABELS: tuple[str, ...] = ("Win:", "Risk:", "Next:")


def retrieve_relevant_documents(
    base_path: str,
    query: str | None,
    limit: int,
    section_labels: tuple[str, ...] = DEFAULT_SECTION_LABELS,
) -> list[EvidenceItem]:
    """Search local markdown files and return the best matching evidence snippets.

    `section_labels` are the line labels the calling domain extracts sections
    from (e.g. "Action:", "Blocker:"). Lines starting with one get a small rank
    boost, so a domain's evidence is made of lines it can actually use.
    """
    # Retrieval is intentionally local-only: the workflow only looks at files
    # under the provided directory and never calls an external service here.
    root = _resolve_allowed_data_path(base_path)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Data path does not exist or is not a directory: {base_path}")

    # Turn a free-form query into simple keywords. This is intentionally basic:
    # the MVP is using understandable ranking rules instead of embeddings.
    keywords = _normalize_keywords(query)
    matches: list[tuple[float, EvidenceItem]] = []
    all_files = sorted(root.rglob("*.md"))
    # File order is a tie-breaker only: a fraction below 1, so it never outweighs
    # a keyword hit (10) or a section label (2). As whole numbers it grew with
    # the file count and buried labeled lines in older notes.
    file_rank = {
        file_path.resolve(): (len(all_files) - index) / (len(all_files) + 1)
        for index, file_path in enumerate(all_files)
    }

    for file_path in all_files:
        text = file_path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        # Return multiple evidence lines from a single file so one note can surface
        # wins, risks, and next steps together instead of collapsing to one excerpt.
        file_matches = _extract_matching_lines(
            file_path=file_path,
            root=root,
            text=text,
            keywords=keywords,
            file_priority=file_rank[file_path.resolve()],
            section_labels=tuple(label.lower() for label in section_labels),
        )
        matches.extend(file_matches)

    matches.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in matches[:limit]]


def _resolve_allowed_data_path(base_path: str) -> Path:
    """Restrict retrieval to the approved local data workspace for the MVP."""
    root = Path(base_path).resolve()
    try:
        root.relative_to(ALLOWED_LOCAL_DATA_ROOT)
    except ValueError as exc:
        raise ValueError(
            "Data path must stay within the approved local data root: "
            f"{ALLOWED_LOCAL_DATA_ROOT}"
        ) from exc
    return root


def _normalize_keywords(query: str | None) -> list[str]:
    """Drop very short tokens and stopwords so retrieval focuses on meaningful terms."""
    if not query:
        return []
    keywords = []
    for part in query.split():
        token = part.strip(" .,;:!?\"'()").lower()
        if len(token) > 2 and token not in _STOPWORDS:
            keywords.append(token)
    return keywords


def _score_text(text: str, keywords: list[str]) -> int:
    """Use a basic count-based score until richer retrieval is needed."""
    if not keywords:
        return 1
    lowered = text.lower()
    return sum(lowered.count(keyword) for keyword in keywords)


def _extract_matching_lines(
    file_path: Path,
    root: Path,
    text: str,
    keywords: list[str],
    file_priority: float,
    section_labels: tuple[str, ...],
) -> list[tuple[float, EvidenceItem]]:
    """Convert a markdown file into ranked line-level evidence items."""
    matches: list[tuple[float, EvidenceItem]] = []
    title = file_path.stem.replace("_", " ").replace("-", " ").title()

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        # Retrieval works at the line level, not the whole-file level. That
        # makes the grounding story easier to explain because each output item
        # can point back to one specific line in one specific file.
        # Strip common markdown list markers so the evidence text reads like a
        # normal sentence in the API response.
        cleaned_line = raw_line.strip("- ").strip()
        if not cleaned_line:
            continue
        if _should_skip_line(cleaned_line):
            continue

        line_score = _line_score(cleaned_line, keywords, file_priority, section_labels)
        if keywords and line_score == 0:
            continue

        matches.append(
            (
                line_score,
                EvidenceItem(
                    source=str(file_path.relative_to(root)),
                    line_number=line_number,
                    title=title,
                    excerpt=cleaned_line[:280],
                ),
            )
        )

    return matches


def _line_score(
    line: str,
    keywords: list[str],
    file_priority: float,
    section_labels: tuple[str, ...],
) -> float:
    """Rank lines by keyword overlap and common status markers."""
    lowered = line.lower()
    # The score is just a weighted keyword count plus a couple of simple boosts.
    # It is not "smart", but it is transparent and easy to debug.
    score = (
        sum(lowered.count(keyword) * 10 for keyword in keywords)
        if keywords
        else 1
    )

    # Lines carrying one of the calling domain's section labels are what its
    # deterministic synthesis extracts, so they get a small boost even when the
    # query terms only appear elsewhere in the same file. Labels are per domain:
    # boosting every "Label:" line also boosted metadata such as "Status:" and
    # let it crowd out usable lines.
    if lowered.startswith(section_labels):
        score += 2

    # Lightly bias toward later files so newer-looking notes edge out older ones
    # when relevance is otherwise similar.
    score += file_priority

    return score


def _should_skip_line(line: str) -> bool:
    """Ignore headings and weak structural lines that do not help grounding."""
    stripped = line.strip()
    if not stripped:
        return True
    # Headings add structure for humans reading markdown files, but they are
    # not strong evidence for a weekly update output.
    if stripped.startswith("#"):
        return True
    return False
