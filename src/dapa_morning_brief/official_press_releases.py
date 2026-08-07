"""Collect the latest press releases from official agency boards."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from typing import TYPE_CHECKING, Final
from urllib.parse import urljoin

import httpx
from typing_extensions import override

from dapa_morning_brief.models import OfficialPressRelease
from dapa_morning_brief.press_release_cache import (
    load_cached_press_releases,
    save_cached_press_releases,
)
from dapa_morning_brief.source_config import USER_AGENT

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

_DAPA_DETAIL_URL: Final[str] = "https://www.dapa.go.kr/dapa/doc/selectDoc.do"
_DAPA_LIST_URL: Final[str] = (
    "https://www.dapa.go.kr/dapa/doc/selectDocList.do?bbsSeq=326&menuSeq=3069"
)
_MND_BASE_URL: Final[str] = "https://www.mnd.go.kr"
_MND_LIST_URL: Final[str] = "https://www.mnd.go.kr/mnd/167/subview.do"
_DAPA_DOCUMENT_ID: Final[re.Pattern[str]] = re.compile(
    r"fn_selectDoc\('(?P<document_id>\d+)'\)",
)
_DAPA_DATE: Final[re.Pattern[str]] = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True, slots=True)
class _HtmlCell:
    class_names: frozenset[str]
    text: str
    href: str | None
    onclick: str | None


class _BoardTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[tuple[_HtmlCell, ...]] = []
        self._cells: list[_HtmlCell] | None = None
        self._class_names: frozenset[str] | None = None
        self._text_parts: list[str] | None = None
        self._href: str | None = None
        self._onclick: str | None = None

    @override
    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        if tag == "tr":
            self._cells = []
        elif tag == "td" and self._cells is not None:
            self._class_names = frozenset((attributes.get("class") or "").split())
            self._text_parts = []
            self._href = None
            self._onclick = None
        elif tag == "a" and self._text_parts is not None:
            self._href = attributes.get("href")
            self._onclick = attributes.get("onclick")

    @override
    def handle_data(self, data: str) -> None:
        if self._text_parts is not None:
            self._text_parts.append(data)

    @override
    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._cells is not None and self._text_parts is not None:
            text = " ".join("".join(self._text_parts).split())
            text = text.removesuffix("새 글").removesuffix("새글").rstrip()
            self._cells.append(
                _HtmlCell(
                    class_names=self._class_names or frozenset(),
                    text=text,
                    href=self._href,
                    onclick=self._onclick,
                ),
            )
            self._class_names = None
            self._text_parts = None
            self._href = None
            self._onclick = None
        elif tag == "tr" and self._cells is not None:
            if self._cells:
                self.rows.append(tuple(self._cells))
            self._cells = None


def parse_dapa_press_releases(document: str) -> tuple[OfficialPressRelease, ...]:
    """Parse DAPA board rows into direct official detail links."""
    parser = _BoardTableParser()
    parser.feed(document)
    releases: list[OfficialPressRelease] = []
    for row in parser.rows:
        subject = next((cell for cell in row if "subject" in cell.class_names), None)
        date_cell = next(
            (cell for cell in row if _DAPA_DATE.fullmatch(cell.text)),
            None,
        )
        if subject is None or subject.onclick is None or date_cell is None:
            continue
        document_match = _DAPA_DOCUMENT_ID.search(subject.onclick)
        if document_match is None:
            continue
        document_id = document_match.group("document_id")
        releases.append(
            OfficialPressRelease(
                agency="방위사업청",
                title=subject.text,
                url=(
                    f"{_DAPA_DETAIL_URL}?bbsSeq=326&docSeq={document_id}&menuSeq=3069"
                ),
                published_on=date.fromisoformat(date_cell.text),
            ),
        )
    return tuple(releases)


def parse_mnd_press_releases(document: str) -> tuple[OfficialPressRelease, ...]:
    """Parse Ministry of National Defense board rows."""
    parser = _BoardTableParser()
    parser.feed(document)
    releases: list[OfficialPressRelease] = []
    for row in parser.rows:
        title_cell = next(
            (cell for cell in row if "td-title" in cell.class_names),
            None,
        )
        date_cell = next(
            (cell for cell in row if "td-date" in cell.class_names),
            None,
        )
        if title_cell is None or title_cell.href is None or date_cell is None:
            continue
        releases.append(
            OfficialPressRelease(
                agency="국방부",
                title=title_cell.text,
                url=urljoin(_MND_BASE_URL, title_cell.href),
                published_on=date.fromisoformat(date_cell.text.replace(".", "-")),
            ),
        )
    return tuple(releases)


def select_latest_press_release(
    releases: Iterable[OfficialPressRelease],
    *,
    as_of: date,
) -> OfficialPressRelease | None:
    """Return the newest release not later than the requested date."""
    return max(
        (release for release in releases if release.published_on <= as_of),
        key=lambda release: release.published_on,
        default=None,
    )


def collect_latest_press_releases(
    *,
    as_of: date,
    client: httpx.Client | None = None,
    cache_path: Path | None = None,
) -> tuple[OfficialPressRelease, ...]:
    """Collect the newest available release from each official board."""
    cached = load_cached_press_releases(cache_path) if cache_path is not None else ()
    if client is not None:
        collected = _collect_with_client(client, as_of=as_of, cached=cached)
        if cache_path is not None:
            save_cached_press_releases(cache_path, collected)
        return collected

    timeout = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=10.0)
    limits = httpx.Limits(
        max_connections=20,
        max_keepalive_connections=10,
        keepalive_expiry=30.0,
    )
    transport = httpx.HTTPTransport(retries=3, limits=limits)
    with httpx.Client(
        transport=transport,
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as owned_client:
        collected = _collect_with_client(owned_client, as_of=as_of, cached=cached)
    if cache_path is not None:
        save_cached_press_releases(cache_path, collected)
    return collected


def _collect_with_client(
    client: httpx.Client,
    *,
    as_of: date,
    cached: tuple[OfficialPressRelease, ...],
) -> tuple[OfficialPressRelease, ...]:
    collected: list[OfficialPressRelease] = []
    sources = (
        ("국방부", _MND_LIST_URL, parse_mnd_press_releases),
        ("방위사업청", _DAPA_LIST_URL, parse_dapa_press_releases),
    )
    for agency, url, parser in sources:
        try:
            response = client.get(url)
            _ = response.raise_for_status()
            current = parser(response.text)
        except (httpx.HTTPError, ValueError):
            current = ()
        candidates = current + tuple(
            release for release in cached if release.agency == agency
        )
        latest = select_latest_press_release(candidates, as_of=as_of)
        if latest is not None:
            collected.append(latest)
    return tuple(collected)
