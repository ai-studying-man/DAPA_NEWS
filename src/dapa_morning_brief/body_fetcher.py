"""Shared article inspection boundary for candidate and history preparation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from dapa_morning_brief.copilot_summary import ArticleBody
    from dapa_morning_brief.models import Briefing


class BodyFetcher(Protocol):
    """Fetch existing article bodies without invoking delivery or generation."""

    def __call__(
        self, briefing: Briefing, *, include_government: bool
    ) -> tuple[ArticleBody, ...]:
        """Fetch news bodies for a bounded candidate batch."""
        ...
