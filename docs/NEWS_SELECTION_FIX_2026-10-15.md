# 뉴스 선택 로직 보완 및 무발송 검증 — 2026-10-15

## 범위와 결론

오늘 실제 발송본(run38634029133, 운영 SHA a507a8ac12f61b8b0197bb5b65850fa335a460ac)의 중복·반복·오분류를 재현하고 보완했다. 텔레그램 발송·워크플로 재실행·LLM 호출은 하지 않았다. 기존 최소3/최대5건 카테고리 제한과 발송 체계는 변경하지 않았다.

## 수정 내용

- `dated_agreement_evidence.py`: 도입부에서 확인한 협약 사건일·당사자·장비·구체 주제 근거를 비교한다. 단순히 같은 무기를 언급한다는 이유로 합치지 않는다. 다른 상대방/장비/사건일/확인 가능한 장소는 별개로 유지한다. 계약·납품·시험·승인·시설 완공 같은 새 단계와 독립 분석은 새 협약 중복 규칙으로 제외하지 않는다. 도시 한영 별칭은 제한된 사전이며 전 세계 장소를 모두 식별하는 기능은 아니다.
- `story_deduplication.py`: 본문 문장이 다르게 재작성됐더라도 높은 확신의 동일 협약 근거가 있으면 같은 날 대표1건을 고른다. 기존 비행·개소·인사 사건 비교는 유지한다.
- `article_history.py`: 본문 대신 압축 사건 근거를 선택된 기사에만 저장하고 최근7일과 비교한다. 기존 URL/제목의 직전2일 비교는 유지한다. 모든 종류의 기사를 의미적으로7일 비교하는 변경은 아니며, 새 이력 근거는 날짜가 확인되는 협약 사건에 한정한다.
- 기존 캐시 전환: 사건 근거가 없는 최근7일 이력 중 협약·자매결연 등 후보의 원문만 기존 수집기로 다시 읽는다. 원래 수집일/URL/제목을 보존하며, 본문 미확보·의견성 제외·사건 근거 부족이면 추측해서 제외하지 않는다. 이미 사건 근거가 있는 이력과 당일·미래·기간 밖 이력은 재조회하지 않는다. 과거 발행시각은 없으므로 수집일을 날짜 해석의 대용으로 사용하며, 명시적인 사건일이 확인돼야 한다.
- `selection_pipeline.py`, `cli.py`: 원문 읽기 후 사건 이력을 대조하고 최종 정원 전에 제외하여 다른 후보로 채운다. 최종 선정 기사만 이력에 기록한다. 기존 공유 수집 인터페이스는 `body_fetcher.py`로 이동해 순환 참조를 없앴다.
- `article_selection_review.py`: 제목·도입부가 뒷받침하는 주된 정부 행위가 분류 불확실 반환보다 먼저 적용되도록 했다. 기사 말미의 회사 이름만으로 기업동향이 되지 않으며, 분류가 불확실하다는 이유로 정상 기사를 일괄 삭제하지 않는다.

## 실패 우선 회귀 증거

|사례|수정 전|수정 후|
|---|---|---|
|비궁 협약 재작성/본문 다른 배경|동일 사건 False, 사건 이력 bodies API 없음: 관련2실패|동일 사건 True|
|정부/국방 주제 보정|새 테스트3실패·정상 대조5통과|8통과|
|본문 후 이력 대조/보충|CandidateSelection.inspect history 인수 없음:1실패|2통과|
|기존 캐시 원문 보충|hydrate_recent_history API 없음:1실패|기존 이력 자동 보충 후 재작성 반복 제외|
|같은 날·회사·장비, 다른 확인 장소|True로 잘못 합침:1실패|False로 유지|

새 회귀 파일: test_dated_event_deduplication.py, test_primary_government_review.py, test_history_selection_pipeline.py, test_history_hydration.py. 다른 상대 기업·다른 무기·다른 사건일·신규 계약·납품·시험·승인·시설 완공·독립 분석·분류 불확실 정상 기사·본문 미확보·기존 캐시 호환을 포함한다.

## 오늘 실제 기사20건 재검증

자료는 실제 발송 준비본의 제목/URL/원래 카테고리와 Actions selected 로그의 발행시각을 사용했다. 원문20건을 **운영 fetch_article_bodies / extract_main_text**로 다시 읽어 스냅숏으로 주입했다. 원문 내용은 감사 시점 것이므로 발송 순간과 수정 차이가 있을 수 있다. 원래 검색 결과의 전체 description과 원천 source 우선순위는 준비본에 없어 재현하지 못했다. 새 검색 결과를 임의로 오늘 발송분이라고 대체하지 않았다.

