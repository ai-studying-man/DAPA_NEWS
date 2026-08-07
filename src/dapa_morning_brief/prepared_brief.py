"""Persist a fully rendered Telegram briefing for scheduled delivery."""

from __future__ import annotations

from datetime import date  # noqa: TC003 - Pydantic resolves this field at runtime.
from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from pathlib import Path


class PreparedBrief(BaseModel):
    """Validated delivery payload produced before the Telegram send window."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    briefing_date: date
    message: str = Field(min_length=1)
    generated_practice_points: int = Field(ge=0)
    fallback_practice_points: int = Field(ge=0)

    @classmethod
    def load(cls, path: Path) -> PreparedBrief:
        """Load and validate a prepared briefing JSON file."""
        return cls.model_validate_json(path.read_bytes())

    def save(self, path: Path) -> None:
        """Write the prepared briefing without storing article bodies."""
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
