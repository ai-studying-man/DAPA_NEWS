"""Headline boundaries for foreign coverage, opinion, and official actions."""

import re
from typing import Final

from dapa_morning_brief.article_scope import DOMESTIC_GOVERNMENT_HEADLINE_PATTERN
from dapa_morning_brief.business_rules import (
    DEFENSE_COMPANY_KEYWORDS,
    FOREIGN_MARKET_KEYWORDS,
)
from dapa_morning_brief.entity_catalog import contains_any
from dapa_morning_brief.sources import DOMESTIC_WEAPON_PROGRAM_KEYWORDS
from dapa_morning_brief.weapon_catalog import matching_weapons

FOREIGN_MILITARY_SUBJECT: Final[re.Pattern[str]] = re.compile(
    r"""(?<![가-힣])(?:미국|美|미|러시아|러|중국|中|일본|日|북한|北|영국|
    유럽|이스라엘|이란|우크라이나|대만|캐나다|호주|폴란드|루마니아)
    (?:의)?\s*(?:방산|방위산업|군용기|함정|호위함|전투기|미사일|
    해군|육군|공군|국방부|군|정부)""",
    re.VERBOSE,
)
OPINION_LABEL: Final[re.Pattern[str]] = re.compile(
    r"""[\[\uff3b【(][^\]\uff3d】)]*
    (?:칼럼|사설|기고|시론|논단|오피니언|기자수첩)
    [^\]\uff3d】)]*[\]\uff3d】)]""",
    re.VERBOSE,
)
KOREAN_ACQUISITION_LINK: Final[re.Pattern[str]] = re.compile(
    r"""(?:한국|韓|국군|우리[ ]군|국산).{0,60}
    (?:계약|도입|구매|개발|전력화|납품|수출|공급|협력|정비|건조)""",
    re.VERBOSE,
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
