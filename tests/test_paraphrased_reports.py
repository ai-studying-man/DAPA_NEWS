import pytest

from dapa_morning_brief.body_similarity import have_similar_bodies


def test_rewritten_delivery_report_keeps_distributed_phrase_evidence() -> None:
    # Given: shared facts are interspersed with independently written reporting.
    left = (
        "공군은 한국형 전투기 양산 1호기를 사천 공장에서 인도받았다. "
        "첫 기체는 경북 예천 운용기지로 이동하면서 편대 비행을 진행했다. "
        "이번 인도는 독자 항공기 개발 계획을 추진한 이후 오랜 기간의 결실이다. "
        "노후 전투기 대체 사업으로 시작된 개발에는 여러 연구기관이 참여했다. "
        "공군 관계자는 향후 실전 배치와 조종사 교육을 준비한다고 설명했다. "
        "기체는 비행시험과 공중급유 시험을 거쳐 전투용 적합 판정을 받았다. "
        "최초 운용대대는 시설 정비와 정비사 양성에 집중할 방침이다. "
        "방위사업청은 추가 생산 물량에 대한 품질 관리도 지속한다. "
        "군 당국은 다음 해부터 임무 수행을 단계적으로 확대할 예정이다. "
        "정부는 안전한 영공 방어를 최우선 과제로 제시했다."
    )
    right = (
        "한국형 전투기 양산 1호기가 드디어 공군에 전달됐다. "
        "사천 공장에서 출발한 기체는 경북 예천 운용기지에 도착했다. "
        "전투기 개발의 긴 여정을 마치고 실전 운영 준비가 시작된 셈이다. "
        "최초 국산 전투기의 등장으로 우리 항공 산업도 새로운 전기를 맞았다. "
        "노후 전투기 대체 목적에 더해 미래 전장에 대응할 능력을 확보했다. "
        "각종 공중급유 시험과 무장 검증 결과 전투용 적합 판정을 통과했다. "
        "비행대대는 정비사 양성과 조종사 교육을 동시에 추진할 계획이다. "
        "후속 생산에서 품질 관리도 중요한 과제로 남는다. "
        "군은 차기 연도 전력화 선언을 목표로 관련 시설을 준비하고 있다. "
        "정부는 안전한 영공 방어를 최우선 과제로 제시했다."
    )
    # When
    duplicate = have_similar_bodies(left, right)
    # Then
    assert duplicate


def test_shared_series_introduction_does_not_merge_distinct_body_leads() -> None:
    # Given
    introduction = (
        "세계 방산 시장이 빠르게 성장하면서 국내 기업도 도약하고 있다. "
        "현지화와 기술 이전 요구가 커지고 인공지능 역량도 중요해졌다. "
    )
    left = "한화 생산 공장 증설 납기 개선 신규 시설 건설 계획. " * 5
    right = "시장 분석 환율 수출 금융 정책 기업 투자 전망 검토. " * 5
    # When
    duplicate = have_similar_bodies(left + introduction, right + introduction)
    # Then
    assert not duplicate


@pytest.mark.parametrize("short_extract", [False, True])
def test_long_reports_with_different_opening_emphasis_share_event_details(
    *, short_extract: bool
) -> None:
    # Given
    event = "국방부 플랫폼 성과공유회 서비스 운영 클라우드 기술 장병 행정 "
    left_opening = event + (
        "가입자 증가 실적 집계 현황 만족도 설문 편의성 신뢰도 응답 평가 "
        "절차 문서 양식 승인 조회 처리 속도 단축 시간 비용 절감 개선 "
        "접속 사용 빈도 화면 접근 통계 결과 성과 "
    )
    right_opening = event + (
        "생성형 모델 학습 질문 답변 추론 검색 추천 자동화 지능형 비서 "
        "데이터 분석 연동 확장 도입 예정 계획 단계 시연 실험 구현 "
        "프로그래밍 계산 반도체 저장 알고리즘 소프트웨어 컴퓨터 네트워크 연구 개발 "
    )
    details = (
        "국방부와 한국지능정보사회진흥원은 서울 행사장에서 장병 통합 플랫폼의 "
        "서비스 개시 성과를 공유했다. 이번 사업은 민간 클라우드 기반으로 "
        "분산 운영되던 인사 행정 복지 의료 교육 시스템을 통합했다. "
        "군 가족과 군무원 예비역 입영 대상자에게 필요한 정보를 제공한다. "
        "모바일 신분증을 통해 군마트 이용과 진료비 청구가 가능해졌다. "
        "신규 전자지갑 기능은 종이 증명서를 대체하며 행정 편의를 높인다. "
        "다음 달에는 인공지능 챗봇과 개인별 혜택 안내 서비스가 추가된다. "
        "참석자는 이용 현황을 검토하고 정보 보호 대책을 점검했다. "
    )
    # When
    left_body = left_opening + details
    if short_extract:
        left_body = " ".join(left_body.split()[:80])
    duplicate = have_similar_bodies(left_body, right_opening + details)
    # Then
    assert duplicate is not short_extract
