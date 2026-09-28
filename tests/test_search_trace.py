from __future__ import annotations

from datetime import datetime

import pytest

from dapa_morning_brief.models import Section
from dapa_morning_brief.rss_parser import KST, parse_rss_items
from dapa_morning_brief.source_config import NAVER_SEARCH_QUERIES, SECTION_QUERIES


def test_radio_queries_cover_both_search_providers() -> None:
    # Given
    radio_queries = ("전투원용 무전기", "전술 무전기")
    # When
    google_queries = " ".join(SECTION_QUERIES[Section.WEAPON_SYSTEM])
    # Then
    assert all(query in NAVER_SEARCH_QUERIES for query in radio_queries)
    assert all(f'"{query}"' in google_queries for query in radio_queries)


@pytest.mark.parametrize(
    "candidate",
    [
        (
            "방사청, 무전기에 때 아닌 급발진…외부의 힘 작용 했나 [취재파일]",
            "Mon, 28 Sep 2026 09:11:45 +0900",
            "https://news.sbs.co.kr/news/endPage.do?news_id=N1008771784",
            "accepted",
        ),
        (
            "방사청 무전기 계약",
            "Sun, 27 Sep 2026 09:00:00 +0900",
            "https://example.org/old",
            "stale",
        ),
        (
            "오늘의 영화 개봉 소식",
            "Mon, 28 Sep 2026 09:00:00 +0900",
            "https://example.org/movie",
            "irrelevant",
        ),
        (
            "방사청 무전기 계약",
            "Mon, 28 Sep 2026 09:00:00 +0900",
            "",
            "missing_metadata",
        ),
    ],
)
def test_trace_records_candidate_decision(
    candidate: tuple[str, str, str, str],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given
    title, date, link, decision = candidate
    monkeypatch.setenv("DAPA_NEWS_TRACE", "1")
    xml = (
        f"<rss><channel><item><title>{title}</title><link>{link}</link>"
        f"<pubDate>{date}</pubDate><source>SBS</source></item></channel></rss>"
    )
    # When
    articles = parse_rss_items(
        xml,
        source_name="Naver",
        default_section=None,
        days=1,
        now=datetime(2026, 9, 29, 6, 30, tzinfo=KST),
    )
    # Then
    assert f"decision={decision}" in caplog.text
    assert f"title={title}" in caplog.text
    assert "published_at=" in caplog.text
    if decision == "accepted":
        assert len(articles) == 1
        assert articles[0].section is Section.POLICY
    else:
        assert articles == []


def test_candidate_trace_is_opt_in(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given
    monkeypatch.delenv("DAPA_NEWS_TRACE", raising=False)
    xml = "<rss><channel><item><title>방사청 무전기 계약</title></item></channel></rss>"
    # When
    _ = parse_rss_items(
        xml,
        source_name="Naver",
        default_section=None,
        days=1,
        now=datetime(2026, 9, 29, 6, 30, tzinfo=KST),
    )
    # Then
    assert "candidate_parse" not in caplog.text
