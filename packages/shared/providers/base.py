from __future__ import annotations

from abc import ABC, abstractmethod

from packages.shared.schemas.director_os import EvidenceItem, WeeklyUpdateDraft


class WeeklyUpdateProvider(ABC):
    """Provider interface for model-assisted weekly update synthesis."""

    @abstractmethod
    def generate_weekly_update(
        self,
        focus: str | None,
        evidence: list[EvidenceItem],
    ) -> WeeklyUpdateDraft:
        """Return a structured draft synthesized from grounded evidence."""
