"""Serialize Naver search starts and stop a rate-limited collection burst."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from http import HTTPStatus
from threading import Lock
from time import monotonic, sleep
from typing import TYPE_CHECKING, Final, final

if TYPE_CHECKING:
    import httpx

_LOGGER = logging.getLogger(__name__)
_INTERVAL: Final = 1.0
_MAX_DELAY: Final = 30.0
_MAX_ATTEMPTS: Final = 3


@final
class NaverRequestGate:
    """Own mutable pacing state shared by all workers in one collection run."""

    def __init__(self) -> None:
        """Initialize per-run pacing and terminal rate-limit state."""
        self._lock = Lock()
        self._next_start: float = 0.0
        self._exhausted: httpx.Response | None = None

    def get(self, client: httpx.Client, url: str) -> httpx.Response:
        """Request with isolated credentials, bounded retries, and shared cooldown."""
        with self._lock:
            if self._exhausted is not None:
                return self._exhausted
            attempt = 0
            while True:
                delay = max(0.0, self._next_start - monotonic())
                if delay:
                    sleep(delay)
                self._next_start = monotonic() + _INTERVAL
                response = client.get(
                    url,
                    headers={
                        "X-Naver-Client-Id": os.environ["NAVER_CLIENT_ID"],
                        "X-Naver-Client-Secret": os.environ["NAVER_CLIENT_SECRET"],
                    },
                    follow_redirects=False,
                )
                if response.status_code != HTTPStatus.TOO_MANY_REQUESTS:
                    return response
                retry_after = dict(response.headers).get("retry-after")
                cooldown = retry_delay(retry_after, attempt, datetime.now(UTC))
                self._next_start = max(self._next_start, monotonic() + cooldown)
                _LOGGER.warning(
                    "naver_rate_limited attempt=%d cooldown_seconds=%.1f",
                    attempt + 1,
                    cooldown,
                )
                attempt += 1
                if attempt >= _MAX_ATTEMPTS:
                    self._exhausted = response
                    _LOGGER.warning(
                        "naver_rate_limit_exhausted remaining_queries_skipped=true"
                    )
                    return response


def retry_delay(value: str | None, attempt: int, now: datetime) -> float:
    """Parse seconds or HTTP-date into a bounded shared cooldown."""
    fallback = 2.0 * (attempt + 1)
    if value is None:
        return fallback
    try:
        seconds = float(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return fallback
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        seconds = (retry_at - now).total_seconds()
    return min(_MAX_DELAY, max(_INTERVAL, seconds))
