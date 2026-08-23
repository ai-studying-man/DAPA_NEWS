from __future__ import annotations

from datetime import date

import httpx

from dapa_morning_brief.models import WeatherForecast
from dapa_morning_brief.weather import collect_weather_forecasts


def test_collect_weather_forecasts_maps_daily_open_meteo_data() -> None:
    # Given
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.params["models"] == "kma_seamless"
        weather_code = 0 if request.url.params["latitude"] == "37.4292" else 3
        return httpx.Response(
            200,
            json={
                "daily": {
                    "time": ["2026-08-22"],
                    "weather_code": [weather_code],
                    "temperature_2m_min": [21.4],
                    "temperature_2m_max": [31.8],
                },
            },
        )

    # When
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        forecasts = collect_weather_forecasts(
            as_of=date(2026, 8, 22),
            client=client,
        )

    # Then
    assert forecasts == (
        WeatherForecast(
            city="과천시",
            condition="맑음",
            minimum_celsius=21.4,
            maximum_celsius=31.8,
        ),
        WeatherForecast(
            city="대전시",
            condition="흐림",
            minimum_celsius=21.4,
            maximum_celsius=31.8,
        ),
    )


def test_collect_weather_forecasts_keeps_failed_location_visible() -> None:
    # Given
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.params["latitude"] == "36.3504":
            return httpx.Response(503)
        return httpx.Response(
            200,
            json={
                "daily": {
                    "time": ["2026-08-22"],
                    "weather_code": [0],
                    "temperature_2m_min": [21.4],
                    "temperature_2m_max": [31.8],
                },
            },
        )

    # When
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        forecasts = collect_weather_forecasts(
            as_of=date(2026, 8, 22),
            client=client,
        )

    # Then
    assert forecasts[0].condition == "맑음"
    assert forecasts[1] == WeatherForecast(
        city="대전시",
        condition="수집 실패",
        minimum_celsius=None,
        maximum_celsius=None,
    )


def test_collect_weather_forecasts_falls_back_when_kma_values_are_missing() -> None:
    # Given
    requested_models: list[str | None] = []

    def respond(request: httpx.Request) -> httpx.Response:
        if "models" in request.url.params:
            assert request.url.params["models"] == "kma_seamless"
            requested_models.append("kma_seamless")
            weather_codes: list[int | None] = [None]
            minimums: list[float | None] = [None]
            maximums: list[float | None] = [None]
        else:
            requested_models.append(None)
            weather_codes = [0]
            minimums = [21.4]
            maximums = [31.8]
        return httpx.Response(
            200,
            json={
                "daily": {
                    "time": ["2026-08-22"],
                    "weather_code": weather_codes,
                    "temperature_2m_min": minimums,
                    "temperature_2m_max": maximums,
                },
            },
        )

    # When
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        forecasts = collect_weather_forecasts(
            as_of=date(2026, 8, 22),
            client=client,
        )

    # Then
    assert requested_models == ["kma_seamless", None, "kma_seamless", None]
    assert all(forecast.minimum_celsius == 21.4 for forecast in forecasts)
