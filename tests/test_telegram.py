from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, TypedDict
from unittest import TestCase
from unittest.mock import patch

from dapa_morning_brief.telegram import (
    TELEGRAM_MESSAGE_LIMIT,
    parse_chat_ids,
    send_telegram_messages,
)

if TYPE_CHECKING:
    from types import TracebackType

    import httpx

TEST_TELEGRAM_TOKEN = "test-token"  # noqa: S105


class TelegramPayload(TypedDict):
    chat_id: str
    text: str
    disable_web_page_preview: bool
    parse_mode: str


@dataclass(frozen=True, slots=True)
class TelegramResponse:
    status_code: int
    text: str


class TelegramTest(TestCase):
    def test_parse_chat_ids_accepts_multiple_comma_separated_targets(self) -> None:
        # Given
        raw_chat_ids = "6015255978, -1004402722342"

        # When
        chat_ids = parse_chat_ids(raw_chat_ids)

        # Then
        assert chat_ids == ("6015255978", "-1004402722342")

    def test_parse_chat_ids_ignores_empty_parts(self) -> None:
        # Given
        raw_chat_ids = " 6015255978, , -1004402722342, "

        # When
        chat_ids = parse_chat_ids(raw_chat_ids)

        # Then
        assert chat_ids == ("6015255978", "-1004402722342")

    def test_send_telegram_messages_chunks_long_text_for_each_chat(self) -> None:
        # Given
        sent_payloads: list[TelegramPayload] = []

        class FakeClient:
            def __init__(
                self,
                *,
                timeout: httpx.Timeout,
                follow_redirects: bool,
            ) -> None:
                self.timeout: httpx.Timeout = timeout
                self.follow_redirects: bool = follow_redirects

            def __enter__(self) -> Self:
                return self

            def __exit__(
                self,
                exc_type: type[BaseException] | None,
                exc: BaseException | None,
                traceback: TracebackType | None,
            ) -> None:
                return None

            def post(self, _url: str, *, json: TelegramPayload) -> TelegramResponse:
                sent_payloads.append(json.copy())
                return TelegramResponse(status_code=200, text="")

        text = f"{'x' * TELEGRAM_MESSAGE_LIMIT}y"

        # When
        with patch("dapa_morning_brief.telegram.httpx.Client", FakeClient):
            send_telegram_messages(
                token=TEST_TELEGRAM_TOKEN,
                chat_ids=("chat-1", "chat-2"),
                text=text,
            )

        # Then
        assert [payload["chat_id"] for payload in sent_payloads] == [
            "chat-1",
            "chat-1",
            "chat-2",
            "chat-2",
        ]
        assert all(
            len(payload["text"]) <= TELEGRAM_MESSAGE_LIMIT
            for payload in sent_payloads
        )
        assert "".join(payload["text"] for payload in sent_payloads[:2]) == text
        assert "".join(payload["text"] for payload in sent_payloads[2:]) == text
        assert all(payload["parse_mode"] == "HTML" for payload in sent_payloads)

    def test_send_telegram_messages_keeps_html_link_together_when_visible_text_fits(
        self,
    ) -> None:
        # Given
        sent_payloads: list[TelegramPayload] = []

        class FakeClient:
            def __init__(
                self,
                *,
                timeout: httpx.Timeout,
                follow_redirects: bool,
            ) -> None:
                self.timeout: httpx.Timeout = timeout
                self.follow_redirects: bool = follow_redirects

            def __enter__(self) -> Self:
                return self

            def __exit__(
                self,
                exc_type: type[BaseException] | None,
                exc: BaseException | None,
                traceback: TracebackType | None,
            ) -> None:
                return None

            def post(self, _url: str, *, json: TelegramPayload) -> TelegramResponse:
                sent_payloads.append(json.copy())
                return TelegramResponse(status_code=200, text="")

        long_url = f"https://example.com/{'x' * TELEGRAM_MESSAGE_LIMIT}"
        text = f'기사\n🔗 <a href="{long_url}">뉴스 기사 링크 바로가기</a>'

        # When
        with patch("dapa_morning_brief.telegram.httpx.Client", FakeClient):
            send_telegram_messages(
                token=TEST_TELEGRAM_TOKEN,
                chat_ids=("chat-1",),
                text=text,
            )

        # Then
        assert [payload["text"] for payload in sent_payloads] == [text]
