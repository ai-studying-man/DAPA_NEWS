"""Near-duplicate story detection for collected news titles."""

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from dapa_morning_brief.models import Article

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
MIN_EVENT_SUBJECT_TOKEN_LENGTH: Final = 6
MIN_TOKEN_LENGTH_FOR_PARTICLE_STRIP: Final = 4
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


def are_same_story(left_title: str, right_title: str) -> bool:
    """Return whether two differently worded titles describe one event."""
    left_normalized = _normalize_title(left_title)
    right_normalized = _normalize_title(right_title)
    left_series = _series_key(left_title)
    right_series = _series_key(right_title)
    left_known_event = _known_event_key(left_normalized)
    right_known_event = _known_event_key(right_normalized)
    if (
        left_normalized == right_normalized
        or (left_series is not None and left_series == right_series)
        or (left_known_event is not None and left_known_event == right_known_event)
    ):
        return True

    left_tokens = _title_tokens(left_title)
    right_tokens = _title_tokens(right_title)
    if left_tokens == right_tokens:
        return True

    if _have_conflicting_event_facts(left_tokens, right_tokens):
        return False

    shared_tokens = left_tokens & right_tokens
    shares_event_subject = any(
        len(token) >= MIN_EVENT_SUBJECT_TOKEN_LENGTH for token in shared_tokens
    )
    if (
        shares_event_subject
        and left_tokens & EVENT_ACTION_TOKENS
        and right_tokens & EVENT_ACTION_TOKENS
    ) or (
        len(shared_tokens) >= MIN_SHARED_CONTEXT_TOKENS
        and any(
            left_tokens & context_tokens and right_tokens & context_tokens
            for context_tokens in EVENT_CONTEXT_TOKEN_GROUPS
        )
    ):
        return True
    if len(shared_tokens) < MIN_SHARED_TOKENS:
        return False

    shorter_token_count = min(len(left_tokens), len(right_tokens))
    containment_ratio = len(shared_tokens) / shorter_token_count
    return containment_ratio >= MIN_CONTAINMENT_RATIO or bool(
        shared_tokens & EVENT_ACTION_TOKENS,
    )


def _have_conflicting_event_facts(
    left_tokens: frozenset[str],
    right_tokens: frozenset[str],
) -> bool:
    left_markets = left_tokens & EVENT_MARKET_TOKENS
    right_markets = right_tokens & EVENT_MARKET_TOKENS
    different_markets = (
        left_markets and right_markets and left_markets.isdisjoint(right_markets)
    )
    conflicting_outcomes = (
        left_tokens & POSITIVE_EVENT_OUTCOME_TOKENS
        and right_tokens & NEGATIVE_EVENT_OUTCOME_TOKENS
    ) or (
        right_tokens & POSITIVE_EVENT_OUTCOME_TOKENS
        and left_tokens & NEGATIVE_EVENT_OUTCOME_TOKENS
    )
    return bool(different_markets or conflicting_outcomes)


def are_same_articles(left: Article, right: Article) -> bool:
    """Compare article titles and available RSS descriptions."""
    if are_same_story(left.title, right.title):
        return True
    if not left.description or not right.description:
        return False

    left_tokens = _title_tokens(left.description)
    right_tokens = _title_tokens(right.description)
    shared_tokens = left_tokens & right_tokens
    if len(shared_tokens) < MIN_DESCRIPTION_SHARED_TOKENS:
        return False
    shorter_token_count = min(len(left_tokens), len(right_tokens))
    return len(shared_tokens) / shorter_token_count >= MIN_DESCRIPTION_CONTAINMENT_RATIO


def _normalize_title(title: str) -> str:
    source_stripped = re.sub(r"\s+-\s+[^-]+$", "", html.unescape(title))
    return re.sub(r"[^0-9a-z가-힣]+", "", source_stripped.casefold())


def _series_key(title: str) -> str | None:
    matched = re.match(r"^\s*\[([^]]+)]", html.unescape(title))
    if matched is None:
        return None
    normalized = re.sub(r"[^0-9a-z가-힣]+", "", matched.group(1).casefold())
    if normalized in GENERIC_SERIES_HEADERS:
        return None
    return normalized or None


def _known_event_key(normalized_title: str) -> str | None:
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


def _title_tokens(title: str) -> frozenset[str]:
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
    normalized = re.sub(r"snt\s*다이내믹스", "snt", normalized)
    normalized = re.sub(r"k\s*-\s*방산", "방산", normalized)
    normalized = normalized.replace("방산혁신단지", "방산혁신클러스터")
    return normalized.replace("대통령표창", "대통령 표창")


def _compact_title_token(token: str) -> str:
    if len(token) == 1 and not token.isdigit():
        return ""
    if token.endswith("하는") and len(token) > len("하는"):
        return token.removesuffix("하는")
    if "연구원" in token:
        return "연구원"
    for particle in KOREAN_PARTICLES:
        if (
            token.endswith(particle)
            and len(token) >= MIN_TOKEN_LENGTH_FOR_PARTICLE_STRIP
        ):
            return token.removesuffix(particle)
    return token
