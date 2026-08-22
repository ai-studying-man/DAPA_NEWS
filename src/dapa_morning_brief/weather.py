"""Collect daily weather forecasts for the DAPA morning briefing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Final

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from dapa_morning_brief.models import WeatherForecast

if TYPE_CHECKING:
    from datetime import date

OPEN_METEO_FORECAST_URL: Final = "https://api.open-meteo.com/v1/forecast"
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


class _DailyForecastPayload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    time: tuple[str, ...]
    weather_code: tuple[int, ...]
    temperature_2m_min: tuple[float, ...]
    temperature_2m_max: tuple[float, ...]


class _ForecastPayload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    daily: _DailyForecastPayload


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
        try:
            response = client.get(
                OPEN_METEO_FORECAST_URL,
                params={
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "daily": "weather_code,temperature_2m_min,temperature_2m_max",
                    "timezone": KST_TIMEZONE,
                    "start_date": as_of.isoformat(),
                    "end_date": as_of.isoformat(),
                },
            )
            _ = response.raise_for_status()
            payload = _ForecastPayload.model_validate_json(response.content)
            day_index = payload.daily.time.index(as_of.isoformat())
            forecasts.append(
                WeatherForecast(
                    city=location.city,
                    condition=_weather_condition(payload.daily.weather_code[day_index]),
                    minimum_celsius=payload.daily.temperature_2m_min[day_index],
                    maximum_celsius=payload.daily.temperature_2m_max[day_index],
                ),
            )
        except (httpx.HTTPError, ValidationError, ValueError):
            forecasts.append(
                WeatherForecast(
                    city=location.city,
                    condition="수집 실패",
                    minimum_celsius=None,
                    maximum_celsius=None,
                ),
            )
    return tuple(forecasts)


WEATHER_CONDITIONS: Final[dict[int, str]] = {
    0: "맑음",
    1: "구름 조금",
    2: "구름 조금",
    3: "흐림",
    45: "안개",
    48: "안개",
    51: "이슬비",
    53: "이슬비",
    55: "이슬비",
    56: "이슬비",
    57: "이슬비",
    61: "비",
    63: "비",
    65: "비",
    66: "비",
    67: "비",
    71: "눈",
    73: "눈",
    75: "눈",
    77: "눈",
    80: "비",
    81: "비",
    82: "비",
    85: "눈",
    86: "눈",
    95: "뇌우",
    96: "뇌우",
    99: "뇌우",
}


def _weather_condition(weather_code: int) -> str:
    return WEATHER_CONDITIONS.get(weather_code, "기타")
