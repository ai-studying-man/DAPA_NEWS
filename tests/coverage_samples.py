from datetime import UTC, datetime

from dapa_morning_brief.models import Article, Section


def coverage_articles(limit: int = 6) -> tuple[Article, ...]:
    titles = {
        Section.GOVERNMENT: (
            "대통령 국무회의 주재",
            "장관 부대 방문",
            "정부 업무보고 시행",
            "국방부 장병 복지 발표",
            "해군 병력 모집 공고",
            "합참 경계태세 점검",
        ),
        Section.POLICY: (
            "획득 예산 편성",
            "조달 절차 개선",
            "품질 인증 확대",
            "규격 문서 개정",
            "선행 연구 착수",
            "계약 심사 규정 공고",
        ),
        Section.WEAPON_SYSTEM: (
            "전투기 양산 계약",
            "미사일 요격 시험",
            "잠수함 신규 배치",
            "정찰위성 궤도 진입",
            "전투원 무전기 성능 검증",
            "레이더 개발 착수",
        ),
        Section.EXPORT_BUSINESS: (
            "유럽 수출 협상",
            "기업 해외 공장 설립",
            "중동 납품 완료",
            "장갑차 호주 공급",
            "필리핀 군함 구매 승인",
            "폴란드 탄약 생산 협약",
        ),
    }
    return tuple(
        Article(
            title,
            f"https://news.test/{section.value}/{index}",
            datetime(2026, 10, 4, 12 - index, tzinfo=UTC),
            "테스트뉴스",
            section,
        )
        for section, headlines in titles.items()
        for index, title in enumerate(headlines[:limit])
    )
