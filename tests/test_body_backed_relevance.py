from datetime import UTC, datetime, tzinfo
from io import StringIO
from unittest.mock import patch
from xml.sax.saxutils import escape

import httpx
import pytest

from dapa_morning_brief.article_selection_review import review_selection
from dapa_morning_brief.briefing import build_briefing
from dapa_morning_brief.cli import main
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Section
from dapa_morning_brief.naver_news import parse_naver_items
from dapa_morning_brief.rss_parser import parse_rss_items
from dapa_morning_brief.source_config import NAVER_SEARCH_QUERIES

TITLE = "[단독] 창고에서 잠자는 4백억 원 무전기…“선이 짧아서”"
URL = "https://n.news.naver.com/mnews/article/056/0012273846"
BODY = """육군이 신형 무전기를 도입했지만 차량 연결선 문제로 운용하지 못했다.
전술 다대역 다기능 무전기 TMMR 290대가 창고에 방치됐다.
무전기 납품과 차량 납품의 사전 협의가 부족했다."""
NOW = datetime(2026, 10, 14, 14, tzinfo=UTC)


def _feed(title: str = TITLE) -> str:
    return "".join(
        (
            "<rss><channel><item>",
            f"<title>{escape(title)}</title><link>{URL}</link>",
            f"<originallink>{URL}</originallink>",
            "<source>KBS</source><description>취재 결과를 전합니다.</description>",
            "<pubDate>Wed, 14 Oct 2026 12:34:00 GMT</pubDate>",
            "</item></channel></rss>",
        )
    )


@pytest.mark.parametrize("title", [TITLE, "육군, 무전기 연결선 문제로 운용 차질"])
def test_naver_radio_reaches_confirmed_policy_selection(title: str) -> None:
    # Given
    articles = parse_naver_items(_feed(title), days=1, now=NOW)
    assert len(articles) == 1
    body = ArticleBody(URL, title, "KBS", BODY)
    # When
    result = build_briefing(articles, max_per_section=5, article_bodies=(body,))
    # Then
    assert [a.url for a in result.sections[Section.POLICY]] == [URL]
    assert not result.sections[Section.POLICY][0].requires_body_review


def test_government_feed_does_not_discard_equipment_before_body_review() -> None:
    # Given / When
    articles = parse_rss_items(
        _feed(),
        source_name="KBS",
        default_section=Section.GOVERNMENT,
        days=1,
        now=NOW,
    )
    # Then
    assert len(articles) == 1
    assert articles[0].requires_body_review


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (BODY, True),
        ("공사 현장에서 민간 작업자용 무전기의 통신 거리를 비교했다.", False),
        ("산악회가 등산용 무전기 사용법을 공유했다.", False),
        ("", False),
    ],
)
def test_full_body_determines_radio_relevance(body: str, expected: bool) -> None:
    # Given
    articles = parse_naver_items(_feed(), days=1, now=NOW)
    assert len(articles) == 1
    # When
    result = review_selection(articles[0], body)
    # Then
    assert (result.article is not None) is expected
    if expected:
        assert result.status.value == "accepted"


@pytest.mark.parametrize("equipment", ["드론", "레이더", "무전기"])
def test_equipment_rule_generalizes_beyond_one_title(equipment: str) -> None:
    # Given
    title = f"새 {equipment} 시험 성공"
    articles = parse_naver_items(_feed(title), days=1, now=NOW)
    assert len(articles) == 1
    body = f"육군은 새 {equipment} 체계의 시험평가를 완료했다."
    # When
    result = review_selection(articles[0], body)
    # Then
    assert result.article is not None
    assert result.status.value == "accepted"


def test_civilian_primary_with_military_tail_is_not_promoted() -> None:
    # Given
    articles = parse_naver_items(_feed(), days=1, now=NOW)
    assert len(articles) == 1
    body = "등산용 무전기의 민간 소비자 판매 행사를 소개했다. " * 100
    body += BODY
    # When
    result = review_selection(articles[0], body)
    # Then
    assert result.article is None


def test_tmmr_has_a_direct_naver_search_query() -> None:
    # Given / When / Then
    assert "TMMR" in NAVER_SEARCH_QUERIES


@pytest.mark.parametrize(
    ("source", "title"),
    [
        ("네이버 블로그", TITLE),
        ("KBS", "댓글 : 무전기 도입에 대한 의견"),
        ("KBS", "게임 속 무전기 성능 비교"),
        ("KBS", "무전기 업체 영업이익 증가"),
        ("KBS", "튀르키예 공군 국산 훈련기 시험 성공"),
        ("KBS", "우크라이나 자국산 미사일 첫 시험"),
    ],
)
def test_body_review_does_not_bypass_existing_exclusions(
    source: str, title: str
) -> None:
    # Given
    xml = _feed(title).replace("<source>KBS</source>", f"<source>{source}</source>")
    # When
    articles = parse_naver_items(xml, days=1, now=NOW)
    # Then
    assert not articles


@pytest.mark.parametrize("as_of", [NOW, datetime(2026, 10, 14, 21, 30, tzinfo=UTC)])
def test_cli_inspects_original_body_and_renders_radio_without_sending(
    monkeypatch: pytest.MonkeyPatch,
    as_of: datetime,
) -> None:
    # Given
    monkeypatch.delenv("DAPA_HISTORY_PATH", raising=False)
    articles = parse_naver_items(_feed(), days=1, now=NOW)
    html = "".join(
        (
            '<html><head><meta property="article:published_time" ',
            'content="2026-10-14T12:34:00+00:00"></head>',
            f"<body><article><h1>{TITLE}</h1><p>{BODY}</p></article></body></html>",
        )
    )
    response = httpx.Response(200, text=html, request=httpx.Request("GET", URL))
    output = StringIO()

    class Clock:
        @staticmethod
        def now(zone: tzinfo) -> datetime:
            return as_of.astimezone(zone)

    # When
    with (
        patch("dapa_morning_brief.cli.datetime", Clock),
        patch("dapa_morning_brief.cli.collect_articles", return_value=articles),
        patch("httpx.Client.get", return_value=response),
        patch("dapa_morning_brief.cli.collect_weather_forecasts", return_value=()),
        patch("dapa_morning_brief.cli.summarize_article_bodies") as summarize,
        patch("dapa_morning_brief.cli.send_telegram_messages") as send,
        patch("sys.stdout", output),
    ):
        result = main(["--dry-run", "--fallback-days", "1"])
    # Then
    assert result == 3
    assert URL in output.getvalue()
    summarize.assert_not_called()
    send.assert_not_called()
