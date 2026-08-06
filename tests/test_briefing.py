from __future__ import annotations

from datetime import datetime, timezone
from unittest import TestCase

from dapa_morning_brief.briefing import build_briefing, format_telegram_message
from dapa_morning_brief.models import Article, OfficialPressRelease, Section


class BriefingTest(TestCase):
    def test_build_briefing_deduplicates_titles_and_limits_each_section(self) -> None:
        # Given
        published = datetime(2026, 6, 14, 6, 0, tzinfo=timezone.utc)
        articles = [
            Article(
                title="방위사업청 획득제도 개선안 발표",
                url="https://example.com/a",
                published_at=published,
                source="정책브리핑",
                section=Section.POLICY,
            ),
            Article(
                title="방위사업청 획득제도 개선안 발표",
                url="https://example.com/b",
                published_at=published,
                source="Google News",
                section=Section.POLICY,
            ),
        ]
        articles.extend(
            Article(
                title=f"정책 기사 {index}",
                url=f"https://example.com/policy-{index}",
                published_at=published,
                source="뉴스",
                section=Section.POLICY,
            )
            for index in range(1, 5)
        )

        # When
        briefing = build_briefing(articles, max_per_section=3)

        # Then
        policy_articles = briefing.sections[Section.POLICY]
        self.assertEqual(3, len(policy_articles))
        self.assertEqual("방위사업청 획득제도 개선안 발표", policy_articles[0].title)
        self.assertEqual(
            len({article.title for article in policy_articles}),
            len(policy_articles),
        )

    def test_build_briefing_keeps_first_similar_title_only(self) -> None:
        # Given
        published = datetime(2026, 7, 9, 6, 0, tzinfo=timezone.utc)
        articles = [
            Article(
                title="개회사하는 이용철 방위사업청장 - 네이트",
                url="https://example.com/first",
                published_at=published,
                source="네이트",
                section=Section.POLICY,
            ),
            Article(
                title="개회사 하는 이용철 방위사업청장 - 연합뉴스",
                url="https://example.com/second",
                published_at=published,
                source="연합뉴스",
                section=Section.POLICY,
            ),
            Article(
                title="이용철 방위사업청장, 개회사 - 네이트",
                url="https://example.com/third",
                published_at=published,
                source="네이트",
                section=Section.POLICY,
            ),
        ]

        # When
        briefing = build_briefing(articles, max_per_section=3)

        # Then
        policy_articles = briefing.sections[Section.POLICY]
        self.assertEqual(1, len(policy_articles))
        self.assertEqual("https://example.com/first", policy_articles[0].url)

    def test_format_telegram_message_contains_new_headline_and_sections(self) -> None:
        # Given
        published = datetime(2026, 6, 14, 6, 0, tzinfo=timezone.utc)
        briefing = build_briefing(
            [
                Article(
                    title="KF-21 후속 양산 계획 구체화",
                    url="https://example.com/kf21",
                    published_at=published,
                    source="국방일보",
                    section=Section.WEAPON_SYSTEM,
                ),
            ],
            max_per_section=3,
        )

        # When
        message = format_telegram_message(
            briefing,
            today=datetime(2026, 6, 14, tzinfo=timezone.utc).date(),
        )

        # Then
        self.assertIn("방사청 출근길 오늘의 뉴스는?💡 - 2026.06.14", message)
        self.assertIn("현 정부 / 국방부 주요 뉴스 : 오늘은 관련 내용 없음", message)
        self.assertIn("방위사업 관련 동향", message)
        self.assertIn("무기체계·전력화", message)
        self.assertNotIn("→ KF-21 후속 양산 계획 구체화", message)
        self.assertIn("📌 실무 참고:", message)
        self.assertIn(
            '🔗 <a href="https://example.com/kf21">뉴스 기사 링크 바로가기</a>',
            message,
        )

    def test_format_telegram_message_includes_current_government_articles(self) -> None:
        # Given
        published = datetime(2026, 6, 14, 6, 0, tzinfo=timezone.utc)
        briefing = build_briefing(
            [
                Article(
                    title="이재명 대통령 방산 수출 지원 확대 언급",
                    url="https://example.com/president",
                    published_at=published,
                    source="정책브리핑",
                    section=Section.GOVERNMENT,
                ),
            ],
            max_per_section=3,
        )

        # When
        message = format_telegram_message(
            briefing,
            today=datetime(2026, 6, 14, tzinfo=timezone.utc).date(),
        )

        # Then
        self.assertIn("현 정부 / 국방부 주요 뉴스", message)
        self.assertIn("1. 이재명 대통령 방산 수출 지원 확대 언급", message)
        self.assertIn(
            '🔗 <a href="https://example.com/president">뉴스 기사 링크 바로가기</a>',
            message,
        )

    def test_official_press_release_section_follows_government_news(self) -> None:
        # Given
        briefing = build_briefing([], max_per_section=3)

        # When
        message = format_telegram_message(
            briefing,
            today=datetime(2026, 8, 6, tzinfo=timezone.utc).date(),
            official_press_releases=(),
        )

        # Then
        government_index = message.index("현 정부 / 국방부 주요 뉴스")
        official_index = message.index("국방부 / 방사청 보도자료")
        policy_index = message.index("방위사업 관련 동향")
        self.assertLess(government_index, official_index)
        self.assertLess(official_index, policy_index)

    def test_official_press_release_section_renders_latest_board_links(self) -> None:
        # Given
        briefing = build_briefing([], max_per_section=3)
        releases = (
            OfficialPressRelease(
                agency="국방부",
                title="국방부 업무보고",
                url=("https://www.mnd.go.kr/bbs/mnd/13000005/DPIM_118612/artclView.do"),
                published_on=datetime(2026, 8, 5, tzinfo=timezone.utc).date(),
            ),
            OfficialPressRelease(
                agency="방위사업청",
                title="‘대체불가 K-방산’으로의 도약",
                url=(
                    "https://www.dapa.go.kr/dapa/doc/selectDoc.do?"
                    "bbsSeq=326&docSeq=58959&menuSeq=3069"
                ),
                published_on=datetime(2026, 8, 5, tzinfo=timezone.utc).date(),
            ),
        )

        # When
        message = format_telegram_message(
            briefing,
            today=datetime(2026, 8, 7, tzinfo=timezone.utc).date(),
            official_press_releases=releases,
        )

        # Then
        self.assertIn(
            '1. 국방부 보도자료(26.8.5.) : <a href="https://www.mnd.go.kr/'
            + 'bbs/mnd/13000005/DPIM_118612/artclView.do"><b>국방부 '
            + "업무보고</b></a>",
            message,
        )
        self.assertIn(
            '2. 방위사업청 보도자료(26.8.5.) : <a href="https://www.dapa.go.kr/'
            + 'dapa/doc/selectDoc.do?bbsSeq=326&amp;docSeq=58959&amp;menuSeq=3069">'
            + "<b>‘대체불가 K-방산’으로의 도약</b></a>",
            message,
        )
        self.assertIn('"가장 최근의 보도자료를 수집합니다"', message)

    def test_format_telegram_message_escapes_html_in_article_fields(self) -> None:
        # Given
        published = datetime(2026, 7, 9, 6, 0, tzinfo=timezone.utc)
        briefing = build_briefing(
            [
                Article(
                    title='K9·원전 협력 강화 논의 <속보> & "확인"',
                    url="https://example.com/news?a=1&b=2",
                    published_at=published,
                    source="뉴스",
                    section=Section.GOVERNMENT,
                ),
            ],
            max_per_section=3,
        )

        # When
        message = format_telegram_message(
            briefing,
            today=datetime(2026, 7, 9, tzinfo=timezone.utc).date(),
        )

        # Then
        self.assertIn(
            '1. K9·원전 협력 강화 논의 &lt;속보&gt; &amp; "확인"',
            message,
        )
        self.assertIn(
            'href="https://example.com/news?a=1&amp;b=2"',
            message,
        )

    def test_format_telegram_message_rotates_daily_quote(self) -> None:
        # Given
        briefing = build_briefing([], max_per_section=3)

        # When
        first_message = format_telegram_message(
            briefing,
            today=datetime(2026, 6, 14, tzinfo=timezone.utc).date(),
        )
        second_message = format_telegram_message(
            briefing,
            today=datetime(2026, 6, 15, tzinfo=timezone.utc).date(),
        )

        # Then
        self.assertNotEqual(
            _quote_line(first_message),
            _quote_line(second_message),
        )


def _quote_line(message: str) -> str:
    for line in message.splitlines():
        if line.startswith('"') and line.endswith('"'):
            return line
    msg = "message does not contain a quoted daily phrase"
    raise AssertionError(msg)
