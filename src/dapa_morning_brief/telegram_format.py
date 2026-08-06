"""Render a DAPA morning briefing for Telegram."""

from __future__ import annotations

import html
from typing import TYPE_CHECKING, Final

from dapa_morning_brief.models import Article, Section

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import date

    from dapa_morning_brief.models import Briefing, OfficialPressRelease, PracticePoint

SECTION_ORDER: Final[tuple[Section, ...]] = (
    Section.GOVERNMENT,
    Section.POLICY,
    Section.WEAPON_SYSTEM,
    Section.EXPORT_BUSINESS,
)

MORNING_QUOTES: Final[tuple[str, ...]] = (
    "대한민국 안보는 정확한 정보에서 시작됩니다.",
    "튼튼한 국방은 치밀한 준비에서 완성됩니다.",
    "오늘의 정확한 판단이 내일의 전력을 만듭니다.",
    "방위사업의 작은 점검이 큰 안보를 지킵니다.",
    "현장의 정보가 정책과 전력화의 출발점입니다.",
    "국방의 미래는 꾸준한 확인과 실행에서 시작됩니다.",
    "빠른 동향 파악이 더 나은 의사결정을 만듭니다.",
)

SECTION_ICONS: Final[dict[Section, str]] = {
    Section.GOVERNMENT: "🗞️",
    Section.POLICY: "🏛️",
    Section.WEAPON_SYSTEM: "⚙️",
    Section.EXPORT_BUSINESS: "🌏",
}

PRACTICE_POINTS: Final[dict[Section, str]] = {
    Section.GOVERNMENT: "대통령·국방부·군 주요 직위자 발언의 사업 영향 확인 필요.",
    Section.POLICY: "관련 제도, 예산, 조달 일정의 실무 영향 확인 필요.",
    Section.WEAPON_SYSTEM: "체계개발, 시험평가, 양산 일정 변동 여부 확인 필요.",
    Section.EXPORT_BUSINESS: "수출 계약, 공급망, 업체별 사업 영향 확인 필요.",
}

PRACTICE_POINT_RULES: Final[tuple[tuple[frozenset[str], str], ...]] = (
    (
        frozenset({"국방규격", "특허", "지식재산"}),
        "국방규격·지식재산권 반영 여부와 분쟁 영향을 확인할 필요.",
    ),
    (
        frozenset({"방산혁신클러스터", "방산혁신단지", "클러스터"}),
        "클러스터 참여기관·지원사업·지역별 추진 일정을 확인할 필요.",
    ),
    (
        frozenset({"인수", "지분", "매각", "출자"}),
        "지분·인수·매각 논의가 사업 수행체계에 미치는 영향을 확인할 필요.",
    ),
    (
        frozenset({"대표발의", "법안", "개정안", "입법"}),
        "법안의 적용 대상·시행 시점과 기존 사업 영향 여부를 확인할 필요.",
    ),
    (
        frozenset({"시험평가", "성능검증", "품질인증", "인증 획득"}),
        "시험평가·인증 결과와 후속 양산 일정 영향을 확인할 필요.",
    ),
    (
        frozenset({"양산", "전력화", "납품", "배치"}),
        "양산·전력화·납품 일정과 물량 변동 여부를 확인할 필요.",
    ),
    (
        frozenset({"공급망", "핵심부품", "소재·부품", "부품 국산화"}),
        "핵심 소재·부품 공급망과 대체조달·납기 위험을 확인할 필요.",
    ),
    (
        frozenset({"수출", "수주", "계약", "협상", "절충교역"}),
        "수출 계약·협상 조건과 현지화·후속지원 일정을 확인할 필요.",
    ),
    (
        frozenset({"기술동맹", "전략적 파트너", "공동개발", "협력체계"}),
        "국가·기업 간 협력 범위와 공동개발·인증·수출 연계를 확인할 필요.",
    ),
    (
        frozenset({"예산", "제도", "법률", "시행령", "조달"}),
        "제도·예산·조달 기준 변경과 진행 사업 적용 시점을 확인할 필요.",
    ),
    (
        frozenset({"ai", "인공지능", "드론", "무인기", "무인체계", "자율비행", "로봇"}),
        "AI·무인체계 적용 범위와 시험·인증·보안 요구사항을 확인할 필요.",
    ),
    (
        frozenset({"전차", "전투기", "함정", "잠수함", "미사일", "소총", "개인화기"}),
        "대상 무기체계의 요구성능·도입 일정·경쟁 구도 변화를 확인할 필요.",
    ),
    (
        frozenset({"후원", "나눔", "봉사", "기부"}),
        "방위사업 직접 관련성과 기업 사회공헌 정보의 포함 필요성을 재확인할 필요.",
    ),
    (
        frozenset({"대통령", "대통령실", "정부", "국방장관", "국무총리"}),
        "정부 지원·주요 직위자 발언의 후속 정책과 사업 반영 여부를 확인할 필요.",
    ),
)


