# 방위사업청 아침 출근길 DAPA NEWS

방위사업·무기체계·방산수출 관련 공개 뉴스를 매일 수집해 Telegram으로
전송하는 조간 브리핑 자동화 프로젝트입니다.

## 실행

```powershell
$env:PYTHONPATH = "src"
python -m dapa_morning_brief.cli --dry-run
```

`uv`가 설치된 환경에서는 다음 명령을 권장합니다.

```bash
uv sync
uv run dapa-morning-brief --dry-run
```

Telegram 발송에는 환경변수가 필요합니다.

```text
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

여러 대상에 동시에 보내려면 `TELEGRAM_CHAT_ID`에 쉼표로 구분한 값을 넣습니다.

```text
TELEGRAM_CHAT_ID=6015255978,-1004402722342
```

## 기본 동작

- 국방일보 RSS, 방위사업청·국방부 보도자료 게시판, Google News와 선택적 네이버 뉴스 API를 수집원으로 사용합니다.
- 출처와 기사 주제를 분리해 제목·설명에 따라 카테고리를 판정합니다.
- 최근 1일 기사를 우선 수집하고, 검증·중복 제거 후 카테고리별 3건 미만이면 2일까지 보완 검색합니다.
- 섹션별 최대 5건을 선정하되, 동일 사건의 유사 기사는 언론사가 달라도 1건만 남깁니다.
- cron-job.org가 매일 05:40 KST에 `dapa-morning-brief` repository dispatch를
  요청합니다. Actions가 06:00 전에 시작되면 그 시각까지 대기한 뒤 기사를 수집하고,
  06:25를 목표로 최종 Telegram 메시지를 JSON으로 준비합니다.
- 준비가 끝난 Actions는 06:30 KST까지 유지된 뒤 Telegram을 한 번 발송합니다. 06:30
  이후 준비가 끝나면 즉시 발송하며, 실패한 실행은 제한된 횟수만 replacement 실행으로
  복구합니다.
- 날짜별 발송 완료 cache와 concurrency를 사용해 cron-job.org 중복 요청이나 수동
  실행이 발생해도 Telegram 중복 발송을 막습니다.
- 준비 JSON에는 최종 메시지와 생성 건수만 저장하며 기사 본문은 저장하지 않습니다.
- 미발송 Actions 실행은 준비된 JSON을 보관한 채 06:30까지 대기합니다. 이미
  06:30을 지났다면 즉시 한 번 발송합니다. 성공한 날짜는 발송 완료로 기록해 중복
  cron-job.org 요청이나 replacement 실행에서 다시 발송하지 않습니다.
- 과천시·대전시의 당일 날씨는 Open-Meteo Forecast API에서 수집해 메시지 상단에
  표시합니다.
- Open-Meteo KMA Seamless 값이 비어 있으면 기상청 단기예보 API를 우선 사용합니다.
  기상청 예보 API도 장애일 때만 Open-Meteo 자동 모델로 재조회합니다.
- Copilot CLI를 사용할 수 없거나 한도를 초과하면 기존 제목·키워드 기반 실무 참고
  메시지를 사용합니다.
- 기사 전문은 복제하지 않고 제목, 출처, 날짜, 링크 중심으로만 전송합니다.

## 예약 실행

자세한 운영 설정은 [docs/cron-job-org.md](docs/cron-job-org.md)와
[docs/CRON_SETUP.md](docs/CRON_SETUP.md)를 참고하세요.


## 네이버 뉴스 API와 수집 기록

네이버 개발자센터에 애플리케이션을 등록하고 사용 API에서 **검색**을 선택합니다.
GitHub 저장소 Settings → Secrets and variables → Actions → Repository secrets에
다음 두 값을 등록합니다. 키는 소스 코드나 로그에 넣지 않습니다.

- `NAVER_CLIENT_ID`: Client ID
- `NAVER_CLIENT_SECRET`: Client Secret

두 값이 없으면 네이버를 건너뛰고 나머지 수집원을 사용하며 로그에 사유가 남습니다.
네이버 요청은 공식 XML API, 최신순, 검색어별 최대 100건을 사용합니다.
네이버 요청은 최소 1초 간격으로 실행하고, 429 응답은 대기 후 최대 3회 시도합니다.
제한이 지속되면 해당 수집 회차의 나머지 네이버 요청을 중단하고 다른 수집원을 사용합니다.
검색 등록 시각이 원문 발행일과 다를 수 있어 Google과 네이버 모두 원문 날짜를 검증합니다.
원문 날짜를 확인할 수 없는 기사는 제외하며 제외 사유를 로그에 남깁니다.

- [네이버 공식 뉴스 검색 API 문서](https://developers.naver.com/docs/serviceapi/search/news/news.md)
- [키워드·기업 별칭·무기체계 초기 등록부](docs/KEYWORD_CATALOG.md)

운영 Actions는 `DAPA_HISTORY_PATH=.dapa-history/articles.json`을 지정하고
매 실행마다 GitHub Actions cache에서 기록을 복원·저장합니다.
전날·전전날 검증 후보로 수집된 동일 URL 또는 정규화 제목은 제외합니다.
추적용 URL 파라미터는 무시하고, 당일 재시도는 허용합니다.
기사 본문은 기록하지 않습니다. 제목이 다른 재작성 기사는 이력만으로 완전히 식별하지
못하며, 같은 실행의 유사 기사 중복 제거는 기존 본문·제목 비교를 함께 사용합니다.
캐시가 처음 생성되거나 삭제되면 과거 기록을 복구할 수 없으므로 그 실행부터 기록합니다.
수동 미리보기는 운영 기록을 변경하지 않습니다.

전체 수집원이 실패하거나 운영 발송 후보가 최종 0건이면 준비 단계가 실패합니다.
일부 카테고리가 3건 미만이면 보완 검색 후 실제 확보한 기사만 사용하고 부족 건수를
로그에 남깁니다. 관련 없는 기사를 넣어 최소 건수를 강제로 맞추지는 않습니다.
