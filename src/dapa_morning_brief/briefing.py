"""Build and render a deduplicated DAPA morning briefing."""

from __future__ import annotations

import html
from typing import TYPE_CHECKING, Final

from dapa_morning_brief.models import Article, Briefing, Section
from dapa_morning_brief.story_deduplication import are_same_articles

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import date

SECTION_ORDER: Final[tuple[Section, ...]] = (
    Section.GOVERNMENT,
    Section.POLICY,
    Section.WEAPON_SYSTEM,
    Section.EXPORT_BUSINESS,
)

SOURCE_PRIORITY: Final[tuple[str, ...]] = (
    "정책브리핑",
    "방위사업청",
    "국방부",
    "국방일보",
    "뉴스와이어",
    "네이버",
    "Google",
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


def build_briefing(
    articles: Iterable[Article],
    *,
    max_per_section: int,
) -> Briefing:
    """Select newest non-duplicate articles for each section."""
    buckets: dict[Section, list[Article]] = {section: [] for section in SECTION_ORDER}
    selected_articles: list[Article] = []

    for section in SECTION_ORDER:
        candidates = sorted(
            (article for article in articles if article.section == section),
            key=_article_rank,
        )
        for article in candidates:
            if any(
                are_same_articles(article, selected)
                for selected in selected_articles
            ):
                continue
            buckets[section].append(article)
            selected_articles.append(article)
            if len(buckets[section]) >= max_per_section:
                break

    return Briefing(
        sections={section: tuple(buckets[section]) for section in SECTION_ORDER},
    )


def format_telegram_message(briefing: Briefing, *, today: date) -> str:
    """Render a Telegram-ready plain text briefing."""
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
            lines.append("현 정부 주요 뉴스 : 오늘은 관련 내용 없음")
            continue

        lines.extend([_section_heading(section), ""])
        if not articles:
            lines.append("수집 기사 없음")
            continue
        for index, article in enumerate(articles, start=1):
            lines.extend(
                [
                    f"{index}. {html.escape(article.title, quote=False)}",
                    (
                        "📌 실무 참고: "
                        f"{html.escape(_practice_point(section), quote=False)}"
                    ),
                    (
                        "🔗 "
                        f'<a href="{html.escape(article.url)}">'
                        "뉴스 기사 링크 바로가기</a>"
                    ),
                    "",
                ],
            )

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


def _practice_point(section: Section) -> str:
    return PRACTICE_POINTS[section]


def _source_rank(source: str) -> int:
    for index, keyword in enumerate(SOURCE_PRIORITY):
        if keyword in source:
            return index
    return len(SOURCE_PRIORITY)


def _article_rank(article: Article) -> tuple[int, int, int, int, int, float]:
    view_count_known = 0 if article.view_count is not None else 1
    view_count_rank = -(article.view_count if article.view_count is not None else 0)
    feed_rank_known = 0 if article.feed_rank is not None else 1
    feed_rank = article.feed_rank if article.feed_rank is not None else 0
    return (
        view_count_known,
        view_count_rank,
        feed_rank_known,
        feed_rank,
        _source_rank(article.source),
        -article.published_at.timestamp(),
    )
