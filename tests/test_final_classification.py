from datetime import UTC, datetime

import pytest

from dapa_morning_brief.briefing import build_briefing
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, Section


@pytest.mark.parametrize(
    ("title", "body", "source", "original", "expected"),
    [
        (
            "청년의 시각으로 국방정책 효능감 높인다",
            "국방부 청년조직은 국방정책에 참여하는 청년들의 의견을 수렴했다.",
            "국방일보",
            Section.POLICY,
            Section.GOVERNMENT,
        ),
        (
            "KAI, 모로코 에어쇼서 FA-50으로 아프리카 시장 공략",
            "한국항공우주산업은 FA-50 수출을 위해 에어쇼에 참가한다.",
            "뉴스",
            Section.WEAPON_SYSTEM,
            Section.EXPORT_BUSINESS,
        ),
        (
            "KAI, 해병대 상륙기동헬기 성과기반 군수지원 계약 체결",
            "KAI는 방위사업청과 MUH-1 성과기반 군수지원(PBL) 계약을 체결했다.",
            "뉴스",
            Section.EXPORT_BUSINESS,
            Section.POLICY,
        ),
    ],
)
def test_final_selection_corrects_body_verified_category(
    title: str, body: str, source: str, original: Section, expected: Section
) -> None:
    # Given
    article = Article(
        title,
        "https://example.com/story",
        datetime(2026, 10, 13, tzinfo=UTC),
        source,
        original,
    )
    inspected = ArticleBody(article.url, title, source, body)
    # When
    result = build_briefing((article,), max_per_section=5, article_bodies=(inspected,))
    # Then
    assert [item.url for item in result.sections[expected]] == [article.url]


def test_final_selection_rejects_nondefense_body_despite_supplied_category() -> None:
    # Given
    article = Article(
        "황기·일천궁, 작물별 물 관리 중요",
        "https://example.com/crop",
        datetime(2026, 10, 13, tzinfo=UTC),
        "농업뉴스",
        Section.WEAPON_SYSTEM,
        search_provider="naver",
    )
    body = ArticleBody(
        article.url,
        article.title,
        article.source,
        "농촌진흥청은 약용작물 황기와 일천궁의 재배와 물 관리 연구 결과를 발표했다.",
    )
    # When
    result = build_briefing((article,), max_per_section=5, article_bodies=(body,))
    # Then
    assert sum(map(len, result.sections.values())) == 0


def test_unavailable_body_preserves_existing_category() -> None:
    # Given
    article = Article(
        "정책 기사",
        "https://example.com/opaque",
        datetime(2026, 10, 13, tzinfo=UTC),
        "뉴스",
        Section.POLICY,
    )
    # When
    result = build_briefing((article,), max_per_section=5)
    # Then
    assert result.sections[Section.POLICY] == (article,)


def test_background_export_does_not_move_domestic_weapon_story() -> None:
    # Given
    article = Article(
        "국내 K9 자주포 성능개량 시험 완료",
        "https://example.com/domestic",
        datetime(2026, 10, 13, tzinfo=UTC),
        "뉴스",
        Section.WEAPON_SYSTEM,
        search_provider="naver",
    )
    body = ArticleBody(
        article.url,
        article.title,
        article.source,
        "국내 전력화를 위한 성능개량 시험을 마쳤다. " * 50
        + "배경으로 해외 시장 공략과 수출 마케팅을 소개했다.",
    )
    # When
    result = build_briefing((article,), max_per_section=5, article_bodies=(body,))
    # Then
    assert result.sections[Section.WEAPON_SYSTEM] == (article,)


@pytest.mark.parametrize("provider", ["", "naver"])
def test_crop_primary_topic_is_rejected_for_every_input_path(provider: str) -> None:
    # Given
    article = Article(
        "황기·일천궁, 작물별 물 관리 중요",
        "https://example.com/agriculture",
        datetime(2026, 10, 13, tzinfo=UTC),
        "농업뉴스",
        Section.WEAPON_SYSTEM,
        search_provider=provider,
    )
    body = ArticleBody(
        article.url,
        article.title,
        article.source,
        "농촌진흥청은 약용작물 재배를 위한 토양 수분 관리 기준을 밝혔다.",
    )
    # When
    result = build_briefing((article,), max_per_section=5, article_bodies=(body,))
    # Then
    assert sum(map(len, result.sections.values())) == 0


@pytest.mark.parametrize(
    ("title", "body", "expected"),
    [
        (
            "독자 기술로 창과 방패 동시 개발…함정 수출 경쟁력↑",
            "국내 기술로 CIWS·KVLS 무기체계를 개발하고 성능시험을 진행했다.",
            Section.WEAPON_SYSTEM,
        ),
        (
            "방산업체 3곳서 미허가 화약류 취급시설 10군데나 운영",
            "정부 합동 점검에서 방산업체 미허가 화약류 시설을 적발했다.",
            Section.POLICY,
        ),
    ],
)
def test_primary_development_or_regulatory_action_precedes_export_label(
    title: str, body: str, expected: Section
) -> None:
    # Given
    article = Article(
        title,
        "https://example.com/review",
        datetime(2026, 10, 13, tzinfo=UTC),
        "뉴스",
        Section.EXPORT_BUSINESS,
    )
    inspected = ArticleBody(article.url, title, article.source, body)
    # When
    result = build_briefing((article,), max_per_section=5, article_bodies=(inspected,))
    # Then
    assert len(result.sections[expected]) == 1


def test_military_primary_rule_survives_incidental_personnel_keyword() -> None:
    # Given
    article = Article(
        "군 수소충전 인프라 구축 빨라지나…허가·검사체계 군 특례 추진",
        "https://example.com/hydrogen",
        datetime(2026, 10, 13, tzinfo=UTC),
        "뉴스",
        Section.GOVERNMENT,
        search_provider="naver",
    )
    body = ArticleBody(
        article.url,
        article.title,
        article.source,
        "군 수소충전 시설 법령 특례와 안전관리자 선임 의무를 검토한다.",
    )
    # When
    result = build_briefing((article,), max_per_section=5, article_bodies=(body,))
    # Then
    assert sum(map(len, result.sections.values())) == 1


def test_herb_homonym_requires_combat_context_in_final_review() -> None:
    # Given
    article = Article(
        "천궁 약재의 효능과 재배",
        "https://example.com/herb",
        datetime(2026, 10, 13, tzinfo=UTC),
        "농업뉴스",
        Section.WEAPON_SYSTEM,
    )
    body = ArticleBody(
        article.url,
        article.title,
        article.source,
        "농촌진흥청은 약용작물 천궁의 토양 수분과 재배 방법을 연구했다.",
    )
    # When
    result = build_briefing((article,), max_per_section=5, article_bodies=(body,))
    # Then
    assert sum(map(len, result.sections.values())) == 0


def test_verified_satellite_failure_keeps_weapon_lifecycle_category() -> None:
    # Given
    article = Article(
        "[단독] 군 정찰위성 4호기 또 덜컥…5개월째 우주서 먹통",
        "https://example.com/satellite",
        datetime(2026, 10, 13, tzinfo=UTC),
        "MBC",
        Section.WEAPON_SYSTEM,
        search_provider="naver",
    )
    body = ArticleBody(
        article.url,
        article.title,
        article.source,
        "우리 군 정찰위성 4호기의 구동기 고장이 발생해 정상 운용이 어렵다.",
    )
    # When
    result = build_briefing((article,), max_per_section=5, article_bodies=(body,))
    # Then
    assert len(result.sections[Section.WEAPON_SYSTEM]) == 1
