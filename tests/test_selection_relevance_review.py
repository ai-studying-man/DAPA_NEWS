from datetime import UTC, datetime

import pytest

from dapa_morning_brief.article_selection_review import review_selection
from dapa_morning_brief.briefing import build_briefing
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, Section


@pytest.mark.parametrize("provider", ["", "naver", "google"])
def test_foreign_internal_event_is_rejected_for_every_provider(provider: str) -> None:
    # Given: a generic defense minister title hides the foreign primary subject.
    article = Article(
        '[총살형 생중계] 국방장관 호언장담하더니…트럼프 "입장 변경"',
        "https://example.com/foreign",
        datetime(2026, 10, 14, tzinfo=UTC),
        "CBC뉴스",
        Section.GOVERNMENT,
        search_provider=provider,
    )
    # When
    result = review_selection(
        article,
        "미국 내 사형 생중계 논란에 미 국방장관이 입장을 밝혔다.",
    )
    # Then
    assert result.article is None
    assert result.status.value == "unrelated"


@pytest.mark.parametrize(
    ("title", "body"),
    [
        (
            "국방부, 미 국방장관 접견",
            "국방부는 미 국방장관과 군수 협력을 논의했다.",
        ),
        (
            "미 국방장관, 한국과 군수 협력 논의",
            "미 국방장관은 한국 국방부와 한미동맹 및 군수 협력을 논의했다.",
        ),
        (
            "미 육군, K9 자주포 시제품 사업 추진",
            "미 육군은 한화의 K9 자주포를 도입하는 사업을 추진했다.",
        ),
        (
            "Hanwha, U.S. Army name K9 howitzer XM1776",
            "The U.S. Army and Hanwha named the K9 howitzer prototype XM1776.",
        ),
        (
            "폴란드 정부, 한국 방산기업과 협력",
            "폴란드 정부는 현대로템과 전차 생산 협력을 논의했다.",
        ),
        (
            "국방부, 부사관 암 치료 지원금 전달",
            "국방부는 부사관 129명에게 암 치료 지원금을 전달했다.",
        ),
    ],
)
def test_defense_connection_is_preserved(title: str, body: str) -> None:
    # Given
    article = Article(
        title,
        "https://example.com/connected",
        datetime(2026, 10, 14, tzinfo=UTC),
        "뉴스",
        Section.GOVERNMENT,
        search_provider="naver",
    )
    # When
    result = review_selection(article, body)
    # Then
    assert result.article is not None


def test_uncertain_category_does_not_discard_article() -> None:
    # Given: a short report cannot resolve a category reliably.
    article = Article(
        "현장 점검 결과 공유",
        "https://example.com/uncertain",
        datetime(2026, 10, 14, tzinfo=UTC),
        "뉴스",
        Section.POLICY,
    )
    # When
    result = review_selection(article, "담당자들은 현장 점검 결과를 공유했다.")
    # Then
    assert result.article == article
    assert result.status.value == "category_uncertain"


def test_rejected_article_is_replaced_without_changing_section_limit() -> None:
    # Given
    foreign = Article(
        "국방장관, 총살형 생중계 논란",
        "https://example.com/foreign",
        datetime(2026, 10, 14, 1, tzinfo=UTC),
        "뉴스",
        Section.GOVERNMENT,
    )
    domestic = Article(
        "국방부, 부사관 암 치료 지원금 전달",
        "https://example.com/domestic",
        datetime(2026, 10, 14, tzinfo=UTC),
        "뉴스",
        Section.GOVERNMENT,
    )
    bodies = (
        ArticleBody(
            foreign.url,
            foreign.title,
            foreign.source,
            "미국 대통령과 미 국방장관이 사형 생중계 방안을 논의했다.",
        ),
        ArticleBody(
            domestic.url,
            domestic.title,
            domestic.source,
            "국방부는 부사관 암 치료비를 지원하는 전달식을 개최했다.",
        ),
    )
    # When
    result = build_briefing(
        (foreign, domestic),
        max_per_section=1,
        article_bodies=bodies,
    )
    # Then
    assert result.sections[Section.GOVERNMENT] == (domestic,)
