"""Headline boundaries for foreign coverage, opinion, and official actions."""

import re
from typing import Final

from dapa_morning_brief.article_scope import (
    DOMESTIC_GOVERNMENT_HEADLINE_PATTERN,
    FOREIGN_PRIMARY_COUNTRIES,
)
from dapa_morning_brief.business_rules import (
    DEFENSE_COMPANY_KEYWORDS,
    FOREIGN_MARKET_KEYWORDS,
)
from dapa_morning_brief.entity_catalog import contains_any
from dapa_morning_brief.sources import (
    AGENCY_KEYWORDS,
    DOMESTIC_WEAPON_PROGRAM_KEYWORDS,
)
from dapa_morning_brief.weapon_catalog import matching_weapons

FOREIGN_SUBJECT_COUNTRIES: Final[str] = "|".join(
    re.escape(country)
    for country in dict.fromkeys(
        (
            *FOREIGN_PRIMARY_COUNTRIES,
            *FOREIGN_MARKET_KEYWORDS,
            "미",
            "러",
            "中",
            "日",
            "北",
            "영국",
            "터키",
            "튀르키에",
        )
    )
)
FOREIGN_MILITARY_SUBJECT: Final[re.Pattern[str]] = re.compile(
    "".join(
        (
            rf"(?<![가-힣])(?:{FOREIGN_SUBJECT_COUNTRIES})(?:의)?\s*",
            r"(?:(?:국산|자국산|자국)\s*)?",
            r"(?:방산|방위산업|군용기|훈련기|함정|호위함|전투기|미사일|",
            r"해군|육군|공군|국방부|군|정부)",
        )
    ),
    re.IGNORECASE,
)
OPINION_LABEL: Final[re.Pattern[str]] = re.compile(
    r"""[\[\uff3b【(][^\]\uff3d】)]*
    (?:칼럼|사설|기고|시론|논단|오피니언|기자수첩)
    [^\]\uff3d】)]*[\]\uff3d】)]""",
    re.VERBOSE,
)
KOREAN_ACQUISITION_LINK: Final[re.Pattern[str]] = re.compile(
    r"""(?:대한민국|한국|韓|국군|우리[ ]군).{0,60}
    (?:계약|도입|구매|개발|전력화|납품|수출|공급|협력|정비|건조)""",
    re.VERBOSE,
)
CIVIC_TOPIC_GROUPS: Final[tuple[tuple[str, ...], ...]] = (
    ("전통시장", "골목경제", "소상공인"),
    ("푸드테크", "농업", "먹거리"),
    ("철도", "도로", "교통망"),
    ("박물관", "관광", "문화시설"),
    ("출산", "보육", "복지"),
)
CIVIC_ACTOR: Final[re.Pattern[str]] = re.compile(
    r"지자체|시청|도청|시의회|도의회|도의원|시의원|[가-힣]+(?:시|군)[,\uff0c은는와과]"
)
MIN_CIVIC_TOPICS: Final = 2
OVERSEAS_CONTEXT_LIMIT: Final = 600
LIFECYCLE_LEAD_LIMIT: Final = 160


def is_incidental_civic_agenda(title: str, context: str) -> bool:
    """Reject multi-sector civic agendas, not dedicated defense budget coverage."""
    text = f"{title} {context}"
    if CIVIC_ACTOR.search(text) is None or not contains_any(
        text, ("예산", "국비", "주요 현안", "지역 현안", "민생", "시정")
    ):
        return False
    mixed_title = any(contains_any(title, group) for group in CIVIC_TOPIC_GROUPS)
    dedicated_defense = contains_any(
        title, ("방산혁신클러스터", "국방", "방위사업", "방산기업", "방산 부품")
    )
    if dedicated_defense and not mixed_title:
        return False
    return (
        sum(contains_any(text, group) for group in CIVIC_TOPIC_GROUPS)
        >= MIN_CIVIC_TOPICS
    )


def is_opinion_headline(title: str) -> bool:
    """Recognize explicit editorial labels, not incidental opinion keywords."""
    return OPINION_LABEL.search(title) is not None


def has_unrelated_foreign_subject(title: str) -> bool:
    """Require a headline-level Korean link for foreign military subjects."""
    if FOREIGN_MILITARY_SUBJECT.search(title) is None:
        return False
    korean_link = (
        bool(matching_weapons(title))
        or contains_any(title, (*DEFENSE_COMPANY_KEYWORDS, "한화 필리조선소"))
        or contains_any(title, DOMESTIC_WEAPON_PROGRAM_KEYWORDS)
        or contains_any(title, AGENCY_KEYWORDS)
        or contains_any(title, ("한미동맹", "주한미군", "한미 연합"))
        or KOREAN_ACQUISITION_LINK.search(title) is not None
        or DOMESTIC_GOVERNMENT_HEADLINE_PATTERN.search(title.strip()) is not None
    )
    return not korean_link


def is_defense_public_action(title: str) -> bool:
    """Identify defense oversight and briefings independently of background policy."""
    actor = contains_any(title, ("국방위", "국방부", "합참"))
    action = contains_any(title, ("브리핑", "현장", "조사", "보고", "대응", "점검"))
    return actor and action


def is_overseas_delivery(title: str, description: str) -> bool:
    """Use snippets to disambiguate weapons only when the title describes shipment."""
    return (
        contains_any(title, FOREIGN_MARKET_KEYWORDS)
        and contains_any(title, ("수송대열", "첫 수송", "현지 도착", "조기 인도"))
        and not contains_any(title, ("훈련", "연습"))
        and bool(matching_weapons(f"{title} {description}"))
    )


def is_overseas_weapon_use(title: str, context: str = "") -> bool:
    """Separate overseas use of Korean weapons from domestic development trials."""
    lead = f"{title} {context[:OVERSEAS_CONTEXT_LIMIT]}"
    return (
        contains_any(lead, FOREIGN_MARKET_KEYWORDS)
        and contains_any(lead, ("홍보 영상", "홍보영상", "현지 운용", "현지운용"))
        and not contains_any(
            f"{title} {context[:LIFECYCLE_LEAD_LIMIT]}",
            ("시험", "개발", "성능개량", "초도양산", "국내 전력화"),
        )
        and any("해외도입" not in entry.domain for entry in matching_weapons(title))
    )
