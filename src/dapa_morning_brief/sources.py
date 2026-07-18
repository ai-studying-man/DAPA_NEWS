"""Source definitions and relevance keywords for the morning brief."""

from __future__ import annotations

from typing import Final

AGENCY_KEYWORDS: Final[tuple[str, ...]] = ("방위사업청", "방사청")

POLICY_KEYWORDS: Final[tuple[str, ...]] = (
    "방위사업청",
    "방사청",
    "방위사업",
    "방위력개선",
    "국방획득",
    "국방조달",
    "방위사업법",
    "국방예산",
    "국방정책",
    "선행연구",
    "탐색개발",
    "국방첨단인증",
    "국방품질",
    "국방기술품질원",
    "국방규격",
    "방산혁신클러스터",
    "군용기 MRO",
    "함정 MRO",
)

WEAPON_SYSTEM_KEYWORDS: Final[tuple[str, ...]] = (
    "무기체계",
    "전력화",
    "체계개발",
    "시험평가",
    "야전운용시험",
    "양산사업",
    "후속양산",
    "최초양산",
    "ROC",
    "CDR",
    "PDR",
    "KF-21",
    "KDDX",
    "L-SAM",
    "M-SAM",
    "천궁",
    "K2",
    "K9",
    "전차",
    "전투기",
    "함정",
    "잠수함",
    "미사일",
    "드론",
    "무인기",
    "K2C1",
    "F-15K",
    "KF-16",
    "링크-22",
    "LINK-22",
    "자폭드론",
    "무인잠수정",
    "호위함",
)

GENERIC_WEAPON_KEYWORDS: Final[tuple[str, ...]] = (
    "드론",
    "무인기",
    "미사일",
    "전차",
    "전투기",
    "함정",
    "잠수함",
    "AI",
    "우주",
)

DOMESTIC_WEAPON_PROGRAM_KEYWORDS: Final[tuple[str, ...]] = (
    "KF-21",
    "KDDX",
    "L-SAM",
    "M-SAM",
    "천궁",
    "K2",
    "K9 자주포",
    "K2C1",
    "F-15K",
    "KF-16",
    "링크-22",
    "LINK-22",
)

DEFENSE_TECH_KEYWORDS: Final[tuple[str, ...]] = (
    "AI",
    "인공지능",
    "무인화",
    "무인체계",
    "유무인복합",
)

DEFENSE_ANCHOR_KEYWORDS: Final[tuple[str, ...]] = (
    *POLICY_KEYWORDS,
    "국방부",
    "군",
    "육군",
    "해군",
    "공군",
    "해병대",
    "ADD",
    "국방과학연구소",
)

DEFENSE_BUSINESS_KEYWORDS: Final[tuple[str, ...]] = (
    "방산",
    "K방산",
    "K-방산",
    "방산수출",
    "방산기업",
    "방위산업",
    "방산계약",
    "절충교역",
    "한화에어로스페이스",
    "한화시스템",
    "한화오션",
    "LIG넥스원",
    "현대로템",
    "한국항공우주",
    "KAI",
    "풍산",
    "대한항공",
    "HD현대중공업",
    "HD현대",
    "K조선",
    "K-조선",
    "함정 수출",
    "특수선",
    "NATO 품질인증",
    "나토 품질인증",
)

EXPORT_EVENT_KEYWORDS: Final[tuple[str, ...]] = (
    "수출",
    "수주",
    "계약",
    "시장",
    "공급망",
    "스타트업",
    "파트너십",
)

EXPORT_DIRECTION_KEYWORDS: Final[tuple[str, ...]] = (
    "수출",
    "수주",
    "해외",
    "글로벌",
)

DEFENSE_EXPORT_PROGRAM_KEYWORDS: Final[tuple[str, ...]] = (
    "K2",
    "K9 자주포",
    "KF-21",
    "KDDX",
    "L-SAM",
    "M-SAM",
    "천궁",
)

DEFENSE_CONTEXT_KEYWORDS: Final[tuple[str, ...]] = (
    *POLICY_KEYWORDS,
    *WEAPON_SYSTEM_KEYWORDS,
    *DEFENSE_BUSINESS_KEYWORDS,
    "국방부",
    "군",
    "육군",
    "해군",
    "공군",
    "ADD",
    "국방과학연구소",
)

EXCLUDE_KEYWORDS: Final[tuple[str, ...]] = (
    "연예",
    "스포츠",
    "야구",
    "축구",
    "농구",
    "게임",
    "드라마",
    "영화",
    "음원",
    "맛집",
    "여행",
    "부동산",
    "코인",
    "가상자산",
    "주가 전망",
    "증시",
    "고문 영입",
    "영입",
    "전 대통령",
    "전대통령",
    "윤 전 대통령",
    "평양 무인기",
    "사망",
    "지병",
    "사고",
)

FOREIGN_CONTEXT_KEYWORDS: Final[tuple[str, ...]] = (
    "러시아",
    "러,",
    "우크라",
    "프랑스",
    "미국",
    "중국",
    "일본",
    "북한",
)

KOREA_ANCHOR_KEYWORDS: Final[tuple[str, ...]] = (
    "한국",
    "대한민국",
    "우리 군",
    "軍",
    "국방부",
    "방위사업청",
    "방사청",
    "국회",
    "K-방산",
    "K방산",
    "이재명 대통령",
    "이 대통령",
    "대통령실",
)


RELEVANT_KEYWORDS: Final[tuple[str, ...]] = DEFENSE_CONTEXT_KEYWORDS
