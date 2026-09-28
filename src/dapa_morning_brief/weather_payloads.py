"""Typed response boundaries for the existing weather providers."""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class _DailyForecastPayload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, allow_inf_nan=False)
    time: tuple[str, ...]
    weather_code: tuple[int | None, ...]
    temperature_2m_min: tuple[float | None, ...]
    temperature_2m_max: tuple[float | None, ...]


class ForecastPayload(BaseModel):
    """Open-Meteo daily arrays, parsed before selecting the requested day."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    daily: _DailyForecastPayload


class KmaForecastItem(BaseModel):
    """One KMA category value with its forecast date and time."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, populate_by_name=True)
    category: str
    forecast_date: str = Field(alias="fcstDate")
    forecast_time: str = Field(alias="fcstTime")
    forecast_value: str = Field(alias="fcstValue")


class _KmaForecastItems(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    item: tuple[KmaForecastItem, ...]


class _KmaForecastBody(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    items: _KmaForecastItems


class _KmaForecastResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    body: _KmaForecastBody


class KmaForecastPayload(BaseModel):
    """KMA proxy response containing forecast items."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    response: _KmaForecastResponse
