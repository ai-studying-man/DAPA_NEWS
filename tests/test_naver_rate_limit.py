from datetime import UTC, datetime
from unittest.mock import patch

import httpx

from dapa_morning_brief import naver_rate_limit
from dapa_morning_brief.naver_rate_limit import retry_delay


def test_retry_after_paces_retry_and_following_query() -> None:
    # Given
    elapsed = [0.0]
    starts: list[float] = []

    def sleep(seconds: float) -> None:
        elapsed[0] += seconds

    def respond(_: httpx.Request) -> httpx.Response:
        starts.append(elapsed[0])
        if len(starts) == 1:
            return httpx.Response(429, headers={"Retry-After": "3"})
        return httpx.Response(200)

    with (
        httpx.Client(transport=httpx.MockTransport(respond)) as client,
        patch(
            "dapa_morning_brief.naver_rate_limit.monotonic",
            side_effect=lambda: elapsed[0],
        ),
        patch("dapa_morning_brief.naver_rate_limit.sleep", side_effect=sleep),
        patch.dict(
            "os.environ", {"NAVER_CLIENT_ID": "id", "NAVER_CLIENT_SECRET": "secret"}
        ),
    ):
        gate = naver_rate_limit.NaverRequestGate()
        # When
        result = gate.get(client, "https://openapi.naver.com/v1/search/news.xml")
        _ = gate.get(client, "https://openapi.naver.com/v1/search/news.xml")
    # Then
    assert result.status_code == 200
    assert starts == [0.0, 3.0, 4.0]


def test_persistent_rate_limit_has_bounded_attempts_and_delay() -> None:
    # Given
    elapsed = [0.0]
    starts: list[float] = []

    def sleep(seconds: float) -> None:
        elapsed[0] += seconds

    def respond(_: httpx.Request) -> httpx.Response:
        starts.append(elapsed[0])
        return httpx.Response(429, headers={"Retry-After": "999999"})

    with (
        httpx.Client(transport=httpx.MockTransport(respond)) as client,
        patch(
            "dapa_morning_brief.naver_rate_limit.monotonic",
            side_effect=lambda: elapsed[0],
        ),
        patch("dapa_morning_brief.naver_rate_limit.sleep", side_effect=sleep),
        patch.dict(
            "os.environ", {"NAVER_CLIENT_ID": "id", "NAVER_CLIENT_SECRET": "secret"}
        ),
    ):
        # When
        result = naver_rate_limit.NaverRequestGate().get(
            client, "https://openapi.naver.com/v1/search/news.xml"
        )
    # Then
    assert result.status_code == 429
    assert starts == [0.0, 30.0, 60.0]


def test_exhausted_gate_skips_remaining_queries() -> None:
    # Given
    calls: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(429)

    with (
        httpx.Client(transport=httpx.MockTransport(respond)) as client,
        patch("dapa_morning_brief.naver_rate_limit.sleep"),
        patch.dict(
            "os.environ", {"NAVER_CLIENT_ID": "id", "NAVER_CLIENT_SECRET": "secret"}
        ),
    ):
        gate = naver_rate_limit.NaverRequestGate()
        # When
        for query in range(10):
            _ = gate.get(
                client, f"https://openapi.naver.com/v1/search/news.xml?q={query}"
            )
    # Then
    assert len(calls) == 3


def test_invalid_retry_after_uses_bounded_fallback() -> None:
    # Given / When
    delay = retry_delay("invalid", 1, datetime(2026, 9, 17, tzinfo=UTC))
    # Then
    assert delay == 4.0


def test_http_date_retry_after_is_respected() -> None:
    # Given

    now = datetime(2026, 9, 17, tzinfo=UTC)
    # When
    delay = retry_delay("Thu, 17 Sep 2026 00:00:10 GMT", 0, now)
    # Then
    assert delay == 10.0
