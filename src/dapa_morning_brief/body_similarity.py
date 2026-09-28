"""Compare substantial article text while distinguishing shared background."""

import re
from itertools import product
from typing import Final

from dapa_morning_brief.story_signals import (
    MIN_BODY_CONTAINMENT_RATIO,
    MIN_BODY_SHARED_SHINGLES,
    MIN_BODY_SHARED_TOKENS,
    body_shingles,
    title_tokens,
)

LEAD_WORD_COUNT: Final = 40
MIN_LEAD_OVERLAP: Final = 0.3
MIN_ORDERED_OVERLAP: Final = 0.04
MIN_PARAPHRASE_OVERLAP: Final = 0.35
EXTENDED_LEAD_WORD_COUNT: Final = 80
MIN_LONG_REPORT_WORDS: Final = 100
MIN_EARLY_ANCHOR_OVERLAP: Final = 0.2
MIN_LONG_REPORT_ORDERED_OVERLAP: Final = 0.15
MIN_LONG_REPORT_TOKEN_OVERLAP: Final = 0.4
ANNOUNCEMENT_WORD_COUNT: Final = 120
MIN_ANNOUNCEMENT_OVERLAP: Final = 0.7
MIN_ANNOUNCEMENT_BODY_OVERLAP: Final = 0.3
MIN_SPECIFIC_ANCHOR_LENGTH: Final = 6
MIN_SPECIFIC_ANCHORS: Final = 2
ANNOUNCEMENT_EVENTS: Final = frozenset(
    {"성과공유회", "간담회", "설명회", "보고회", "토론회", "세미나", "포럼", "협약식"}
)


def has_substantial_body(body: str) -> bool:
    """Require enough words for body evidence to supersede metadata similarity."""
    return len(body.split()) >= MIN_BODY_SHARED_TOKENS


def have_similar_bodies(left_body: str, right_body: str) -> bool:
    """Require lead overlap and ordered phrases as evidence of duplicate content."""
    lead_overlap = _lead_overlap(left_body, right_body, LEAD_WORD_COUNT)
    matching_lead = lead_overlap >= MIN_LEAD_OVERLAP
    extended_lead = (
        min(len(left_body.split()), len(right_body.split())) >= MIN_LONG_REPORT_WORDS
        and lead_overlap >= MIN_EARLY_ANCHOR_OVERLAP
        and _lead_overlap(left_body, right_body, EXTENDED_LEAD_WORD_COUNT)
        >= MIN_LEAD_OVERLAP
    )
    if not matching_lead and not extended_lead:
        return False
    left_tokens, right_tokens = title_tokens(left_body), title_tokens(right_body)
    shared_tokens = left_tokens & right_tokens
    token_overlap = len(shared_tokens) / min(len(left_tokens), len(right_tokens))
    if (
        extended_lead
        and len(shared_tokens) >= MIN_BODY_SHARED_TOKENS
        and token_overlap >= MIN_ANNOUNCEMENT_BODY_OVERLAP
        and _same_announced_event(left_body, right_body)
    ):
        return True
    left_shingles, right_shingles = body_shingles(left_body), body_shingles(right_body)
    shared_shingles = left_shingles & right_shingles
    if len(shared_shingles) < MIN_BODY_SHARED_SHINGLES:
        return False
    ordered_overlap = len(shared_shingles) / min(
        len(left_shingles), len(right_shingles)
    )
    if not matching_lead:
        return (
            ordered_overlap >= MIN_LONG_REPORT_ORDERED_OVERLAP
            and token_overlap >= MIN_LONG_REPORT_TOKEN_OVERLAP
            and len(shared_tokens) >= MIN_BODY_SHARED_TOKENS
        )
    if ordered_overlap >= MIN_BODY_CONTAINMENT_RATIO:
        return True
    return (
        ordered_overlap >= MIN_ORDERED_OVERLAP
        and len(shared_tokens) >= MIN_BODY_SHARED_TOKENS
        and token_overlap >= MIN_PARAPHRASE_OVERLAP
    )


def _lead_overlap(left_body: str, right_body: str, word_count: int) -> float:
    left = title_tokens(" ".join(left_body.split()[:word_count]))
    right = title_tokens(" ".join(right_body.split()[:word_count]))
    count = min(len(left), len(right))
    return len(left & right) / count if count else 0.0


def _same_announced_event(left_body: str, right_body: str) -> bool:
    left_sentences = re.split(
        r"(?<=[.!?])\s+", " ".join(left_body.split()[:ANNOUNCEMENT_WORD_COUNT])
    )
    right_sentences = re.split(
        r"(?<=[.!?])\s+", " ".join(right_body.split()[:ANNOUNCEMENT_WORD_COUNT])
    )
    for left_sentence, right_sentence in product(left_sentences, right_sentences):
        left_dates = set(re.findall(r"\b\d{1,2}일", left_sentence))
        if not left_dates or left_dates != set(
            re.findall(r"\b\d{1,2}일", right_sentence)
        ):
            continue
        left, right = title_tokens(left_sentence), title_tokens(right_sentence)
        shared = left & right
        if not shared.intersection(ANNOUNCEMENT_EVENTS):
            continue
        specific_anchors = {
            token for token in shared if len(token) >= MIN_SPECIFIC_ANCHOR_LENGTH
        }
        if (
            len(specific_anchors) >= MIN_SPECIFIC_ANCHORS
            and len(shared) / min(len(left), len(right)) >= MIN_ANNOUNCEMENT_OVERLAP
        ):
            return True
    return False
