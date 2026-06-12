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

    def get_last_usage(self) -> dict[str, int]:
        """Return token counts from the most recent generate_weekly_update call.

        Providers that support prompt caching override this to surface
        cache_read_input_tokens and cache_creation_input_tokens so callers
        can record them in the WorkflowTrace without coupling to specific
        provider implementations.
        """
        return {}