def format_telegram_message(
    briefing: Briefing,
    *,
    today: date,
    practice_points: Iterable[PracticePoint] = (),
    official_press_releases: Iterable[OfficialPressRelease] = (),
) -> str:
    """Render a Telegram-ready plain text briefing."""
    generated_points = {point.article_url: point.text for point in practice_points}
    releases = tuple(official_press_releases)
    lines = [
        f"방사청 출근길 오늘의 뉴스는?💡 - {today:%Y.%m.%d}",
        "",
        "💬 오늘의 한마디",
        f'"{daily_quote(today)}"',
    ]
    for section in SECTION_ORDER:
        lines.extend(["", "━━━━━━━━━━━━━━━", ""])
        articles = briefing.sections[section]
        if section is Section.GOVERNMENT and not articles:
            lines.append(f"{section.display_title} : 오늘은 관련 내용 없음")
        else:
            lines.extend([_section_heading(section), ""])
            if not articles:
                lines.append("수집 기사 없음")
            for index, article in enumerate(articles, start=1):
                practice_point = generated_points.get(
                    article.url, _practice_point(article)
                )
                lines.extend(
                    [
                        f"{index}. {html.escape(article.title, quote=False)}",
                        f"📌 실무 참고: {html.escape(practice_point, quote=False)}",
                        (
                            "🔗 "
                            f'<a href="{html.escape(article.url)}">'
                            "뉴스 기사 링크 바로가기</a>"
                        ),
                        "",
                    ],
                )

        if section is Section.GOVERNMENT:
            lines.extend(["", "━━━━━━━━━━━━━━━", "", "🏛️ 국방부 / 방사청 보도자료", ""])
            if releases:
                for index, release in enumerate(releases, start=1):
                    published = release.published_on
                    lines.append(
                        "".join(
                            (
                                f"{index}. {html.escape(release.agency, quote=False)} ",
                                f"보도자료({published.year % 100}.{published.month}.",
                                f"{published.day}.) : ",
                                f'<a href="{html.escape(release.url)}"><b>',
                                f"{html.escape(release.title, quote=False)}</b></a>",
                            ),
                        ),
                    )
                lines.extend(["", '"가장 최근의 보도자료를 수집합니다"'])
            else:
                lines.append("수집된 공식 보도자료 없음")

    lines.extend(
        [
            "━━━━━━━━━━━━━━━",
            "",
            "📊 오늘의 키워드",
            "",
            "#방위사업 #무기체계 #전력화 #K방산 #방산수출",
        ],
    )
    return "\n".join(lines).strip()


def daily_quote(today: date) -> str:
    """Return a deterministic quote that changes by date."""
    return MORNING_QUOTES[today.toordinal() % len(MORNING_QUOTES)]


def _section_heading(section: Section) -> str:
    return f"{SECTION_ICONS[section]} {section.display_title}"


def _practice_point(article: Article) -> str:
    text = f"{article.title} {article.description}".casefold()
    for keywords, practice_point in PRACTICE_POINT_RULES:
        if any(keyword in text for keyword in keywords):
            return practice_point
    return PRACTICE_POINTS[article.section]
