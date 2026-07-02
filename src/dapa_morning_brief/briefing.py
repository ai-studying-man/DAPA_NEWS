from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date
from typing import Final, assert_never

from dapa_morning_brief.models import Article, Briefing, Section

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

TOPIC_KEYWORDS: Final[tuple[str, ...]] = (
    "방산혁신클러스터",
    "미르온",
    "KF-21",
    "KDDX",
    "L-SAM",
    "M-SAM",
    "K9",
    "K2",
    "천궁",
    "핵잠수함",
    "전작권",
    "한화에어로스페이스",
    "LIG넥스원",
    "현대로템",
    "한국항공우주",
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


def build_briefing(
    articles: Iterable[Article],
    *,
    max_per_section: int,
) -> Briefing:
    """Select newest non-duplicate articles for each section."""
    buckets: dict[Section, list[Article]] = {section: [] for section in SECTION_ORDER}
    global_seen_topics: set[str] = set()

    for section in SECTION_ORDER:
        seen_topics: set[str] = set()
        candidates = sorted(
            (article for article in articles if article.section == section),
            key=lambda article: (
                _source_rank(article.source),
                -article.published_at.timestamp(),
                article.title,
            ),
        )
        for article in candidates:
            topic = _dedupe_key(article.title)
            if topic in seen_topics or topic in global_seen_topics:
                continue
            seen_topics.add(topic)
            global_seen_topics.add(topic)
            buckets[section].append(article)
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
                    f"{index}. {article.title}",
                    f"→ {summarize_title(article.title)}",
                    f"📌 실무 참고: {_practice_point(section)}",
                    f"🔗 {article.url}",
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


def summarize_title(title: str) -> str:
    """Create a short 30-40 character summary from article title metadata."""
    cleaned = re.sub(r"\s+", " ", title).strip(" -|[]")
    cleaned = re.sub(r"^\[[^\]]+\]\s*", "", cleaned)
    if len(cleaned) <= 40:
        return cleaned
    return f"{cleaned[:37].rstrip()}..."


def daily_quote(today: date) -> str:
    """Return a deterministic quote that changes by date."""
    return MORNING_QUOTES[today.toordinal() % len(MORNING_QUOTES)]


def _section_heading(section: Section) -> str:
    match section:
        case Section.GOVERNMENT:
            return f"🗞️ {section.title}"
        case Section.POLICY:
            return f"🏛️ {section.title}"
        case Section.WEAPON_SYSTEM:
            return f"⚙️ {section.title}"
        case Section.EXPORT_BUSINESS:
            return f"🌏 {section.title}"
        case unreachable:
            assert_never(unreachable)


def _practice_point(section: Section) -> str:
    match section:
        case Section.GOVERNMENT:
            return "대통령·국방부·군 주요 직위자 발언의 사업 영향 확인 필요."
        case Section.POLICY:
            return "관련 제도, 예산, 조달 일정의 실무 영향 확인 필요."
        case Section.WEAPON_SYSTEM:
            return "체계개발, 시험평가, 양산 일정 변동 여부 확인 필요."
        case Section.EXPORT_BUSINESS:
            return "수출 계약, 공급망, 업체별 사업 영향 확인 필요."
        case unreachable:
            assert_never(unreachable)


def _source_rank(source: str) -> int:
    for index, keyword in enumerate(SOURCE_PRIORITY):
        if keyword in source:
            return index
    return len(SOURCE_PRIORITY)


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", "", title).casefold()


def _dedupe_key(title: str) -> str:
    normalized = _normalize_title(title)
    if ("공격헬기" in normalized or "미르온" in normalized) and "엔진" in normalized:
        return "topic:공격헬기엔진"
    if "대드론" in normalized and "요격" in normalized:
        return "topic:대드론요격"
    for keyword in TOPIC_KEYWORDS:
        if _normalize_title(keyword) in normalized:
            return f"topic:{_normalize_title(keyword)}"
    return normalized