- [굿모닝충청 비궁](https://www.goodmorningcc.com/news/articleView.html?idxno=453988) / [동아일보 비궁](https://www.donga.com/news/amp/all/20261014/134843592/1): 10/13 워싱턴 AUSA·LIG D&A–Firehawk·2.75인치 비궁 추진체 TA의 같은 사건. 대표1건만 남음.
- [성남시 CNB](https://www.cnbnews.com/news/articleView.html?idxno=1019123) / [전일 컨슈머타임스](https://www.cstimes.com/news/articleView.html?idxno=723828): 10/8~11 방문·협약·학교 사격훈련 시스템 도입 논의 반복. 현재 반복 제외.
- [미 국방차관 기사](https://www.asiatoday.co.kr/kn/view.php?key=20261015010004581): 무기체계에서 정부/국방으로 이동, 기사 보존. 정부 섹션이므로 기존의 무기체계 일반 실무참고 템플릿도 붙지 않음.
- [국회 지뢰도발 결의안](https://www.ksilbo.co.kr/news/articleView.html?idxno=1069595): 기업동향에서 정부/국방으로 이동, 기사 보존.
- [TMMR 창고 방치](https://news.kbs.co.kr/news/pc/view/view.do?ncd=8686063&ref=A)와 [별개 전투원용무전기 구매사업](https://www.news2day.co.kr/article/20261014500388)은 서로 다른 사업/쟁점으로 둘 다 보존.
- 광주 군공항 방문과 지작사 방문은 다른 장소/임무로 모두 관련성 판정 accepted 유지. 후자는 정부 카테고리 정원 때문에 최종 출력에서 밀린 것이지 중복/무관으로 제외된 것이 아님.
- [KAI 종합 기사](https://www.webeconomy.co.kr/news/articleView.html?idxno=2335002)는 기존 비행 외 위성시설 등 추가 내용을 포함하여 일괄 중복 삭제하지 않음.

### 실제 CLI 무발송 재현

`cli.main(["--dry-run", "--fallback-days", "1"])`을 실행하고 수집/본문 경계에 위 실측20건과 전일 실측 본문을 주입했다. 실제 분류·중복·이력·신선도·정원·메시지 생성 경로를 사용했다. 날씨는 이번 검증 범위 밖이라 빈값으로 주입했고, LLM·발송·이력 쓰기는 호출 감시로0회를 확인했다. 원래20건만 넣은 재현이므로 보충 가능한 전체 검색 후보를 포함하지 않는다.

```text
SELECTED government 5 [11,18,1,2,3]
SELECTED policy 5 [6,7,8,9,10]
SELECTED weapon_system 3 [12,13,14]
SELECTED export_business 3 [16,17,20]
CLI_EXIT 0 LLM_CALLS 0 TELEGRAM_CALLS 0 HISTORY_WRITES 0
CLI_LINKS 16
```

16건은 정원 설정을 줄인 결과가 아니다. 중복 대표1건·전일 반복1건과 정부 정원 초과2건을 제외한 제한 입력 재현 결과다. 분류 전후 정상 대조의 관련성 유지도 별도로 확인했다.

사건 근거를 미리 만들어 넣지 않은 **기존 캐시 그대로의 첫 실행**도 별도 검증했다. 전일 이력 event=None에서 시작해 협약 후보 원문1건을 보충하고 같은16건 결과를 얻었다.

```text
LEGACY_FIRST_RUN_QA_PASS CLI_EXIT=0 links=16 historical_reads=1 LLM=0 TELEGRAM=0 history_writes=0
SECTIONS=5/5/3/3; prior_semantic_event_initially=None; SeongnamRepeatExcluded=True
PoniardRepresentativeCount=1; DifferentRadioProjectsRetained=True; GovernmentCorrections=2; MixedKAIKept=True
```

## 검증 한계와 별도 잔여사항

- 네이버 키가 필요한 새 원격 수집/미래 발송은 실행하지 않았다. 준비본·실측 원문을 경계에 주입한 오늘 기사 재현이지 내일 운영 성공의 보증은 아니다.
- 뉴스1 인터뷰는 운영 추출에서도57자 부제 수준이다. 본문 미확보 문제와 뉴스투데이 의견성 진단 기사의 편집 정책은 이번 세 가지 수정과 별개로 남는다. 전체 기사가 완전히 검증됐다고 주장하지 않는다.
- 과거 원문이 없어졌거나 장소/당사자/날짜 근거가 부족하면 의미 중복을 확정하지 않는다. 정상 기사 보존을 우선하므로 모든 재작성 중복을100% 제거하지는 못한다.
- CLI235 / story_deduplication227 pure LOC는200~250 경고 구간이다. 이번 변경은 작은 연결 수정이며250을 넘지 않는다. 다음 확장 시 실행 준비와 사건 비교 책임을 먼저 분리한다. 나머지 변경 모듈은200 이하.
- 전역 format --check는 기존 미수정 파일12개도 재포맷 대상으로 보고했다. 해당 사용자/기존 파일은 변경하지 않고 이번 변경 파일만 형식을 정리했다.

## 최종 품질 게이트

```text
568 passed, 52 subtests passed in 15.79s
ruff check src tests: All checks passed!
basedpyright: 0 errors, 0 warnings, 0 notes
ruff format --check <변경11파일>: 11 files already formatted
check-no-excuse-rules.py <변경11파일>: no violations in 11 file(s)
FINAL_ACTUAL20_CLI_PASS exit=0 sections=5/5/3/3 links=16 legacy_hydration_reads=1 LLM=0 Telegram=0 HistoryWrites=0
```

변경 모듈별 책임은 사건 근거 비교/선택 이력/분류 보정/수집 인터페이스/선택 연결로 나뉘며, 외부 이력은 frozen Pydantic 모델로 파싱한다. 새로운 Any·cast·타입 무시·광범위 예외 삼키기는 없다. 공개 docstring은 수집 및 이력 계약, 테스트 주석은 Given/When/Then 구분에 필요한 것이다. 임시 디버깅 스냅숏과 저널은 위 근거를 기록한 뒤 제거했으며 기존 사용자 파일과 오늘 감사 보고서는 그대로 보존했다.

구현 커밋: `de97fd2`(정부 분류 보정), `20973f5`(동일 협약·발송 이력 보완). 위 게이트는 두 변경을 모두 포함한 코드에 대해 실행했다.
