"""Collect daily weather forecasts for the DAPA morning briefing."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING, Final

import httpx

from dapa_morning_brief.models import WeatherForecast
from dapa_morning_brief.weather_payloads import (
    ForecastPayload,
    KmaForecastItem,
    KmaForecastPayload,
)

if TYPE_CHECKING:
    from datetime import date

OPEN_METEO_FORECAST_URL: Final = "https://api.open-meteo.com/v1/forecast"
MAX_WEATHER_ATTEMPTS: Final = 3
MAX_RETRY_DELAY: Final = 5
_LOGGER = logging.getLogger(__name__)
KMA_PROXY_BASE_URL: Final = (
    os.environ.get("KSKILL_PROXY_BASE_URL") or "https://k-skill-proxy.nomadamas.org"
).rstrip("/")
KMA_FORECAST_URL: Final = f"{KMA_PROXY_BASE_URL}/v1/korea-weather/forecast"
KST_TIMEZONE: Final = "Asia/Seoul"


@dataclass(frozen=True, slots=True)
class WeatherLocation:
    """Fixed location used for the morning weather summary."""

    city: str
    latitude: float
    longitude: float


WEATHER_LOCATIONS: Final[tuple[WeatherLocation, ...]] = (
    WeatherLocation(city="과천시", latitude=37.4292, longitude=126.9876),
    WeatherLocation(city="대전시", latitude=36.3504, longitude=127.3845),
)


def collect_weather_forecasts(
    *,
    as_of: date,
    client: httpx.Client | None = None,
) -> tuple[WeatherForecast, ...]:
    """Collect one local-time daily forecast for every configured city."""
    if client is None:
        with httpx.Client(timeout=10.0, follow_redirects=True) as owned_client:
            return _collect_with_client(as_of=as_of, client=owned_client)
    return _collect_with_client(as_of=as_of, client=client)


def _collect_with_client(
    *,
    as_of: date,
    client: httpx.Client,
) -> tuple[WeatherForecast, ...]:
    forecasts: list[WeatherForecast] = []
    for location in WEATHER_LOCATIONS:
        forecast: WeatherForecast | None = None
        try:
            forecast = _collect_kma_forecast(
                as_of=as_of, client=client, location=location
            )
        except (httpx.HTTPError, ValueError) as error:
            _log_failure(location.city, "kma_proxy", error)
        if forecast is None:
            _LOGGER.warning(
                "weather_fallback city=%s provider=open_meteo_auto", location.city
            )
            forecast = _collect_open_meteo(as_of, client, location)
        if forecast is None:
            _LOGGER.error("weather_unavailable city=%s", location.city)
        forecasts.append(
            forecast
            if forecast is not None
            else WeatherForecast(
                city=location.city,
                condition="수집 실패",
                minimum_celsius=None,
                maximum_celsius=None,
            ),
        )
    return tuple(forecasts)


def _log_failure(city: str, provider: str, error: httpx.HTTPError | ValueError) -> None:
    match error:
        case httpx.HTTPStatusError(response=response):
            status = response.status_code
        case httpx.HTTPError() | ValueError():
            status = 0
    _LOGGER.warning(
        "weather_request_failed city=%s provider=%s status=%s reason=%s",
        city,
        provider,
        status,
        type(error).__name__,
    )


def _collect_open_meteo(
    as_of: date,
    client: httpx.Client,
    location: WeatherLocation,
) -> WeatherForecast | None:
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "daily": "weather_code,temperature_2m_min,temperature_2m_max",
        "timezone": KST_TIMEZONE,
        "start_date": as_of.isoformat(),
        "end_date": as_of.isoformat(),
    }
    for attempt in range(1, MAX_WEATHER_ATTEMPTS + 1):
        delay = attempt
        try:
            response = client.get(OPEN_METEO_FORECAST_URL, params=params)
            _ = response.raise_for_status()
            daily = ForecastPayload.model_validate_json(response.content).daily
            rows = tuple(
                zip(
                    daily.time,
                    daily.weather_code,
                    daily.temperature_2m_min,
                    daily.temperature_2m_max,
                    strict=True,
                )
            )
            for day, code, minimum, maximum in rows:
                if (
                    day == as_of.isoformat()
                    and code is not None
                    and minimum is not None
                    and maximum is not None
                ):
                    return WeatherForecast(
                        city=location.city,
                        condition=_weather_condition(code),
                        minimum_celsius=minimum,
                        maximum_celsius=maximum,
                    )
            _LOGGER.warning(
                "weather_missing_day city=%s provider=open_meteo_auto", location.city
            )
            break
        except httpx.HTTPStatusError as error:
            _log_failure(location.city, "open_meteo_auto", error)
            if (
                error.response.status_code != HTTPStatus.TOO_MANY_REQUESTS
                and error.response.status_code < HTTPStatus.INTERNAL_SERVER_ERROR
            ):
                break
            retry_after = (
                error.response.headers["Retry-After"]
                if "Retry-After" in error.response.headers
                else str(attempt)
            )
            delay = int(retry_after) if retry_after.isdigit() else MAX_RETRY_DELAY + 1
            if delay > MAX_RETRY_DELAY:
                break
        except httpx.HTTPError as error:
            _log_failure(location.city, "open_meteo_auto", error)
        except ValueError as error:
            _log_failure(location.city, "open_meteo_auto", error)
            break
        if attempt < MAX_WEATHER_ATTEMPTS:
            _LOGGER.warning(
                "weather_retry city=%s attempt=%s delay=%s",
                location.city,
                attempt + 1,
                delay,
            )
            time.sleep(delay)
    return None


def _collect_kma_forecast(
    *,
    as_of: date,
    client: httpx.Client,
    location: WeatherLocation,
) -> WeatherForecast | None:
    response = client.get(
        KMA_FORECAST_URL,
        params={
            "lat": location.latitude,
            "lon": location.longitude,
        },
    )
    _ = response.raise_for_status()
    payload = KmaForecastPayload.model_validate_json(response.content)
    target_date = as_of.strftime("%Y%m%d")
    items = tuple(
        item
        for item in payload.response.body.items.item
        if item.forecast_date == target_date
    )
    hourly_temperatures = [
        float(item.forecast_value) for item in items if item.category == "TMP"
    ]
    if not hourly_temperatures:
        return None
    minimum_temperatures = [
        float(item.forecast_value) for item in items if item.category == "TMN"
    ]
    maximum_temperatures = [
        float(item.forecast_value) for item in items if item.category == "TMX"
    ]
    return WeatherForecast(
        city=location.city,
        condition=_kma_weather_condition(items),
        minimum_celsius=min(minimum_temperatures or hourly_temperatures),
        maximum_celsius=max(maximum_temperatures or hourly_temperatures),
    )


KMA_PRECIPITATION_CONDITIONS: Final[dict[int, str]] = {
    1: "비",
    2: "비/눈",
    3: "눈",
    4: "소나기",
}
KMA_SKY_CONDITIONS: Final[dict[int, str]] = {
    1: "맑음",
    3: "구름 많음",
    4: "흐림",
}


def _kma_weather_condition(items: tuple[KmaForecastItem, ...]) -> str:
    precipitation_codes = {
        int(item.forecast_value) for item in items if item.category == "PTY"
    }
    for code in (4, 3, 2, 1):
        if code in precipitation_codes:
            return KMA_PRECIPITATION_CONDITIONS[code]
    sky_codes = {int(item.forecast_value) for item in items if item.category == "SKY"}
    return KMA_SKY_CONDITIONS.get(max(sky_codes, default=1), "맑음")


WEATHER_CONDITIONS: Final[dict[int, str]] = {
    0: "맑음",
    **dict.fromkeys((1, 2), "구름 조금"),
    3: "흐림",
    **dict.fromkeys((45, 48), "안개"),
    **dict.fromkeys((51, 53, 55, 56, 57), "이슬비"),
    **dict.fromkeys((61, 63, 65, 66, 67, 80, 81, 82), "비"),
    **dict.fromkeys((71, 73, 75, 77, 85, 86), "눈"),
    **dict.fromkeys((95, 96, 99), "뇌우"),
}


def _weather_condition(weather_code: int) -> str:
    return WEATHER_CONDITIONS.get(weather_code, "기타")
