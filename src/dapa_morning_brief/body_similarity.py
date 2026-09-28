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
MIN_ORDERED_OVERLAP: Final = 0.2
MIN_PARAPHRASE_OVERLAP: Final = 0.55


def has_substantial_body(body: str) -> bool:
    """Require enough words for body evidence to supersede metadata similarity."""
    return len(body.split()) >= MIN_BODY_SHARED_TOKENS


def have_similar_bodies(left_body: str, right_body: str) -> bool:
    """Require lead overlap and ordered phrases as evidence of duplicate content."""
    left_lead = title_tokens(" ".join(left_body.split()[:LEAD_WORD_COUNT]))
    right_lead = title_tokens(" ".join(right_body.split()[:LEAD_WORD_COUNT]))
    lead_count = min(len(left_lead), len(right_lead))
    if not lead_count or len(left_lead & right_lead) / lead_count < MIN_LEAD_OVERLAP:
        return False
    left_shingles, right_shingles = body_shingles(left_body), body_shingles(right_body)
    shared_shingles = left_shingles & right_shingles
    if len(shared_shingles) < MIN_BODY_SHARED_SHINGLES:
        return False
    ordered_overlap = len(shared_shingles) / min(
        len(left_shingles), len(right_shingles)
    )
    if ordered_overlap >= MIN_BODY_CONTAINMENT_RATIO:
        return True
    left_tokens, right_tokens = title_tokens(left_body), title_tokens(right_body)
    shared_tokens = left_tokens & right_tokens
    return (
        ordered_overlap >= MIN_ORDERED_OVERLAP
        and len(shared_tokens) >= MIN_BODY_SHARED_TOKENS
        and len(shared_tokens) / min(len(left_tokens), len(right_tokens))
        >= MIN_PARAPHRASE_OVERLAP
    )
