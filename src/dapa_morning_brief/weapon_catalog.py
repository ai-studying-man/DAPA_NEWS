"""Publicly sourced seed registry, not an exhaustive military inventory."""

from dataclasses import dataclass
from typing import Final

from dapa_morning_brief.entity_catalog import contains_any


@dataclass(frozen=True, slots=True)
class WeaponEntry:
    """Keep identity, contextual disambiguation and verification evidence together."""

    identifier: str
    aliases: tuple[str, ...]
    domain: str
    source_url: str
    context: tuple[str, ...] = ()
    service: str = "미확인"
    status: str = "공식 제품/사업 존재 확인; 현 운용 상태 미확인"
    checked_on: str = "2026-09-17"


ROTEM: Final[str] = "https://www.hyundai-rotem.co.kr/ko/business/defense/content.do"
HANWHA: Final[str] = "https://www.hanwhaaerospace.com/kor/whatwedo/product/land.do"
KAI: Final[str] = "https://www.koreaaero.com/KO/Business/T50.aspx"
KAI_HELICOPTERS: Final[str] = "https://www.koreaaero.com/KO/MediaCenter/PR_Video.aspx"
LIG: Final[str] = "https://www.ligdefenseaerospace.com/about/history.do"
NAVAL: Final[str] = (
    "https://www.hanwhasystems.com/kr/business/defense/naval/combat_index.do"
)
KOREAN_CONTEXT: Final[tuple[str, ...]] = (
    "한국",
    "대한민국",
    "국군",
    "우리 군",
    "방위사업청",
    "방사청",
    "국산",
    "KAI",
    "한국항공우주",
)
WEAPON_CATALOG: Final[tuple[WeaponEntry, ...]] = (
    WeaponEntry(
        "k2", ("K2", "K-2"), "지상기동", ROTEM, ("전차", "tank", "로템", "Rotem")
    ),
    WeaponEntry(
        "k2c1",
        ("K2C1",),
        "개인화기",
        "https://www.korea.kr/news/policyNewsView.do?newsId=148968058",
        service="해병대(인용 부대)",
    ),
    WeaponEntry("k600", ("K600",), "지상기동", ROTEM),
    WeaponEntry("k808", ("K808",), "지상기동", ROTEM),
    WeaponEntry("k806", ("K806",), "지상기동", ROTEM),
    WeaponEntry("k877", ("K877",), "지휘통제", ROTEM),
    WeaponEntry("k870", ("K870",), "지휘통제", ROTEM),
    WeaponEntry(
        "k9", ("K9", "K-9"), "화력", HANWHA, ("자주포", "howitzer", "한화", "Hanwha")
    ),
    WeaponEntry(
        "k10", ("K10",), "군수지원", HANWHA, ("탄약", "장갑차", "한화", "Hanwha")
    ),
    WeaponEntry("k77", ("K77",), "지휘통제", HANWHA),
    WeaponEntry("k105a1", ("K105A1",), "화력", HANWHA),
    WeaponEntry("k55a1", ("K55A1",), "화력", HANWHA),
    WeaponEntry("k56", ("K56",), "군수지원", HANWHA),
    WeaponEntry("chunmoo", ("천무",), "화력", HANWHA),
    WeaponEntry("cheongung", ("천궁",), "방공", LIG),
    WeaponEntry("bigung", ("비궁",), "유도무기", LIG),
    WeaponEntry(
        "cheonma", ("천마",), "방공", LIG, ("유도무기", "방공", "지대공", "LIG")
    ),
    WeaponEntry(
        "kf21",
        ("KF-21", "KF21", "KF 21", "보라매"),
        "항공",
        "https://www.koreaaero.com/VIRTUAL_EX/CorporateZone/FixedWing.html",
    ),
    WeaponEntry("t50", ("T-50", "T50"), "항공", KAI, KOREAN_CONTEXT),
    WeaponEntry("t50i", ("T-50i",), "항공", KAI),
    WeaponEntry("ta50", ("TA-50", "TA50"), "항공", KAI),
    WeaponEntry("fa50", ("FA-50", "FA50"), "항공", KAI),
    WeaponEntry("surion", ("KUH-1", "수리온"), "항공", KAI_HELICOPTERS),
    WeaponEntry("lah", ("LAH", "소형무장헬기"), "항공", KAI_HELICOPTERS),
    WeaponEntry("kss3", ("KSS-III", "장보고-III"), "해양", NAVAL, service="해군"),
    WeaponEntry(
        "ticn",
        ("TICN", "전술정보통신체계"),
        "지휘통신",
        "https://www.hanwhasystems.com/m/kr/business/defense/c5i/communication01.do",
    ),
    WeaponEntry(
        "f35a",
        ("F-35A", "F35A"),
        "항공(해외도입)",
        "https://www.dapa.go.kr/dapa/doc/selectDoc.do?bbsSeq=326&docSeq=18580&menuSeq=3069",
        KOREAN_CONTEXT,
        service="공군",
    ),
)


def matching_weapons(text: str) -> tuple[WeaponEntry, ...]:
    """Require identifying context for homonyms and internationally shared systems."""
    return tuple(
        entry
        for entry in WEAPON_CATALOG
        if contains_any(text, entry.aliases)
        and (not entry.context or contains_any(text, entry.context))
    )
