from dataclasses import replace
from datetime import UTC, datetime

import pytest

from dapa_morning_brief.briefing import build_briefing, build_candidate_pool
from dapa_morning_brief.copilot_summary import ArticleBody
from dapa_morning_brief.models import Article, Section
from dapa_morning_brief.rss_parser import classify_title, is_relevant_article
from dapa_morning_brief.story_deduplication import are_same_articles


@pytest.mark.parametrize(
    "title",
    [
        '"미사일이 없다" 뒤늦게 부랴부랴…美 방산업계 호황',
        '[단독] "북 포로 송환" 후 러 군용기 이어 함정도 동해 전개',
        "한국 인근 해역에 러시아 함정 전개",
        "중국 방산기업, 신형 무인기 공개",
        "[칼럼] 강신철 신임 국방부 장관에게 거는 기대",
        "[사설] 국방예산 확대와 방산 수출의 미래",
        "[기고] KF-21 양산 계약에 대한 제언",
        "[기자수첩] 첨단무기보다 중요한 것… 우리 군에 싸울 의지",
        "[2026 지상군페스티벌] 첨단강군 육군 최대 축제 열린다",
    ],
)
def test_background_keywords_do_not_admit_foreign_or_opinion_news(title: str) -> None:
    # Given: search snippets contain domestic keywords unrelated to the main topic.
    description = "한국 국방예산과 한화 방산 수출, KF-21 개발도 배경으로 언급했다."
    # When
    relevant = is_relevant_article(title, description, "연합뉴스")
    # Then
    assert not relevant


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("DMZ 폭발 현장 찾은 국방위…北 지뢰일 경우 상응 대응", Section.GOVERNMENT),
        ("국방부, DMZ 지뢰 추정 폭발 상황 관련 브리핑", Section.GOVERNMENT),
        ("국방위, 방위사업법 개정안 의결", Section.POLICY),
        ("방사청, 국방조달 제도 개선안 발표", Section.POLICY),
        ("국방부, 한미 연합훈련 계획 발표", Section.GOVERNMENT),
        ("美 국방부, 한미동맹 강화 방안 발표", Section.GOVERNMENT),
        ("미국 해군, 한국 함정 도입 검토", Section.EXPORT_BUSINESS),
        ("폴란드 국방부, K9 자주포 추가 도입", Section.EXPORT_BUSINESS),
        ("KAI·멕시코, 항공우주산업 협력 강화", Section.EXPORT_BUSINESS),
        ("K2 전차 국내 양산 계약 체결", Section.WEAPON_SYSTEM),
        (
            "첫 KF-21 넘긴 KAI… 전투기 이후 '무장·정비'까지 판다",
            Section.EXPORT_BUSINESS,
        ),
        ("소수 업체가 방산시장 독과점…'50년 카르텔' 깬다", Section.POLICY),
        (
            "한화, 美 방산 영토 넓힌다…K9 이어 조선·해양까지 현지화 속도",
            Section.EXPORT_BUSINESS,
        ),
    ],
)
def test_primary_action_controls_category(title: str, expected: Section) -> None:
    # Given: unrelated technology and export context cannot override the headline.
    description = "한국 국방예산과 AI 전력화, 방산 수출 관련 배경을 소개했다."
    # When
    result = (
        is_relevant_article(title, description, "연합뉴스"),
        classify_title(title, description=description, source="연합뉴스"),
    )
    # Then
    assert result == (True, expected)


def test_overseas_weapon_arrival_uses_snippet_to_resolve_weapon_alias() -> None:
    # Given
    title = "예정보다 빨리 온 한국 K9…루마니아 첫 수송대열에 구원투수도"
    description = "한화에어로스페이스의 K9 자주포가 루마니아에 조기 인도됐다."
    # When
    section = classify_title(title, description=description, source="서울신문")
    # Then
    assert section is Section.EXPORT_BUSINESS


def _article(title: str, url: str) -> Article:
    return Article(
        title=title,
        url=url,
        published_at=datetime(2026, 9, 28, tzinfo=UTC),
        source="연합뉴스",
        section=Section.GOVERNMENT,
    )


