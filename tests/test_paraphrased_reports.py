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


@pytest.mark.parametrize(
    ("event_day", "venue", "expected"),
    [
        ("28", "피스앤파크컨벤션", True),
        ("29", "피스앤파크컨벤션", False),
        ("28", "부산국제회의장", False),
    ],
)
def test_same_announced_event_survives_independent_reporting(
    event_day: str, venue: str, *, expected: bool
) -> None:
    # Given
    left = (
        "국방 통합 플랫폼이 민간 클라우드를 활용해 새로운 서비스를 준비한다. "
        "군 가족과 장병이 모바일 환경에서 복지 업무를 처리하게 된다. "
        "한국지능정보사회진흥원은 28일 서울 피스앤파크컨벤션에서 "
        "국방부와 장병 통합 플랫폼 성과공유회를 열었다. "
        "참석자들은 지난 사업 운영 결과를 검토했다. "
        "이 시스템은 신분증을 디지털 형태로 전환하는 작업을 지원한다. "
        "기존 인사 행정 복지 의료 교육 등 분산 시스템을 통합했다. "
        "군 가족들도 종이 증명서 없이 모바일 인증을 사용할 수 있다. "
        "입영 대상자와 예비역도 플랫폼을 통해 필요한 정보를 확인한다. "
        "민간 클라우드 도입으로 안정성과 운영 효율성이 개선됐다. "
        "네이버클라우드와 카카오엔터프라이즈가 기반 시설 구축에 참여했다. "
        "다음 달 본격적인 서비스 개시를 앞두고 추가 기능을 검증하고 있다. "
        "관계 기관은 보안과 개인정보 보호를 최우선으로 점검한다. "
    )
    right = (
        "민간 클라우드 기반 장병 통합 플랫폼에 인공지능 비서가 도입된다. "
        "모바일 서비스는 국방부의 행정 업무 처리 방식을 바꿀 전망이다. "
        f"{event_day}일 국방부와 한국지능정보사회진흥원은 서울 "
        f"{venue}에서 장병 플랫폼 성과공유회를 열고 계획을 밝혔다. "
        "앞으로 인공지능이 개인별 복무 상황에 맞는 정보를 먼저 안내한다. "
        "새로운 챗봇은 군 규정과 복지 혜택에 대해 답변한다. "
        "전자지갑의 신분증과 증명서는 인증에 활용된다. "
        "교육 일정과 의료 지원 안내 등도 함께 제공할 방침이다. "
        "군 가족과 예비역을 포함한 이용자가 플랫폼에 접속할 수 있다. "
        "분산 시스템 통합과 개인정보 보호를 동시에 고려했다. "
        "네이버클라우드와 카카오엔터프라이즈는 안정적인 기반 시설을 제공한다. "
        "관계 기관은 서비스 개시 이후에도 실제 이용 결과를 검증한다. "
        "추가 기능은 다음 달 공개하며 보안 점검을 마친 뒤 제공할 계획이다. "
    )
    # When
    duplicate = have_similar_bodies(left, right)
    # Then
    assert duplicate is expected
