from __future__ import annotations

from datetime import date

import httpx

from dapa_morning_brief.models import OfficialPressRelease
from dapa_morning_brief.official_press_releases import (
    collect_latest_press_releases,
    parse_dapa_press_releases,
    parse_mnd_press_releases,
    select_latest_press_release,
)


def test_parse_dapa_press_releases_builds_direct_detail_link() -> None:
    # Given
    document = (
        '<table><tbody><tr><td class="num">691</td><td class="subject">'
        '<a href="#none" onclick="fn_selectDoc(\'58959\')">'
        '<p class="text">‘대체불가 K-방산’으로의 도약</p>'
        '<span class="new">새 글</span></a></td><td>2026-08-05</td>'
        '<td class="view">151</td></tr></tbody></table>'
    )

    # When
    releases = parse_dapa_press_releases(document)

    # Then
    assert releases == (
        OfficialPressRelease(
            agency="방위사업청",
            title="‘대체불가 K-방산’으로의 도약",
            url=(
                "https://www.dapa.go.kr/dapa/doc/selectDoc.do?"
                "bbsSeq=326&docSeq=58959&menuSeq=3069"
            ),
            published_on=date(2026, 8, 5),
        ),
    )


def test_parse_mnd_press_releases_reads_title_date_and_link() -> None:
    # Given
    document = (
        '<table><tbody><tr><td class="td-num">13343</td>'
        '<td class="td-title alignL"><a href="/bbs/mnd/13000005/'
        'DPIM_118612/artclView.do"><strong><span>국방부 업무보고</span>'
        '</strong><span class="new">새글</span></a></td>'
        '<td class="td-date">2026.08.05</td>'
        '<td class="td-counts">116</td></tr></tbody></table>'
    )

    # When
    releases = parse_mnd_press_releases(document)

    # Then
    assert releases == (
        OfficialPressRelease(
            agency="국방부",
            title="국방부 업무보고",
            url=("https://www.mnd.go.kr/bbs/mnd/13000005/DPIM_118612/artclView.do"),
            published_on=date(2026, 8, 5),
        ),
    )


def test_select_latest_press_release_keeps_latest_before_as_of_date() -> None:
    # Given
    releases = (
        OfficialPressRelease(
            agency="국방부",
            title="미래 게시물",
            url="https://example.com/future",
            published_on=date(2026, 8, 8),
        ),
        OfficialPressRelease(
            agency="국방부",
            title="8월 5일 최신 보도자료",
            url="https://example.com/latest",
            published_on=date(2026, 8, 5),
        ),
        OfficialPressRelease(
            agency="국방부",
            title="8월 4일 보도자료",
            url="https://example.com/older",
            published_on=date(2026, 8, 4),
        ),
    )

    # When
    latest = select_latest_press_release(releases, as_of=date(2026, 8, 7))

    # Then
    assert latest == releases[1]


def test_collect_latest_press_releases_returns_one_per_official_board() -> None:
    # Given
    documents = {
        "https://www.mnd.go.kr/mnd/167/subview.do": (
            '<table><tr><td class="td-title"><a href="/bbs/mnd/13000005/'
            'DPIM_118612/artclView.do"><span>국방부 업무보고</span></a></td>'
            '<td class="td-date">2026.08.05</td></tr></table>'
        ),
        ("https://www.dapa.go.kr/dapa/doc/selectDocList.do?bbsSeq=326&menuSeq=3069"): (
            '<table><tr><td class="subject"><a onclick="fn_selectDoc(\'58959\')">'
            "<p>‘대체불가 K-방산’으로의 도약</p></a></td>"
            "<td>2026-08-05</td></tr></table>"
        ),
    }

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=documents[str(request.url)])

    # When
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        releases = collect_latest_press_releases(
            as_of=date(2026, 8, 7),
            client=client,
        )

    # Then
    assert [release.agency for release in releases] == ["국방부", "방위사업청"]
    assert [release.published_on for release in releases] == [
        date(2026, 8, 5),
        date(2026, 8, 5),
    ]
