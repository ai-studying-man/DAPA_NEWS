from datetime import date

import httpx
import pytest

from dapa_morning_brief.weather import collect_weather_forecasts


@pytest.mark.parametrize("failure", ["timeout", "503", "429"])
def test_daejeon_recovers_from_transient_fallback_failure(failure: str) -> None:
    # Given: KMA is unavailable and the first Daejeon fallback request fails.
    attempts = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        if request.url.host == "k-skill-proxy.nomadamas.org":
            return httpx.Response(500)
        if "models" in request.url.params:
            return httpx.Response(
                200,
                json={
                    "daily": {
                        "time": ["2026-09-29"],
                        "weather_code": [None],
                        "temperature_2m_min": [None],
                        "temperature_2m_max": [None],
                    }
                },
            )
        if request.url.params["latitude"] == "36.3504":
            attempts += 1
            if attempts == 1:
                if failure == "timeout":
                    message = "temporary failure"
                    raise httpx.ReadTimeout(message, request=request)
                return httpx.Response(int(failure), headers={"Retry-After": "0"})
        return httpx.Response(
            200,
            json={
                "daily": {
                    "time": ["2026-09-29"],
                    "weather_code": [2],
                    "temperature_2m_min": [13.9],
                    "temperature_2m_max": [25.4],
                }
            },
        )

    # When
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        forecasts = collect_weather_forecasts(as_of=date(2026, 9, 29), client=client)
    # Then
    assert forecasts[1].minimum_celsius == 13.9
    assert forecasts[1].maximum_celsius == 25.4
    assert attempts == 2


def test_suspended_kma_model_is_not_requested() -> None:
    # Given
    providers: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        providers.append(request.url.host)
        assert "models" not in request.url.params
        if request.url.host == "k-skill-proxy.nomadamas.org":
            return httpx.Response(500)
        return httpx.Response(
            200,
            json={
                "daily": {
                    "time": ["2026-09-29"],
                    "weather_code": [0],
                    "temperature_2m_min": [12.2],
                    "temperature_2m_max": [24.1],
                }
            },
        )

    # When
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        forecasts = collect_weather_forecasts(as_of=date(2026, 9, 29), client=client)
    # Then
    assert len(forecasts) == 2
    assert providers == ["k-skill-proxy.nomadamas.org", "api.open-meteo.com"] * 2


def test_weather_failure_logs_city_provider_and_status(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, request=request)

    # When
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        forecasts = collect_weather_forecasts(as_of=date(2026, 9, 29), client=client)
    # Then
    assert forecasts[1].condition == "수집 실패"
    assert "city=대전시" in caplog.text
    assert "provider=open_meteo_auto" in caplog.text
    assert "status=400" in caplog.text


def test_mismatched_daily_arrays_fail_gracefully() -> None:
    # Given
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.host == "k-skill-proxy.nomadamas.org":
            return httpx.Response(500)
        return httpx.Response(
            200,
            json={
                "daily": {
                    "time": ["2026-09-29"],
                    "weather_code": [],
                    "temperature_2m_min": [13.9],
                    "temperature_2m_max": [25.4],
                }
            },
        )

    # When
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        forecasts = collect_weather_forecasts(as_of=date(2026, 9, 29), client=client)
    # Then
    assert all(forecast.condition == "수집 실패" for forecast in forecasts)


@pytest.mark.parametrize(
    ("status", "retry_after", "expected_attempts"),
    [(503, "0", 3), (400, "0", 1), (429, "60", 1)],
)
def test_weather_retries_are_bounded(
    status: int, retry_after: str, expected_attempts: int
) -> None:
    # Given
    attempts: dict[str, int] = {}

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.host == "k-skill-proxy.nomadamas.org":
            return httpx.Response(500)
        latitude = request.url.params["latitude"]
        attempts[latitude] = attempts.get(latitude, 0) + 1
        return httpx.Response(status, headers={"Retry-After": retry_after})

    # When
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        forecasts = collect_weather_forecasts(as_of=date(2026, 9, 29), client=client)
    # Then
    assert attempts == {"37.4292": expected_attempts, "36.3504": expected_attempts}
    assert all(forecast.condition == "수집 실패" for forecast in forecasts)