def test_shared_vocabulary_without_matching_body_flow_is_not_duplicate() -> None:
    # Given: the same military vocabulary in different sentence order and facts.
    left = _article("국방부 현장 조사 결과 브리핑", "https://example.com/briefing")
    right = _article("국회 현장 방문 보고서 공개", "https://example.com/visit")
    words = [
        "국방부",
        "현장",
        "조사",
        "결과",
        "브리핑",
        "안전",
        "점검",
        "부대",
        "지뢰",
        "폭발",
        "사고",
        "원인",
        "분석",
        "장비",
        "확보",
        "예산",
        "계획",
        "대응",
        "국회",
        "위원회",
        "방문",
        "장병",
        "보호",
        "교육",
        "수색",
        "절차",
        "유엔사",
        "합동",
        "임무",
        "수행",
        "통로",
        "개척",
        "보고",
        "진술",
        "확인",
        "재발",
        "방지",
        "지원",
        "협의",
    ]
    # When
    duplicate = are_same_articles(
        left, right, left_body=" ".join(words), right_body=" ".join(reversed(words))
    )
    # Then
    assert not duplicate


def test_different_body_leads_are_not_merged_by_shared_background() -> None:
    # Given: two developments reuse the same long background passage.
    left = _article("국방부 조사단 감식 결과 공개", "https://example.com/results")
    right = _article("국회 위원들 부상 장병 위문", "https://example.com/visit")
    background = (
        "지난주 비무장지대 수색 작전 중 폭발 사고가 발생했다. "
        "당시 병력은 장비를 착용하고 통로를 개척하다가 부상을 입었다. "
        "유엔사와 우리 군은 공동 조사를 위해 현장을 보존하고 있다. "
    ) * 4
    left_lead = "조사단 감식 분석 파편 성분 장치 규격 증거 감정 전문가 결과 발표. "
    right_lead = "국회 의원 병원 방문 환자 가족 면담 치료 지원 의료진 격려 위문. "
    # When
    duplicate = are_same_articles(
        left,
        right,
        left_body=left_lead * 5 + background,
        right_body=right_lead * 5 + background,
    )
    # Then
    assert not duplicate


def test_similar_titles_do_not_override_different_substantial_bodies() -> None:
    # Given
    left = _article("국방부 DMZ 지뢰 사고 조사 발표", "https://example.com/a")
    right = replace(
        left, title="국방부 DMZ 지뢰 사고 현장 점검", url="https://example.com/b"
    )
    # When
    duplicate = are_same_articles(
        left,
        right,
        left_body=" ".join(f"감식자료{index}" for index in range(50)),
        right_body=" ".join(f"방문기록{index}" for index in range(50)),
    )
    # Then
    assert not duplicate


def test_body_reprints_are_removed_across_categories() -> None:
    # Given: distinct headlines for the same press statement.
    left = _article("조사 결과 발표…군 대응 방침 설명", "https://example.com/a")
    right = replace(
        left,
        title="비무장지대 현안 중간 브리핑",
        url="https://example.com/b",
        section=Section.POLICY,
    )
    body = (
        "합동참모본부는 비무장지대 폭발 사고 중간 조사 결과를 공개했다. "
        "조사단은 수색 현장에서 확보한 파편과 영상 자료를 분석했다. "
        "국립과학수사연구원 감식 결과를 종합해 지뢰 종류를 판정할 예정이다. "
        "군은 북한 매설 지뢰로 확인될 경우 상응하는 조치를 취한다고 밝혔다."
    )
    bodies = tuple(
        ArticleBody(article_url=a.url, title=a.title, source=a.source, body=body)
        for a in (left, right)
    )
    # When
    briefing = build_briefing((left, right), max_per_section=5, article_bodies=bodies)
    # Then
    assert sum(map(len, briefing.sections.values())) == 1


def test_candidates_keep_similar_headlines_until_body_comparison() -> None:
    # Given
    left = _article("국방부 DMZ 지뢰 사고 조사 발표", "https://example.com/a")
    right = replace(
        left, title="국방부 DMZ 지뢰 사고 현장 점검", url="https://example.com/b"
    )
    # When
    pool = build_candidate_pool((left, left, right), max_per_section=15)
    # Then
    assert set(pool.sections[Section.GOVERNMENT]) == {left, right}


def test_candidates_reserve_agency_coverage_without_fuzzy_dedup() -> None:
    # Given
    recent = replace(
        _article("국방 AI 실증", "https://example.com/a"), section=Section.POLICY
    )
    agency = replace(
        recent,
        title="방위사업청 AI 실증 사업",
        url="https://example.com/b",
        published_at=datetime(2026, 9, 27, tzinfo=UTC),
    )
    # When
    pool = build_candidate_pool((recent, agency), max_per_section=1)
    # Then
    assert pool.sections[Section.POLICY] == (agency,)
