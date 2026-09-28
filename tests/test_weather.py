from __future__ import annotations

from datetime import date

import httpx

from dapa_morning_brief.models import WeatherForecast
from dapa_morning_brief.weather import collect_weather_forecasts


def test_collect_weather_forecasts_maps_daily_open_meteo_data() -> None:
    # Given
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.host == "k-skill-proxy.nomadamas.org":
            return httpx.Response(503)
        assert "models" not in request.url.params
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
        if request.url.host == "k-skill-proxy.nomadamas.org":
            return httpx.Response(503)
        if request.url.params.get("latitude") == "36.3504":
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
    requested_sources: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.host == "k-skill-proxy.nomadamas.org":
            requested_sources.append("kma_api")
            return httpx.Response(
                200, json={"response": {"body": {"items": {"item": []}}}}
            )
        requested_sources.append("open_meteo_auto")
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
    assert requested_sources == [
        "kma_api",
        "open_meteo_auto",
        "kma_api",
        "open_meteo_auto",
    ]
    assert all(forecast.minimum_celsius == 21.4 for forecast in forecasts)


def test_collect_weather_forecasts_prefers_available_kma_daily_forecast() -> None:
    # Given
    requested_locations: list[tuple[str, str]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.host == "k-skill-proxy.nomadamas.org":
            requested_locations.append(
                (request.url.params["lat"], request.url.params["lon"]),
            )
            return httpx.Response(
                200,
                json={
                    "response": {
                        "body": {
                            "items": {
                                "item": [
                                    {
                                        "category": "TMP",
                                        "fcstDate": "20260822",
                                        "fcstTime": "0600",
                                        "fcstValue": "24",
                                    },
                                    {
                                        "category": "TMP",
                                        "fcstDate": "20260822",
                                        "fcstTime": "1500",
                                        "fcstValue": "33",
                                    },
                                    {
                                        "category": "SKY",
                                        "fcstDate": "20260822",
                                        "fcstTime": "0600",
                                        "fcstValue": "1",
                                    },
                                    {
                                        "category": "SKY",
                                        "fcstDate": "20260822",
                                        "fcstTime": "1500",
                                        "fcstValue": "4",
                                    },
                                    {
                                        "category": "PTY",
                                        "fcstDate": "20260822",
                                        "fcstTime": "0600",
                                        "fcstValue": "0",
                                    },
                                ],
                            },
                        },
                    },
                },
            )
        raise AssertionError

    # When
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        forecasts = collect_weather_forecasts(
            as_of=date(2026, 8, 22),
            client=client,
        )

    # Then
    assert requested_locations == [
        ("37.4292", "126.9876"),
        ("36.3504", "127.3845"),
    ]
    assert forecasts[0] == WeatherForecast(
        city="과천시",
        condition="흐림",
        minimum_celsius=24.0,
        maximum_celsius=33.0,
    )
