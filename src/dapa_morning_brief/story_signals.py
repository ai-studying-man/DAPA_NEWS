"""Token normalization and reviewed event signals for news deduplication."""

import html
import re
from typing import Final

LOW_SIGNAL_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "관련",
        "논의",
        "발표",
        "사진",
        "속보",
        "종합",
        "단독",
        "하는",
        "전격",
        "최신",
    },
)
GENERIC_SERIES_HEADERS: Final[frozenset[str]] = frozenset(
    {"기고", "단독", "사설", "속보", "인터뷰", "종합", "포토"},
)
EVENT_ACTION_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "개발",
        "계약",
        "도입",
        "발사",
        "배치",
        "수주",
        "시험",
        "완료",
        "진수",
        "착수",
        "체결",
        "취소",
        "표창",
        "조성",
        "출범",
        "구축",
        "협약",
        "업무협약",
        "검토",
    },
)
EVENT_CONTEXT_TOKEN_GROUPS: Final[tuple[frozenset[str], ...]] = (
    frozenset(
        {
            "매입",
            "베팅",
            "인수",
            "지분",
            "출자",
            "투자",
            "확대",
            "확보",
        },
    ),
)
EVENT_MARKET_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "인도네시아",
        "폴란드",
        "루마니아",
        "사우디",
        "아랍에미리트",
        "이라크",
        "미국",
        "캐나다",
        "호주",
        "필리핀",
        "태국",
        "말레이시아",
        "페루",
        "멕시코",
        "uae",
    },
)
POSITIVE_EVENT_OUTCOME_TOKENS: Final[frozenset[str]] = frozenset(
    {"체결", "완료", "성공", "수주", "착수"},
)
NEGATIVE_EVENT_OUTCOME_TOKENS: Final[frozenset[str]] = frozenset(
    {"취소", "무산", "실패", "중단"},
)
MIN_SHARED_TOKENS: Final = 3
MIN_SHARED_CONTEXT_TOKENS: Final = 2
MIN_CONTAINMENT_RATIO: Final = 0.5
MIN_DESCRIPTION_SHARED_TOKENS: Final = 4
MIN_DESCRIPTION_CONTAINMENT_RATIO: Final = 0.7
BODY_SHINGLE_SIZE: Final = 3
MIN_BODY_SHARED_SHINGLES: Final = 8
MIN_BODY_CONTAINMENT_RATIO: Final = 0.5
MIN_BODY_SHARED_TOKENS: Final = 30
MIN_EVENT_SUBJECT_TOKEN_LENGTH: Final = 6
MIN_TOKEN_LENGTH_FOR_PARTICLE_STRIP: Final = 3
ADMINISTRATIVE_SUFFIXES: Final[tuple[str, ...]] = (
    "특별자치도",
    "특별자치시",
    "광역시",
    "특별시",
    "시",
    "도",
    "군",
)
KOREAN_PARTICLES: Final[tuple[str, ...]] = (
    "으로",
    "에서",
    "에게",
    "까지",
    "부터",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "에",
    "의",
    "로",
)


def body_shingles(body: str) -> frozenset[tuple[str, ...]]:
    """Build ordered word triples for body-flow comparison."""
    tokens = re.findall(r"[0-9a-z]+|[가-힣]+", html.unescape(body).casefold())
    return frozenset(
        tuple(tokens[index : index + BODY_SHINGLE_SIZE])
        for index in range(len(tokens) - BODY_SHINGLE_SIZE + 1)
    )


def normalize_title(title: str) -> str:
    """Remove publisher suffixes and punctuation for exact title comparison."""
    source_stripped = re.sub(r"\s+-\s+[^-]+$", "", html.unescape(title))
    return re.sub(r"[^0-9a-z가-힣]+", "", source_stripped.casefold())


def series_key(title: str) -> str | None:
    """Extract a specific series header, excluding generic editorial labels."""
    matched = re.match(r"^\s*\[([^]]+)]", html.unescape(title))
    if matched is None:
        return None
    normalized = re.sub(r"[^0-9a-z가-힣]+", "", matched.group(1).casefold())
    if normalized in GENERIC_SERIES_HEADERS:
        return None
    return normalized or None


def known_event_key(normalized_title: str) -> str | None:
    """Recognize reviewed event paraphrases rather than individual keywords."""
    if "한화" in normalized_title and any(
        marker in normalized_title
        for marker in ("힐링데이", "군인가족", "모범군인", "모범장병")
    ):
        return "한화군인가족힐링데이"
    if (
        "공격헬기" in normalized_title or "미르온" in normalized_title
    ) and "엔진" in normalized_title:
        return "공격헬기엔진"
    if "대드론" in normalized_title and "요격" in normalized_title:
        return "대드론요격"
    if ("천궁ii" in normalized_title or "천궁2" in normalized_title) and (
        "중동3개국" in normalized_title or "세계방공망" in normalized_title
    ):
        return "천궁ii수출확산"
    return None


def title_tokens(title: str) -> frozenset[str]:
    """Normalize aliases and Korean suffixes for event comparison."""
    normalized_aliases = _normalize_aliases(title)
    source_stripped = re.sub(r"\s+-\s+[^-]+$", "", normalized_aliases)
    raw_tokens: list[str] = re.findall(
        r"[0-9a-z]+|[가-힣]+",
        source_stripped,
    )
    tokens = {
        token
        for raw_token in raw_tokens
        if (token := _compact_title_token(raw_token)) and token not in LOW_SIGNAL_TOKENS
    }
    return frozenset(tokens)


def _normalize_aliases(title: str) -> str:
    normalized = html.unescape(title).casefold()
    normalized = re.sub(r"\bmexico\b", "멕시코", normalized)
    normalized = re.sub(r"시연\s*(?:행사|회)(?:에서|서)?", "시연", normalized)
    normalized = normalized.replace("무인기", "드론")
    normalized = re.sub(r"snt\s*다이내믹스", "snt", normalized)
    normalized = re.sub(r"k\s*-\s*방산", "방산", normalized)
    normalized = normalized.replace(
        "방산혁신클러스터지역협의회",
        "방산혁신클러스터 지역협의회",
    )
    normalized = normalized.replace("방산혁신단지", "방산혁신클러스터")
    return normalized.replace("대통령표창", "대통령 표창")


def _compact_title_token(token: str) -> str:
    if len(token) == 1 and not token.isdigit():
        return ""
    if token.endswith("하는") and len(token) > len("하는"):
        return token.removesuffix("하는")
    if "연구원" in token:
        return "연구원"
    for suffix in ADMINISTRATIVE_SUFFIXES:
        if token.endswith(suffix) and len(token) > len(suffix) + 1:
            return token.removesuffix(suffix)
    for particle in KOREAN_PARTICLES:
        if (
            token.endswith(particle)
            and len(token) >= MIN_TOKEN_LENGTH_FOR_PARTICLE_STRIP
        ):
            return token.removesuffix(particle)
    return token
