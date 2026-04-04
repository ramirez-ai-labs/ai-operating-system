from __future__ import annotations

from pathlib import Path

from packages.shared.schemas.director_os import EvidenceItem


def retrieve_relevant_documents(
    base_path: str,
    query: str | None,
    limit: int,
) -> list[EvidenceItem]:
    root = Path(base_path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Data path does not exist or is not a directory: {base_path}")

    keywords = _normalize_keywords(query)
    matches: list[tuple[int, EvidenceItem]] = []

    for file_path in sorted(root.rglob("*.md")):
        text = file_path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        score = _score_text(text, keywords)
        if keywords and score == 0:
            continue

        excerpt = _best_excerpt(text, keywords)
        matches.append(
            (
                score,
                EvidenceItem(
                    source=str(file_path.relative_to(root)),
                    title=file_path.stem.replace("_", " ").replace("-", " ").title(),
                    excerpt=excerpt,
                ),
            )
        )

    matches.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in matches[:limit]]


def _normalize_keywords(query: str | None) -> list[str]:
    if not query:
        return []
    return [part.lower() for part in query.split() if len(part.strip()) > 2]


def _score_text(text: str, keywords: list[str]) -> int:
    if not keywords:
        return 1
    lowered = text.lower()
    return sum(lowered.count(keyword) for keyword in keywords)


def _best_excerpt(text: str, keywords: list[str]) -> str:
    lines = [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ""

    for line in lines:
        lowered = line.lower()
        if not keywords or any(keyword in lowered for keyword in keywords):
            return line[:280]
    return lines[0][:280]
