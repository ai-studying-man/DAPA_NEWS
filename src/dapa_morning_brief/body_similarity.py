"""Compare substantial article text while distinguishing shared background."""

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
    left_shingles, right_shingles = body_shingles(left_body), body_shingles(right_body)
    shared_shingles = left_shingles & right_shingles
    if len(shared_shingles) < MIN_BODY_SHARED_SHINGLES:
        return False
    ordered_overlap = len(shared_shingles) / min(
        len(left_shingles), len(right_shingles)
    )
    left_tokens, right_tokens = title_tokens(left_body), title_tokens(right_body)
    shared_tokens = left_tokens & right_tokens
    token_overlap = len(shared_tokens) / min(len(left_tokens), len(right_tokens))
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
