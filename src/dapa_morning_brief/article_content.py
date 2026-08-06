"""Download selected news pages and extract their main article text."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, ClassVar, Final

import httpx
import trafilatura
from googlenewsdecoder import gnewsdecoder
from pydantic import BaseModel, ConfigDict, ValidationError

from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.source_config import USER_AGENT

if TYPE_CHECKING:
    from dapa_morning_brief.models import Briefing

MAX_BODY_CHARACTERS: Final = 4_000
MIN_BODY_CHARACTERS: Final = 40


class _DecodedGoogleUrl(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    status: bool
    decoded_url: str | None = None


def extract_main_text(html_text: str) -> str | None:
    """Extract bounded article text from an HTML document."""
    extracted = trafilatura.extract(
        html_text,
        favor_precision=True,
        include_comments=False,
        include_tables=False,
        output_format="txt",
    )
    if extracted is None:
        return None
    normalized = " ".join(extracted.split())
    if len(normalized) < MIN_BODY_CHARACTERS:
        return None
    return normalized[:MAX_BODY_CHARACTERS]


def resolve_article_url(article_url: str) -> str:
    """Resolve Google News RSS links to their publisher URL when possible."""
    if not article_url.startswith("https://news.google.com/"):
        return article_url
    try:
        decoded = _DecodedGoogleUrl.model_validate(gnewsdecoder(article_url))
    except ValidationError:
        return article_url
    if decoded.status and decoded.decoded_url:
        return decoded.decoded_url
    return article_url


def fetch_article_bodies(briefing: Briefing) -> tuple[ArticleBody, ...]:
    """Fetch bodies only for articles selected into the final briefing."""
    timeout = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
    headers = {"User-Agent": os.getenv("DAPA_BRIEF_USER_AGENT", USER_AGENT)}
    bodies: list[ArticleBody] = []
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers=headers,
    ) as client:
        for articles in briefing.sections.values():
            for article in articles:
                try:
                    response = client.get(resolve_article_url(article.url))
                    _ = response.raise_for_status()
                except httpx.HTTPError:
                    continue
                body = extract_main_text(response.text)
                if body is None:
                    continue
                bodies.append(
                    ArticleBody(
                        article_url=article.url,
                        title=article.title,
                        source=article.source,
                        body=body,
                    ),
                )
    return tuple(bodies)
