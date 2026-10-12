from dapa_morning_brief.article_classification import is_relevant_article
from dapa_morning_brief.entity_catalog import contains_keyword
from dapa_morning_brief.weapon_catalog import matching_weapons


def test_cheongung_alias_does_not_match_inside_crop_name() -> None:
    # Given
    title = "황기·일천궁, 작물별 물 관리 중요… 적정 토양 수분 기준 밝혀"
    # When
    matched = contains_keyword(title, "천궁")
    # Then
    assert not matched


def test_crop_article_has_no_weapon_identity_or_newsletter_relevance() -> None:
    # Given
    title = "황기·일천궁, 작물별 물 관리 중요… 적정 토양 수분 기준 밝혀"
    description = "농촌진흥청은 약용작물 황기와 일천궁의 물 관리 기준을 밝혔다."
    # When
    weapons = matching_weapons(title)
    relevant = is_relevant_article(title, description, "농기자재신문")
    # Then
    assert weapons == ()
    assert not relevant


def test_cheongung_particles_and_model_suffixes_remain_supported() -> None:
    # Given
    samples = ("천궁을 도입한다", "천궁Ⅱ 요격 성공", "천궁-II 수출", "한국형 천궁2")
    # When
    matched = tuple(contains_keyword(text, "천궁") for text in samples)
    # Then
    assert all(matched)
