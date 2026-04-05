from __future__ import annotations

from pathlib import Path

from packages.shared.schemas.director_os import EvidenceItem


def retrieve_relevant_documents(
    base_path: str,
    query: str | None,
    limit: int,
) -> list[EvidenceItem]:
    """Search local markdown files and return the best matching evidence snippets."""
    root = Path(base_path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Data path does not exist or is not a directory: {base_path}")

    keywords = _normalize_keywords(query)
    matches: list[tuple[int, EvidenceItem]] = []

    for file_path in sorted(root.rglob("*.md")):
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
        )
        matches.extend(file_matches)

    matches.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in matches[:limit]]


def _normalize_keywords(query: str | None) -> list[str]:
    """Drop very short tokens so retrieval focuses on more meaningful terms."""
    if not query:
        return []
    return [part.lower() for part in query.split() if len(part.strip()) > 2]


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
) -> list[tuple[int, EvidenceItem]]:
    """Convert a markdown file into ranked line-level evidence items."""
    matches: list[tuple[int, EvidenceItem]] = []
    title = file_path.stem.replace("_", " ").replace("-", " ").title()

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        cleaned_line = raw_line.strip("- ").strip()
        if not cleaned_line:
            continue

        line_score = _line_score(cleaned_line, keywords)
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


def _line_score(line: str, keywords: list[str]) -> int:
    """Rank lines by keyword overlap and common status markers."""
    lowered = line.lower()
    score = sum(lowered.count(keyword) for keyword in keywords) if keywords else 1

    # Status prefixes are useful signals for the weekly-update workflow even
    # when the explicit query terms only appear elsewhere in the same file.
    if lowered.startswith(("win:", "risk:", "next:")):
        score += 2

    return score
