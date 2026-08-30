from __future__ import annotations

import json
import subprocess
from io import StringIO
from unittest.mock import patch

from dapa_morning_brief.copilot_summary import (
    ArticleBody,
    parse_copilot_output,
    summarize_article_bodies,
)


def test_parse_copilot_output_returns_typed_practice_points() -> None:
    # Given
    raw_output = (
        '[{"article_url":"https://example.com/a",'
        '"text":"계약 일정과 후속 조달·납품 영향을 확인해야 함"}]'
    )

    # When
    points = parse_copilot_output(raw_output)

    # Then
    assert len(points) == 1
    assert points[0].article_url == "https://example.com/a"
    assert points[0].text == "계약 일정과 후속 조달·납품 영향 확인"


def test_parse_copilot_output_rejects_practice_point_shorter_than_20_chars() -> None:
    # Given
    raw_output = json.dumps(
        [{"article_url": "https://example.com/a", "text": f"{'가' * 17}확인"}],
        ensure_ascii=False,
    )

    # When
    points = parse_copilot_output(raw_output)

    # Then
    assert points == ()


def test_parse_copilot_output_rejects_practice_point_longer_than_30_chars() -> None:
    # Given
    raw_output = json.dumps(
        [{"article_url": "https://example.com/a", "text": f"{'가' * 29}확인"}],
        ensure_ascii=False,
    )

    # When
    points = parse_copilot_output(raw_output)

    # Then
    assert points == ()


def test_parse_copilot_output_rejects_invalid_json() -> None:
    # Given
    invalid_output = "요약 결과를 생성하지 못했습니다."

    # When
    points = parse_copilot_output(invalid_output)

    # Then
    assert points == ()


def test_parse_copilot_output_accepts_json_code_fence() -> None:
    # Given
    raw_output = (
        "```json\n"
        '[{"article_url":"https://example.com/a",'
        '"text":"후속 양산 계약 시점 및 납품 일정 확인"}]\n'
        "```"
    )

    # When
    points = parse_copilot_output(raw_output)

    # Then
    assert len(points) == 1


def test_parse_copilot_output_retains_valid_items_when_one_is_invalid() -> None:
    # Given
    raw_output = json.dumps(
        [
            {
                "article_url": "https://example.com/valid",
                "text": "후속 양산 계약 시점 및 납품 일정 확인",
            },
            {
                "article_url": "https://example.com/invalid",
                "text": "너무 짧음",
            },
        ],
        ensure_ascii=False,
    )

    # When
    points = parse_copilot_output(raw_output)

    # Then
    assert len(points) == 1
    assert points[0].article_url == "https://example.com/valid"


def test_parse_copilot_output_extracts_array_from_explanatory_text() -> None:
    # Given
    raw_output = (
        "요청한 JSON입니다.\n"
        '[{"article_url":"https://example.com/a",'
        '"text":"후속 양산 계약 시점 및 납품 일정 확인"}]\n'
        "이상입니다."
    )

    # When
    points = parse_copilot_output(raw_output)

    # Then
    assert len(points) == 1


def test_summarize_article_bodies_falls_back_when_copilot_limit_is_exceeded() -> None:
    # Given
    article = ArticleBody(
        article_url="https://example.com/a",
        title="방산 계약 일정 발표",
        source="테스트뉴스",
        body="방산 계약 체결 시점과 납품 일정이 발표됐다.",
    )

    quota_exceeded = subprocess.CompletedProcess(
        args=("copilot",),
        returncode=1,
        stdout="",
        stderr="AI credit limit exceeded",
    )

    # When
    diagnostic_output = StringIO()
    with (
        patch(
            "dapa_morning_brief.copilot_summary.shutil.which",
            return_value="copilot",
        ),
        patch(
            "dapa_morning_brief.copilot_summary.subprocess.run",
            return_value=quota_exceeded,
        ),
        patch("sys.stderr", diagnostic_output),
    ):
        points = summarize_article_bodies((article,))

    # Then
    assert points == ()
    assert "exit_code=1" in diagnostic_output.getvalue()
    assert "AI credit limit exceeded" in diagnostic_output.getvalue()


def test_summarize_article_bodies_rejects_unknown_article_url() -> None:
    # Given
    article = ArticleBody(
        article_url="https://example.com/known",
        title="방산 계약 일정 발표",
        source="테스트뉴스",
        body="방산 계약 체결 시점과 납품 일정이 발표됐다.",
    )
    response = subprocess.CompletedProcess(
        args=("copilot",),
        returncode=0,
        stdout=(
            '[{"article_url":"https://example.com/unknown",'
            '"text":"알 수 없는 계약 일정 및 후속 조달 영향 확인"}]'
        ),
        stderr="",
    )

    # When
    diagnostic_output = StringIO()
    with (
        patch(
            "dapa_morning_brief.copilot_summary.shutil.which",
            return_value="copilot",
        ),
        patch(
            "dapa_morning_brief.copilot_summary.subprocess.run",
            return_value=response,
        ),
        patch("sys.stderr", diagnostic_output),
    ):
        points = summarize_article_bodies((article,))

    # Then
    assert points == ()
    assert "unknown_urls=1" in diagnostic_output.getvalue()
