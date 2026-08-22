from __future__ import annotations

from datetime import date

import httpx

from dapa_morning_brief.models import WeatherForecast
from dapa_morning_brief.weather import collect_weather_forecasts


def test_collect_weather_forecasts_maps_daily_open_meteo_data() -> None:
    # Given
    def respond(request: httpx.Request) -> httpx.Response:
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
