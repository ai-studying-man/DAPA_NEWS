"""Persist the latest validated official press releases."""

from __future__ import annotations

from datetime import date  # noqa: TC003 - Pydantic resolves this field at runtime.
from typing import TYPE_CHECKING, Final

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from dapa_morning_brief.models import OfficialPressRelease

if TYPE_CHECKING:
    from pathlib import Path
    from typing import ClassVar


class _CachedPressRelease(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    agency: str
    title: str
    url: str
    published_on: date


_PRESS_RELEASE_CACHE: Final = TypeAdapter(tuple[_CachedPressRelease, ...])


def load_cached_press_releases(
    cache_path: Path,
) -> tuple[OfficialPressRelease, ...]:
    """Load valid cached releases or return no fallback entries."""
    try:
        payload = cache_path.read_bytes()
    except FileNotFoundError:
        return ()
    try:
        cached = _PRESS_RELEASE_CACHE.validate_json(payload)
    except ValidationError:
        return ()
    return tuple(
        OfficialPressRelease(
            agency=release.agency,
            title=release.title,
            url=release.url,
            published_on=release.published_on,
        )
        for release in cached
    )


def save_cached_press_releases(
    cache_path: Path,
    releases: tuple[OfficialPressRelease, ...],
) -> None:
    """Persist releases for fallback use by later scheduled runs."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cached = tuple(
        _CachedPressRelease(
            agency=release.agency,
            title=release.title,
            url=release.url,
            published_on=release.published_on,
        )
        for release in releases
    )
    _ = cache_path.write_bytes(_PRESS_RELEASE_CACHE.dump_json(cached))
