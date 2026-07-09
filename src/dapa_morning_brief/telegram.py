"""Telegram Bot API delivery helpers."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Final

import httpx
from typing_extensions import override

TELEGRAM_MESSAGE_LIMIT: Final = 4096
_TELEGRAM_ERROR_STATUS: Final = 400


@dataclass(frozen=True, slots=True)
class TelegramSendError(RuntimeError):
    """Telegram sendMessage failure."""

    status_code: int
    body: str

    @override
    def __str__(self) -> str:
        return f"Telegram send failed: HTTP {self.status_code} {self.body}"


def send_telegram_message(*, token: str, chat_id: str, text: str) -> None:
    """Send a plain text message through Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    message_texts = _message_chunks(text)
    timeout = httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=5.0)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for message_text in message_texts:
            payload = {
                "chat_id": chat_id,
                "text": message_text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            response = client.post(url, json=payload)
            if response.status_code >= _TELEGRAM_ERROR_STATUS:
                raise TelegramSendError(
                    status_code=response.status_code,
                    body=response.text,
                )


def parse_chat_ids(raw_chat_ids: str) -> tuple[str, ...]:
    """Parse comma-separated Telegram chat IDs."""
    return tuple(
        chat_id
        for chat_id in (part.strip() for part in raw_chat_ids.split(","))
        if chat_id
    )


def send_telegram_messages(
    *,
    token: str,
    chat_ids: tuple[str, ...],
    text: str,
) -> None:
    """Send the same message to one or more Telegram chats."""
    for chat_id in chat_ids:
        send_telegram_message(token=token, chat_id=chat_id, text=text)


def _message_chunks(text: str) -> tuple[str, ...]:
    if not text:
        return ("",)
    if _visible_length(text) <= TELEGRAM_MESSAGE_LIMIT:
        return (text,)

    chunks: list[str] = []
    current = ""
    for block in text.split("\n\n"):
        candidate = block if not current else f"{current}\n\n{block}"
        if _visible_length(candidate) <= TELEGRAM_MESSAGE_LIMIT:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if _visible_length(block) <= TELEGRAM_MESSAGE_LIMIT:
            current = block
            continue
        chunks.extend(_split_long_plain_block(block))
        current = ""
    if current:
        chunks.append(current)
    return tuple(chunks)


def _split_long_plain_block(text: str) -> tuple[str, ...]:
    return tuple(
        text[index : index + TELEGRAM_MESSAGE_LIMIT]
        for index in range(0, len(text), TELEGRAM_MESSAGE_LIMIT)
    )


def _visible_length(text: str) -> int:
    without_tags = re.sub(r"<[^>]+>", "", text)
    return len(html.unescape(without_tags))
