from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import patch

import httpx
import pytest

from dapa_morning_brief import collector, naver_news
from dapa_morning_brief.models import Section
from dapa_morning_brief.official_press_releases import parse_dapa_press_releases
from dapa_morning_brief.official_sources import parse_board_articles


def test_all_failed_sources_raise_instead_of_empty_brief() -> None:
    # Given
    transport = httpx.MockTransport(lambda _: httpx.Response(503))
    client = httpx.Client(transport=transport)
    with (
        patch("dapa_morning_brief.collector.httpx.Client", return_value=client),
        patch.dict("os.environ", {"NAVER_CLIENT_ID": "", "NAVER_CLIENT_SECRET": ""}),
        pytest.raises(RuntimeError, match="sources failed"),
    ):
        # When / Then
        _ = collector.collect_articles(days=1, include_google=True, only_google=True)


def test_naver_adapter_uses_original_link_and_cleans_markup() -> None:
    # Given

    xml = """<rss><channel><item><title>&lt;b&gt;방위사업청&lt;/b&gt; 계약 발표</title>
    <originallink>https://publisher.example/news/1</originallink>
    <link>https://news.naver.com/1</link><description>신규 획득사업</description>
    <pubDate>Thu, 17 Sep 2026 05:00:00 +0900</pubDate></item></channel></rss>"""
    # When
    articles = naver_news.parse_naver_items(
        xml, days=1, now=datetime(2026, 9, 17, tzinfo=UTC)
    )
    # Then
    assert len(articles) == 1
    assert articles[0].url == "https://publisher.example/news/1"
    assert articles[0].title == "방위사업청 계약 발표"
    assert articles[0].source == "publisher.example"
    assert articles[0].search_provider == "naver"


def test_partial_source_outage_keeps_successful_results() -> None:
    # Given
    def respond(request: httpx.Request) -> httpx.Response:
        if "방위사업청" in request.url.params.get("q", ""):
            return httpx.Response(200, text="<rss><channel/></rss>")
        return httpx.Response(503)

    client = httpx.Client(transport=httpx.MockTransport(respond))
    with patch("dapa_morning_brief.collector.httpx.Client", return_value=client):
        # When
        articles = collector.collect_articles(
            days=1, include_google=True, only_google=True
        )
    # Then
    assert articles == []


def test_naver_credentials_only_sent_to_naver_and_errors_redacted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given
    observed: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(401)

    client = httpx.Client(transport=httpx.MockTransport(respond))
    with (
        patch("dapa_morning_brief.collector.httpx.Client", return_value=client),
        patch.dict(
            "os.environ",
            {"NAVER_CLIENT_ID": "test-id", "NAVER_CLIENT_SECRET": "secret-value"},
        ),
        pytest.raises(collector.CollectionError),
    ):
        # When
        _ = collector.collect_articles(days=1, include_google=True, only_google=False)
    # Then
    naver_requests = [
        request for request in observed if request.url.host == "openapi.naver.com"
    ]
    assert naver_requests
    assert all(
        request.headers.get("X-Naver-Client-Secret") == "secret-value"
        for request in naver_requests
    )
    assert all(
        "X-Naver-Client-Secret" not in request.headers
        for request in observed
        if request.url.host != "openapi.naver.com"
    )
    assert "secret-value" not in caplog.text
    assert "status=401" in caplog.text
    assert all(request.url.params["sort"] == "date" for request in naver_requests)
    assert all(" OR " not in request.url.params["query"] for request in naver_requests)


def test_board_articles_use_content_classification() -> None:
    # Given

    html = """<table><tr><td class="subject"><a
    onclick="fn_selectDoc('55')">KF-21 후속양산</a></td>
    <td>2026-09-17</td></tr></table>"""
    # When
    articles = parse_board_articles(
        html,
        parser=parse_dapa_press_releases,
        days=1,
        now=datetime(2026, 9, 17, tzinfo=UTC),
    )
    # Then
    assert articles[0].section is Section.WEAPON_SYSTEM
    assert "docSeq=55" in articles[0].url


def test_html_success_response_is_collection_failure() -> None:
    # Given
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, text="<html><body>Unavailable</body></html>"),
        )
    )
    with (
        patch("dapa_morning_brief.collector.httpx.Client", return_value=client),
        pytest.raises(collector.CollectionError),
    ):
        # When / Then
        _ = collector.collect_articles(days=1, include_google=True, only_google=True)


def test_missing_credentials_skip_naver_and_google_disabled_is_respected(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given
    observed: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        observed.append(request.url.host)
        return httpx.Response(200, text="<rss><channel/></rss>")

    client = httpx.Client(transport=httpx.MockTransport(respond))
    with (
        patch("dapa_morning_brief.collector.httpx.Client", return_value=client),
        patch.dict("os.environ", {"NAVER_CLIENT_ID": "", "NAVER_CLIENT_SECRET": ""}),
    ):
        # When
        _ = collector.collect_articles(days=1, include_google=False, only_google=False)
    # Then
    assert "openapi.naver.com" not in observed
    assert "news.google.com" not in observed
    assert "reason=missing_credentials" in caplog.text


def test_naver_redirect_does_not_forward_credentials_to_another_host() -> None:
    # Given
    observed: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(
            302, headers={"Location": "https://external.example/news"}
        )

    client = httpx.Client(transport=httpx.MockTransport(respond))
    with (
        patch("dapa_morning_brief.collector.httpx.Client", return_value=client),
        patch("dapa_morning_brief.collector.RSS_SOURCES", ()),
        patch("dapa_morning_brief.collector.BOARD_SOURCES", ()),
        patch("dapa_morning_brief.collector.NAVER_SEARCH_QUERIES", ("방사청",)),
        patch.dict(
            "os.environ",
            {"NAVER_CLIENT_ID": "test-id", "NAVER_CLIENT_SECRET": "secret-value"},
        ),
        pytest.raises(collector.CollectionError),
    ):
        # When
        _ = collector.collect_articles(days=1, include_google=False, only_google=False)
    # Then
    assert len(observed) == 1
    assert observed[0].url.host == "openapi.naver.com"


@pytest.fixture(autouse=True)
def immediate_naver_waits() -> Iterator[None]:
    with patch("dapa_morning_brief.naver_rate_limit.sleep"):
        yield


def test_naver_emphasis_does_not_split_korean_keywords() -> None:
    xml = """<rss><channel><item>
    <title>한화&lt;b&gt;시스템&lt;/b&gt;, 국방부 무기체계 계약 체결</title>
    <originallink>https://publisher.example/contract</originallink>
    <link>https://news.naver.com/contract</link>
    <description>&lt;b&gt;국방&lt;/b&gt;부와 무기체계 계약을 체결했다.</description>
    <pubDate>Thu, 17 Sep 2026 05:00:00 +0900</pubDate>
    </item></channel></rss>"""
    articles = naver_news.parse_naver_items(
        xml,
        days=1,
        now=datetime(2026, 9, 17, tzinfo=UTC),
    )
    assert len(articles) == 1
    assert articles[0].title.startswith("한화시스템,")
    assert articles[0].description.startswith("국방부와")
