from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from dapa_morning_brief.briefing import build_briefing, build_candidate_pool
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, Section


def _article(title: str, index: int = 0) -> Article:
    return Article(
        title=title,
        url=f"https://example.com/story-{index}",
        published_at=datetime(2026, 9, 29, tzinfo=UTC) + timedelta(minutes=index),
        source="뉴스",
        section=Section.POLICY,
    )


def _oversubscribed_articles() -> list[Article]:
    titles = (
        "국방 예산 집행계획 발표",
        "군용기 정비시설 확충",
        "우주산업 기술지원 간담회",
        "첨단 소재 연구센터 개관",
        "해군 통신체계 실증 착수",
        "육군 드론 운용 교육",
        "항공 정비사 채용 확대",
        "국방 반도체 연구 협약",
        "장병 복지 지원 계획",
        "잠수함 정비 인력 양성",
        "군수 물류창고 확장",
        "부대 에너지 절감 시설",
        "국방 소프트웨어 경진대회",
        "지능형 보안 장비 시범운영",
        "군수품 인증제 개선",
        "공군 안전관리 회의 개최",
    )
    return [
        _article("방사청, 무전기에 때 아닌 급발진…외부의 힘 작용 했나 [취재파일]"),
        *[
            replace(
                _article(title, index),
                description="방위사업청 관련 배경을 설명했다.",
            )
            for index, title in enumerate(titles, start=1)
        ],
    ]


@pytest.mark.parametrize("candidate_stage", [True, False])
def test_acquisition_oversight_survives_oversubscribed_section(
    candidate_stage: bool,
) -> None:
    # Given
    articles = _oversubscribed_articles()
    cap = 15 if candidate_stage else 5
    # When
    result = (
        build_candidate_pool(articles, max_per_section=cap)
        if candidate_stage
        else build_briefing(articles, max_per_section=cap)
    )
    # Then
    selected = result.sections[Section.POLICY]
    assert articles[0] in selected
    assert len(selected) == cap


def test_incidental_civic_body_is_filtered_before_final_quota() -> None:
    # Given
    civic = _article("구미시, 방산·AI 예산 확보 협의", 2)
    defense = _article("군용기 정비시설 확충", 1)
    body = ArticleBody(
        article_url=civic.url,
        title=civic.title,
        source=civic.source,
        body=(
            "구미시와 도의원들이 예산을 논의했다. "
            "전통시장과 철도, 박물관, 보육 사업에 집중했다."
        ),
    )
    # When
    result = build_briefing((civic, defense), max_per_section=1, article_bodies=(body,))
    # Then
    assert result.sections[Section.POLICY] == (defense,)


def test_substantive_story_replaces_newer_photo_of_same_event_only() -> None:
    # Given
    full = _article("방사청 무전기 부품 원산지 변경 논란")
    photo = replace(
        full,
        title="[사진] 방사청 무전기 부품 원산지 변경 논란",
        url="https://example.com/photo",
        published_at=full.published_at + timedelta(minutes=1),
    )
    body = ArticleBody(
        article_url=full.url,
        title=full.title,
        source=full.source,
        body="방위사업청은 무전기 조달 사업의 부품 원산지 변경 경위를 조사했다. " * 8,
    )
    # When
    result = build_briefing((photo, full), max_per_section=5, article_bodies=(body,))
    # Then
    assert result.sections[Section.POLICY] == (full,)


def test_accountability_reservation_preserves_cross_section_deduplication() -> None:
    # Given
    articles = _oversubscribed_articles()
    same_story = replace(articles[0], section=Section.GOVERNMENT)
    # When
    result = build_briefing((same_story, *articles), max_per_section=5)
    # Then
    selected = [item for section in result.sections.values() for item in section]
    assert sum(item.url == articles[0].url for item in selected) == 1


def test_agency_background_cannot_displace_newer_ordinary_news() -> None:
    # Given
    older = replace(
        _article("기업 기술지원 협약"),
        description="방사청 무전기 부품 원산지 논란도 배경으로 소개했다.",
    )
    newer = _article("신규 국방 기술 실증", 1)
    # When
    result = build_briefing((older, newer), max_per_section=1)
    # Then
    assert result.sections[Section.POLICY] == (newer,)


def test_general_contract_scrutiny_is_reserved_without_investigative_label() -> None:
    # Given
    articles = _oversubscribed_articles()
    oversight = replace(articles[0], title="방위사업청 군수품 납품 계약 부실 감사")
    # When
    result = build_briefing((oversight, *articles[1:]), max_per_section=5)
    # Then
    assert oversight in result.sections[Section.POLICY]


def test_photo_and_substantive_variants_reach_body_inspection() -> None:
    # Given
    full = _article("방사청 무전기 부품 원산지 변경 논란")
    photo = replace(
        full,
        title="[사진] 방사청 무전기 부품 원산지 변경 논란",
        url="https://example.com/photo",
        published_at=full.published_at + timedelta(minutes=1),
    )
    # When
    result = build_candidate_pool((photo, full), max_per_section=15)
    # Then
    assert set(result.sections[Section.POLICY]) == {photo, full}


def test_distinct_photo_event_is_not_excluded_by_article_format() -> None:
    # Given
    photo = _article("[사진] 국방장관 군수시설 현장 방문", 1)
    oversight = _article("방위사업청 무전기 부품 원산지 논란")
    # When
    result = build_briefing((photo, oversight), max_per_section=5)
    # Then
    assert result.sections[Section.POLICY] == (photo, oversight)
