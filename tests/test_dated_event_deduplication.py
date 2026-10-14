from datetime import UTC, date, datetime

import pytest

from dapa_morning_brief.article_history import ArticleHistory
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.dated_agreement_evidence import (
    agreement_evidence,
    same_agreement,
)
from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.story_deduplication import are_same_articles


def item(title: str, suffix: str) -> Article:
    return Article(
        title=title,
        url=f"https://example.com/{suffix}",
        published_at=datetime(2026, 10, 14, tzinfo=UTC),
        source="test",
        section=Section.EXPORT_BUSINESS,
    )


LEFT = (
    "LIG D&A는 지난 13일 워싱턴 AUSA에서 파이어호크와 비궁 추진체 기술협약을 체결했다. "
)
RIGHT = (
    "미국 워싱턴 AUSA 현장에서 지난 13일 파이어호크와 LIG D&A가 "
    "비궁 추진체 개발 협약을 맺었다. "
)


def test_rewritten_dated_agreement_when_bodies_have_different_background() -> None:
    # Given
    left, right = (
        item("LIG D&A 비궁 미국 시장 뚫을까", "a"),
        item("비궁 로켓 현지 개발 협력", "b"),
    )
    # When
    result = are_same_articles(
        left,
        right,
        left_body=LEFT + "미국 시장 진출 가능성을 설명했다. " * 15,
        right_body=RIGHT + "첨단 제조 공정과 비용 경쟁력을 확보한다. " * 15,
    )
    # Then
    assert result is True


def test_history_when_rewritten_dated_agreement_was_collected_six_days_ago() -> None:
    # Given
    left, right = (
        item("성남시 폴란드 방산 협력 강화", "a"),
        item("성남 방산 수출 교두보 마련", "b"),
    )
    first = (
        "성남시는 지난 8일 브로츠와프에서 폴란드 방산협회와 "
        "사격훈련 시스템 업무협약을 체결했다."
    )
    second = (
        "지난 8일 성남시와 폴란드 방산협회는 브로츠와프 현장에서 "
        "사격훈련 시스템 협약을 맺었다."
    )
    history = ArticleHistory().record(
        [left],
        today=date(2026, 10, 9),
        bodies=(ArticleBody(left.url, left.title, left.source, first),),
    )
    # When
    selected = history.exclude_recent(
        [right],
        today=date(2026, 10, 15),
        bodies=(ArticleBody(right.url, right.title, right.source, second),),
    )
    # Then
    assert selected == ()


@pytest.mark.parametrize(
    "title",
    [
        "비궁 신규 공급 계약 체결",
        "비궁 첫 납품",
        "비궁 시험 성공",
        "비궁 수출 승인",
        "비궁 협약 종합 분석",
        "비궁 협력과 위성시설 완공",
    ],
)
def test_new_milestone_or_independent_analysis_is_not_agreement_repeat(
    title: str,
) -> None:
    # Given
    published = datetime(2026, 10, 14, tzinfo=UTC)
    # When
    result = agreement_evidence(title, LEFT, published)
    # Then
    assert result is None


def test_different_occurrence_dates_preserve_same_weapon_agreements() -> None:
    # Given
    published = datetime(2026, 10, 15, tzinfo=UTC)
    first = agreement_evidence("비궁 협력", LEFT, published)
    second = agreement_evidence("비궁 협력", RIGHT.replace("13일", "14일"), published)
    # When
    result = same_agreement(first, second)
    # Then
    assert result is False


@pytest.mark.parametrize(
    "changed",
    [
        RIGHT.replace("파이어호크", "록히드마틴"),
        RIGHT.replace("비궁", "천궁"),
        RIGHT + " 비궁 공급 계약을 체결했다.",
    ],
)
def test_distinct_partner_product_or_new_lead_milestone_survives(changed: str) -> None:
    # Given
    published = datetime(2026, 10, 14, tzinfo=UTC)
    first = agreement_evidence("방산 현지화 협력", LEFT, published)
    second = agreement_evidence("방산 현지화 협력", changed, published)
    # When
    result = same_agreement(first, second)
    # Then
    assert result is False


def test_date_directly_adjacent_to_agreement_parses_without_iteration_failure() -> None:
    # Given
    published = datetime(2026, 10, 14, tzinfo=UTC)
    # When
    result = agreement_evidence(
        "방산 협약", "지난 13일협약 체결을 발표했다.", published
    )
    # Then
    assert result is not None


def test_same_parties_on_same_day_at_different_confirmed_sites_are_not_merged() -> None:
    # Given
    published = datetime(2026, 10, 14, tzinfo=UTC)
    first = agreement_evidence("비궁 현지화 협력", LEFT, published)
    second = agreement_evidence(
        "비궁 현지화 협력", LEFT.replace("워싱턴", "서울"), published
    )
    # When
    result = same_agreement(first, second)
    # Then
    assert result is False
