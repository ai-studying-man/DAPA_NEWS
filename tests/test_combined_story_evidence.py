from dataclasses import replace
from datetime import UTC, datetime

import pytest

from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.story_deduplication import are_same_articles, are_same_story


def test_different_weapon_contracts_are_not_duplicates() -> None:
    left = Article(
        "방사청, K2 전차 폴란드 수출 계약 체결",
        "https://example.com/k2",
        datetime(2026, 9, 28, tzinfo=UTC),
        "뉴스A",
        Section.EXPORT_BUSINESS,
    )
    right = replace(
        left,
        title="방사청, K9 자주포 폴란드 수출 계약 체결",
        url="https://example.com/k9",
    )
    assert not are_same_story(left.title, right.title)
    assert not are_same_articles(left, right)


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("K2 전차 폴란드 1차 수출 계약 체결", "K2 전차 폴란드 2차 수출 계약 체결"),
        ("K9 자주포 폴란드 24문 수출 계약", "K9 자주포 폴란드 54문 수출 계약"),
    ],
)
def test_different_contract_rounds_or_quantities_are_not_duplicates(
    first: str, second: str
) -> None:
    left = Article(
        first,
        "https://example.com/a",
        datetime(2026, 9, 28, tzinfo=UTC),
        "뉴스A",
        Section.EXPORT_BUSINESS,
    )
    right = replace(left, title=second, url="https://example.com/b")
    assert not are_same_story(first, second)
    assert not are_same_articles(left, right)


@pytest.mark.parametrize("body_available", [True, False])
def test_short_briefing_captions_use_title_and_context_together(
    body_available: bool,
) -> None:
    # Given
    left = Article(
        "국방부, DMZ 지뢰 추정 폭발 상황 관련 브리핑",
        "https://example.com/photo",
        datetime(2026, 9, 28, tzinfo=UTC),
        "뉴스1",
        Section.GOVERNMENT,
        description="권대원 합참 차장이 DMZ 지뢰 추정 폭발 상황 브리핑을 하고 있다.",
    )
    right = replace(
        left,
        title='군 "북 매설지뢰로 최종판정되면 상응조치…모든책임 북에"',
        url="https://example.com/gallery",
        description=(
            "권대원 합동참모본부 차장이 비무장지대 폭발 중간 조사 결과를 브리핑했다."
        ),
    )
    # When
    duplicate = are_same_articles(
        left,
        right,
        left_body=left.description if body_available else "",
        right_body="",
    )
    # Then
    assert duplicate


def test_short_field_visit_is_not_the_briefing_with_same_background() -> None:
    # Given
    left = Article(
        "국방부 DMZ 지뢰 사고 조사 결과 브리핑",
        "https://example.com/briefing",
        datetime(2026, 9, 28, tzinfo=UTC),
        "뉴스1",
        Section.GOVERNMENT,
        description="합참은 DMZ 폭발 사고 조사 결과를 브리핑했다.",
    )
    right = replace(
        left,
        title="국방위 DMZ 지뢰 사고 현장 방문",
        url="https://example.com/visit",
        description="국방위 의원들이 DMZ 폭발 사고 현장을 방문해 점검했다.",
    )
    # When
    duplicate = are_same_articles(left, right)
    # Then
    assert not duplicate


def test_near_identical_headlines_still_merge_when_long_bodies_differ() -> None:
    # Given
    left = Article(
        "방사청, 전술 무전기 대체 부품 납품 재공고 결정",
        "https://example.com/a",
        datetime(2026, 9, 28, tzinfo=UTC),
        "뉴스A",
        Section.POLICY,
    )
    right = replace(
        left,
        title="방사청 전술 무전기 대체부품 납품 재공고 결정 [종합]",
        url="https://example.com/b",
    )
    # When
    duplicate = are_same_articles(
        left,
        right,
        left_body=" ".join(f"계약자료{index}" for index in range(45)),
        right_body=" ".join(f"취재기록{index}" for index in range(45)),
    )
    # Then
    assert duplicate


def test_reworded_leads_and_titles_identify_one_event() -> None:
    left = Article(
        "합참, DMZ 지뢰 폭발 사고 중간 브리핑",
        "https://example.com/report-a",
        datetime(2026, 9, 28, tzinfo=UTC),
        "뉴스A",
        Section.GOVERNMENT,
    )
    right = replace(
        left,
        title="국방부 DMZ 지뢰 사고 브리핑…북한 책임 확인되면 조치",
        url="https://example.com/report-b",
    )
    assert are_same_articles(
        left,
        right,
        left_body="합참이 DMZ 지뢰 폭발 사고 조사에 관한 중간 브리핑을 열었다. "
        + " ".join(f"감식자료{index}" for index in range(50)),
        right_body="오늘 열린 브리핑에서 DMZ 지뢰 사고 폭발 원인을 군이 설명했다. "
        + " ".join(f"대응기록{index}" for index in range(50)),
    )


def test_short_photo_captions_match_despite_different_quote_headline() -> None:
    attribution = "(서울=뉴스1) 김진환 기자 = 권대원 합동참모본부 차장이 28일 서울"
    context = "용산구 국방부 브리핑실에서 DMZ 지뢰 추정 폭발 상황 관련 중간 조사"
    captions = "합참 지뢰 폭발 사고 브리핑 합참, DMZ 지뢰 추정 폭발 사고"
    left = Article(
        "국방부, DMZ 지뢰 추정 폭발 상황 관련 브리핑",
        "https://example.com/photo-a",
        datetime(2026, 9, 28, tzinfo=UTC),
        "뉴스A",
        Section.GOVERNMENT,
    )
    right = replace(
        left,
        title='군 "북 매설지뢰로 최종판정되면 상응조치…모든책임 북에"',
        url="https://example.com/photo-b",
    )
    assert are_same_articles(
        left,
        right,
        left_body=f"{attribution} {context} 브리핑을 하고 있다. 2026.9.28/뉴스1",
        right_body=f"{captions} 브리핑 자료 설명하는 양진혁 합참 작전부장",
    )


def test_batch_and_total_quantities_do_not_override_matching_full_bodies() -> None:
    left = Article(
        "폴란드, K2 전차 180대 2차 계약 체결",
        "https://example.com/batch",
        datetime(2026, 9, 28, tzinfo=UTC),
        "뉴스A",
        Section.EXPORT_BUSINESS,
    )
    right = replace(
        left,
        title="K2 전차 2차 계약 체결…총 1,000대 도입 계획",
        url="https://example.com/total",
    )
    body = " ".join(f"동일계약내용{index}" for index in range(50))
    assert are_same_articles(left, right, left_body=body, right_body=body)
    different_round = replace(right, title="K2 전차 1차 계약 체결…총 1,000대 도입 계획")
    assert not are_same_articles(
        left, different_round, left_body=body, right_body=body
    )
