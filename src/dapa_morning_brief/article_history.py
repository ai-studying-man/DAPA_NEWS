"""Persist recent collection identities without storing article bodies."""

from __future__ import annotations

import re
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import parse_qsl, urlencode, urlsplit

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dapa_morning_brief.models import Article


class HistoryEntry(BaseModel):
    """Stable identities and the collection date."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    collected_on: date
    url: str
    title: str


class ArticleHistory(BaseModel):
    """A bounded collection ledger; same-day retries remain possible."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    entries: tuple[HistoryEntry, ...] = ()

    @classmethod
    def load(cls, path: Path) -> ArticleHistory:
        """Load validated history, failing explicitly on damaged state."""
        if not path.exists():
            return cls()
        return cls.model_validate_json(path.read_bytes())

    def exclude_recent(
        self,
        articles: Iterable[Article],
        *,
        today: date,
    ) -> tuple[Article, ...]:
        """Exclude identities collected on either of the previous two days."""
        recent = tuple(
            entry
            for entry in self.entries
            if today - timedelta(days=2) <= entry.collected_on < today
        )
        urls = {entry.url for entry in recent}
        titles = {entry.title for entry in recent}
        return tuple(
            article
            for article in articles
            if canonical_url(article.url) not in urls
            and normalized_title(article.title) not in titles
        )

    def record(self, articles: Iterable[Article], *, today: date) -> ArticleHistory:
        """Retain seven days and record each day's collection once per identity."""
        entries = [
            entry
            for entry in self.entries
            if today - timedelta(days=7) <= entry.collected_on <= today
        ]
        known_urls = {entry.url for entry in entries if entry.collected_on == today}
        known_titles = {entry.title for entry in entries if entry.collected_on == today}
        for article in articles:
            url = canonical_url(article.url)
            title = normalized_title(article.title)
            if url in known_urls or title in known_titles:
                continue
            entries.append(HistoryEntry(collected_on=today, url=url, title=title))
            known_urls.add(url)
            known_titles.add(title)
        return ArticleHistory(entries=tuple(entries))

    def save(self, path: Path) -> None:
        """Replace the ledger atomically after successful preparation."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            _ = stream.write(self.model_dump_json(indent=2))
        try:
            _ = temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def canonical_url(url: str) -> str:
    """Ignore tracking parameters while retaining article identifiers."""
    parsed = urlsplit(url)
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.casefold().startswith("utm_")
            and key.casefold() not in {"fbclid", "gclid"}
        )
    )
    return f"{parsed.netloc.casefold()}{parsed.path}?{query}"


def normalized_title(title: str) -> str:
    """Match exact titles across punctuation and whitespace variants."""
    return re.sub(r"[\W_]+", "", title.casefold())
