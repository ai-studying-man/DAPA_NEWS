# PRD: 방위사업 조간 뉴스 텔레그램 봇

## 1. 개요

공개 방위사업 뉴스 RSS를 cron-job.org가 매일 05:40(KST)에 GitHub Actions로 요청하고, Actions가 06:00(KST)에 수집·분류를 시작해 06:25까지 최종 메시지 준비를 목표로 하며, 06:30에 Telegram Bot API 발송을 목표로 하는 조간 브리핑 봇을 구축한다. 실행이 실패하면 60초 뒤 제한된 횟수의 replacement workflow로 복구해 당일 브리핑 발송을 다시 시도한다.

이 봇의 목적은 직원들이 출근길에 방위사업, 무기체계, 방산수출, 국방정책 동향을 빠르게 파악하도록 돕는 것이다. 국내외 출장 중이거나 내부망/내부 시스템에 접근하기 어려운 직원도 공개 출처 기반 동향을 확인할 수 있어야 한다.

## 2. 문제 정의

현재 방위사업 관련 정보는 여러 공식 사이트, 언론사, 보도자료 배포망에 흩어져 있다. 직원이 매일 아침 직접 확인하기에는 시간이 많이 들고, 출장 중에는 내부 시스템 접근이 어려워 정보 공백이 생긴다.

필요한 것은 내부자료를 외부로 전송하는 시스템이 아니라, 공개 출처의 공식성 있는 자료를 자동 수집해 읽기 쉬운 조간 형식으로 재구성하는 시스템이다.

## 3. 목표

- 매일 06:30(KST)에 방위사업 관련 핵심 동향을 텔레그램으로 자동 발송한다.
- 공식 출처를 우선하고, 보조 뉴스/RSS는 키워드 필터와 중복 제거를 거쳐 사용한다.
- 제목·RSS 설명·출처에 `방위사업청` 또는 `방사청`이 명시된 공개 기사는 일반 관련성 필터에서 누락하지 않는다.
- 선택한 원문 기사의 제목, 출처, 발행일, 링크를 변경 없이 제공한다.
- 섹션별로 방위사업청·국방정책, 무기체계·전력화, 방산수출·방산업계 동향을 구분한다.
- 출장 중인 직원도 모바일 텔레그램에서 빠르게 확인할 수 있게 한다.

## 4. 비목표

- 비공개 내부자료, 내부망 문서, 대외비/군사기밀 정보를 수집하거나 전송하지 않는다.
- 기사 전문을 무단 복제하지 않는다.
- 투자 목적의 방산주/테마주 알림 서비스를 만들지 않는다.
- 텔레그램을 내부 결재, 지시, 업무보고 시스템으로 사용하지 않는다.

## 5. 주요 사용자

- 방위사업, 국방정책, 무기체계, 방산수출 동향을 매일 확인해야 하는 직원
- 국내외 출장 중 내부 시스템 접근이 제한되는 직원
- 아침 회의 전 핵심 이슈를 빠르게 파악해야 하는 실무자/관리자

## 6. 핵심 사용 시나리오

1. cron-job.org가 매일 05:40(KST)에 `dapa-morning-brief` repository dispatch를 요청한다.
   Actions가 06:00 전에 시작되면 06:00까지 대기한 뒤 RSS 조회와 날씨 수집을 시작한다.
2. 최근 24~72시간 기사 중 방위사업 관련성이 있는 항목과 방사청 필수수집 기사를 남긴다.
3. 동일 URL, 유사 제목, 동일 연재 머리말, 핵심 개체·사건, RSS 설명 유사도를 이용해 중복 기사를 하나의 스토리로 묶는다.
4. 중복 스토리에서는 실제 조회수가 가장 높은 원문 기사 1건을 남기고 주식/테마주성 기사를 제거한다. 조회수가 없을 때만 노출순위, 공식성, 최신성을 사용한다.
5. 규칙 기반으로 섹션을 분류하며 기사 제목과 내용을 요약·합성·재작성하지 않는다.
6. 06:25(KST)을 목표로 최종 Telegram 메시지 JSON 준비를 완료한다. 목표 시각을 넘겨도 준비를 계속한다.
7. 같은 Actions 실행이 06:30(KST)에 Telegram Bot API를 한 번 호출한다. 이미 목표 시각을 넘겼다면 즉시 호출하고, 실패하면 60초 뒤 replacement workflow가 전체 실행을 다시 시작한다.
8. 사용자는 출근길 또는 출장 중 모바일에서 핵심 동향과 원문 링크를 확인한다.

## 7. 정보 출처 우선순위

### 7.1 1순위: 공식 정부 원천

| 출처 | 용도 | RSS |
|---|---|---|
정책브리핑 및 국방부 RSS는 사용하지 않는다. 공식 보도자료 섹션도 발행하지 않으며, 현재 운영 수집원은 국방일보 방위사업 RSS와 Google News RSS다.

### 7.2 2순위: 국방 전문 준공식 소스

| 출처 | 용도 | RSS |
|---|---|---|
| 국방일보 국방안보 | 국방·안보 일반 | `http://kookbang.dema.mil.kr/dema_xml/dema0010010000.xml` |
| 국방일보 방위사업 | 방위사업 기사 | `http://kookbang.dema.mil.kr/dema_xml/dema0010020000.xml` |
| 국방일보 군사 | 군사 기획/해설 | `http://kookbang.dema.mil.kr/dema_xml/dema0020010000.xml` |
| 국방일보 국군 무기도감 | 무기체계 배경 정보 | `http://kookbang.dema.mil.kr/dema_xml/dema0020010033.xml` |

### 7.3 3순위: 보조 보도자료/뉴스 소스

| 출처 | 용도 | RSS |
|---|---|---|
| 뉴스와이어 방위산업 | 방산 기업/기관 보도자료 | `https://api.newswire.co.kr/rss/industry/418` |
| 뉴스와이어 항공우주 | 항공우주·무기체계 관련 | `https://api.newswire.co.kr/rss/industry/407` |
| 뉴스와이어 드론 | 무인체계 관련 | `https://api.newswire.co.kr/rss/industry/620` |
| 뉴스와이어 중앙정부 | 정부 보도자료 보조 | `https://api.newswire.co.kr/rss/industry/1407` |
| 뉴스와이어 공공기관 | 공공기관 발표 보조 | `https://api.newswire.co.kr/rss/industry/1409` |
| 뉴시스 정치 | 국방·정책 보조 기사 | `https://www.newsis.com/RSS/politics.xml` |
| 뉴시스 산업 | 방산업계 보조 기사 | `https://www.newsis.com/RSS/industry.xml` |
| 연합뉴스TV 정치 | 국방·정책 방송 기사 | `http://www.yonhapnewstv.co.kr/category/news/politics/feed/` |

### 7.4 Google News RSS의 위치

Google News RSS는 누락 보완용으로만 사용한다. 공식성과 재현성을 높이기 위해 기본값은 공식 RSS와 보조 RSS를 먼저 사용하고, 결과가 부족할 때만 Google News RSS 검색어를 추가한다.

## 8. 분류 체계

### 8.1 방위사업청·국방정책

- 방위사업청, 국방부, 국방조달, 획득, 방위력개선사업, 예산, 제도, 계약, 부처 발표

### 8.2 무기체계·전력화

- 무기체계 개발, 시험평가, 양산, 전력화, 국방과학연구소, 국방기술품질원, 국방기술진흥연구소
- KF-21, K2, K9, L-SAM, M-SAM, 유도무기, 무인기, 함정, 항공, 지상장비

### 8.3 방산수출·방산업계

- K-방산, 방산수출, 해외 계약, 국제협력, 한화에어로스페이스, 현대로템, 한국항공우주, LIG넥스원 등

## 9. 필터링 기준

### 기관 필수수집 규칙

- 제목, RSS 설명 또는 출처에 `방위사업청` 또는 `방사청`이 명시된 공개 기사는 일반 관련성 점수와 섹션별 상한을 적용하기 전에 후보군에 보존한다.
- 기관 필수수집 기사는 투자성·비공개 정보·유효하지 않은 URL 등 안전 필터를 제외하고 일반 키워드 부족만으로 제거하지 않는다.
- 기관 필수수집은 후보 수집 보장을 뜻한다. 동일 사건을 반복 보도한 기관 관련 기사에는 중복 제거를 적용하고 공식 원출처 1건을 대표로 남긴다.
- Google News의 `"방위사업청" OR "방사청"` 전용 쿼리와 섹션별 쿼리를 독립적으로 실행해 누락을 보완한다.

### 포함 키워드

```text
방위사업청, 방사청, 방위사업, 방위력개선, 국방획득, 국방조달,
무기체계, 전력화, 시험평가, 양산, 국방과학연구소, ADD,
국방기술품질원, 국방기술진흥연구소, K-방산, 방산수출,
KF-21, K2, K9, L-SAM, M-SAM, 유도무기, 무인기, 항공우주
```

### 제외 키워드

```text
방산주, 수혜주, 테마주, 상한가, 급등, 급락, 증시, 목표가,
매수의견, 리포트, 관련주, 투자전략
```

## 10. 기능 요구사항

### FR-1. RSS 수집

- 등록된 RSS 피드를 GitHub Actions가 매일 06:00(KST)에 조회하기 시작한다. 시작 요청은
  cron-job.org의 05:40(KST) `repository_dispatch`로 전달된다.
- 각 항목에서 제목, 링크, 발행일, 출처, RSS 설명을 추출한다.
- RSS 응답 실패 시 해당 피드만 실패 처리하고 전체 작업은 계속 진행한다.

### FR-2. 날짜 필터

- 기본 수집 기간은 최근 24시간이다.
- 월요일 또는 휴일 다음날에는 최근 72시간까지 확장할 수 있다.
- 기사 수가 부족하면 3일, 최대 5일까지 재시도한다.

### FR-3. 중복 제거

- 동일 URL은 1건만 남긴다.
- 추적 파라미터와 Google News 중간 URL을 정규화한 canonical URL이 같으면 1건만 남긴다.
- 언론사 접미사, 특수문자, 조사, 공백을 제거한 정규화 제목이 같으면 1건만 남긴다.
- `[불붙는 KAI 인수전]`처럼 동일한 괄호형 연재 머리말을 공유하고 핵심 개체·사건이 같으면 하나의 스토리 클러스터로 묶는다.
- 제목과 RSS 설명에서 `기업/기관 + 대상 + 행위` 사건 지문을 만들고, 제목·설명 유사도가 임계값 이상이면 동일 사건으로 판정한다.
- `조성`, `출범`, `구축`, `업무협약`처럼 표현이 달라도 긴 사업 주제어가 같으면 동일 사업 이벤트 후보로 판정한다.
- 사업명 별칭을 정규화하되 긴 주제어와 양쪽 사건 행위가 함께 확인될 때만 병합한다.
- 단순히 `K2`, `KAI`, `방위사업청` 같은 공통 키워드 하나만 같다는 이유로 합치지 않는다.
- 같은 이슈가 여러 언론에 반복 보도된 경우 실제 조회수가 제공되면 조회수가 가장 높은 원문 기사 1건을 선택한다.
- 실제 조회수가 없으면 RSS/Google News 노출순위, 공식성, 최신성 순으로 원문 기사 1건을 선택하며 조회수를 추정하거나 생성하지 않는다.
- 중복 제거 후 유효 기사가 있으면 각 섹션에 최대 5건까지 제공한다.
- 선택된 기사의 제목과 URL을 그대로 사용하고 여러 기사 제목·내용을 축약·합성·재작성하지 않는다.
- 중복 판정 결과에는 대표 기사, 제외 기사, 판정 근거와 점수를 로그로 남긴다.

### FR-4. 관련성 판정

- 제목·RSS 설명·출처에 `방위사업청` 또는 `방사청`이 명시된 유효 기사는 기관 필수수집 후보로 판정한다.
- 포함 키워드가 제목 또는 설명에 포함된 기사를 우선한다.
- 제외 키워드가 포함된 주식/투자성 기사는 제외한다.
- 애매한 기사는 규칙 기반 관련성 판정에서 제외할 수 있다.
- 현 정부 뉴스는 `직위자/정부 + 방산/국방`과 `대통령/대통령실/정부 + 주요 국정행위` 검색 쿼리로 수집하고 제목·RSS 설명·출처를 함께 분류한다.
- 특정 인물명에 의존하지 않고 제목의 행위 주체가 대통령·대통령실·정부인지, 업무보고·국무회의·국정과제·국정성과 문맥이 이어지는지를 함께 판정한다.
- 일반적인 `정부 + 기본법/시행령` 기사에는 대통령 주체 또는 국방 문맥이 없으면 제외한다.
- 기본 수집 기간에 일부 섹션만 비어 있으면 보강 기간을 재조회하되, 이미 채워진 섹션은 교체하지 않고 비어 있던 섹션만 보강한다.
- `정부 + 드론/AI`처럼 일반 산업에도 쓰이는 조합은 국방부·군·방위사업·방산 등 국방 앵커가 없으면 제외한다.

### FR-5. 원문 보존

- 기사 전문을 새로 작성하거나 여러 기사 내용을 결합하지 않는다.
- 선택된 기사의 원문 제목, 출처, 발행일, URL을 그대로 전달한다.
- RSS 설명은 중복 판정에만 사용하고 텔레그램용 기사 내용으로 생성하지 않는다.

### FR-6. 텔레그램 발송

- `pyTelegramBotAPI`의 `telebot.TeleBot`을 사용한다.
- 실무 참고는 섹션별 고정 문구가 아니라 기사 제목과 RSS 설명에 확인되는 사건 유형으로 선택한다.
- 규격·특허, 클러스터, 시험평가, 양산, 공급망, 수출계약, 제도·예산, AI·무인체계 등 확인 가능한 신호만 사용한다.
- 실무 참고는 담당자가 확인할 항목을 제시하며 원문에 없는 사실·성과·일정을 생성하지 않는다.
- 정기 발송에는 polling이 필요하지 않으며, `send_message(chat_id, text, parse_mode="HTML")` 형태로 전송한다.
- 메시지가 Telegram 길이 제한을 넘으면 섹션 단위로 분할 발송한다.
- 채널 발송 시 봇을 채널 관리자로 추가해야 한다.

### FR-7. 운영 알림

- 수집 결과가 0건이면 "오늘 수집된 공개 방위사업 관련 기사가 없습니다"를 발송한다.
- 발송 실패 시 job을 실패 처리하고 로그를 남긴 뒤 60초 후 replacement workflow를 요청한다.
- 발송 성공 시 날짜별 완료 상태를 저장하고 이후 실행에서는 Telegram API를 호출하지 않는다.
- 매일 발송 결과를 로컬 로그 또는 GitHub Actions 로그에 남긴다.

## 11. 비기능 요구사항

- 보안: 봇 토큰과 텔레그램 chat_id는 `.env` 또는 GitHub Secrets에 저장한다.
- 개인정보: 수신자 개인 전화번호나 계정 정보를 저장하지 않는다.
- 기밀성: 공개 RSS와 공개 뉴스만 사용한다. 내부자료는 입력하지 않는다.
- 안정성: 일부 RSS가 실패해도 나머지 피드로 브리핑을 생성한다.
- 재현성: RSS URL, 키워드, 중복 판정 기준, 실행 시간을 코드/설정으로 관리한다.
- 확장성: 향후 Slack, 이메일, Notion, 사내 포털로 발송 채널을 추가할 수 있게 모듈화한다.

## 12. 권장 기술스택

### 언어/런타임

- Python 3.11 이상

### RSS/HTTP

- `feedparser`: RSS/XML 파싱
- `httpx`: HTTP 요청, timeout, retry 처리

### 텔레그램

- `pyTelegramBotAPI`: `telebot` 기반 텔레그램 발송
- Telegram Bot API: BotFather로 토큰 발급, `sendMessage` API 사용

### 스케줄링

- 운영 스케줄의 단일 기준은 cron-job.org의 매일 05:40 KST 요청이다.
- cron-job.org는 `dapa-morning-brief` repository dispatch를 호출하고, Actions는
  06:00 KST까지 대기한 뒤 수집을 시작한다.
- 준비 명령과 Telegram 발송은 production job당 각각 한 번만 시도한다.
- 어느 단계든 production job이 실패하면 60초 뒤 replacement 실행을 요청하며, replacement는
  최대 5회로 제한한다.
- Telegram 발송에 성공한 날짜는 완료 상태로 기록하고 이후 실행에서는 발송하지 않는다.
- 06:25는 준비 완료 목표로 기록하고, 06:30 이전에 준비되면 해당 시각까지 대기한다.
- 06:30 이후에 준비되면 즉시 Telegram Bot API를 호출한다.
- 수동 Actions 실행은 기존 입력에 따라 미리보기 또는 명시적 재발송을 수행한다.

주의: GitHub Actions 자체 schedule은 사용하지 않는다. cron-job.org가 workflow 시작을 담당하고,
이미 시작된 Actions의 Python/API/Telegram 실패만 60초 뒤 최대 5회 replacement workflow로
복구한다. 한 production job 안에서 준비나 Telegram 발송을 반복하지 않는다. production job은
최대 120분 실행한다.

### 기사 처리

- 결정론적 키워드 필터, 중복 판정, 원문 기사 순위 규칙을 사용한다.
- 기사 제목이나 본문을 생성하는 LLM 단계는 두지 않는다.

### 설정/비밀값

- 로컬: `.env`
- GitHub Actions: Repository Secrets
- 필수 환경변수:

```text
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TZ=Asia/Seoul
```

## 13. 시스템 아키텍처

```text
cron-job.org(05:40 KST)
  -> repository_dispatch(dapa-morning-brief)
  -> Wait Until Collection Target(06:00 KST)
  -> RSS Collector
  -> Normalizer
  -> Keyword Filter
  -> Deduplicator
  -> Ranker
  -> Rule-based Classifier
  -> Telegram Formatter
  -> One Preparation Attempt
  -> Preparation Target Check(06:25 KST)
  -> Wait Until Send Target When Early(06:30 KST)
  -> One Telegram Send Attempt(immediate when late)
  -> Failed Run Re-dispatch(after 60 seconds)
  -> Logs
```

## 14. 메시지 포맷

```text
방위사업 조간 브리핑 - YYYY.MM.DD

1. 방위사업청·국방정책
1) 기사 제목
- 출처 / 발행일
- 링크

2. 무기체계·전력화
...

3. 방산수출·방산업계
...

#방위사업청 #방위사업 #무기체계 #K방산 #국방정책
```

Telegram HTML 모드 사용 시 예:

```html
<b>방위사업 조간 브리핑 - 2026.06.12</b>

<b>1. 방위사업청·국방정책</b>
1) <a href="ARTICLE_URL">기사 제목</a>
- 출처 / 발행일
```

## 15. 원문 처리 정책

- 입력된 기사 제목과 URL은 수정하지 않는다.
- 서로 다른 기사 제목이나 설명을 합쳐 새로운 제목·본문·요약을 만들지 않는다.
- RSS 설명은 관련성 및 중복 판정에만 사용하고 발송 메시지에 기사 내용으로 재작성하지 않는다.
- 텔레그램 HTML 변환은 이스케이프와 링크 태그 적용만 수행한다.

## 16. 텔레그램 연동 설계

### 16.1 BotFather 준비

1. Telegram에서 `@BotFather`를 연다.
2. `/newbot`으로 봇을 생성한다.
3. 발급된 bot token을 `TELEGRAM_BOT_TOKEN`에 저장한다.
4. 발송 대상이 채널이면 봇을 채널 관리자로 추가한다.
5. 발송 대상이 단체방이면 봇을 초대한 뒤 chat_id를 확인한다.

### 16.2 발송 코드 개념

```python
import os
import telebot

bot = telebot.TeleBot(os.environ["TELEGRAM_BOT_TOKEN"], parse_mode="HTML")
bot.send_message(
    chat_id=os.environ["TELEGRAM_CHAT_ID"],
    text=message,
    disable_web_page_preview=False,
)
```

정기 발송만 필요하면 `bot.infinity_polling()`은 사용하지 않는다. `/start`, `/latest`, `/help` 같은 대화형 명령을 지원할 때만 polling 또는 webhook을 추가한다.

## 17. 스케줄링 설계

### 17.1 GitHub Actions 운영 기준

```yaml
on:
  repository_dispatch:
    types: [dapa-morning-brief, dapa-morning-brief-retry]
  workflow_dispatch:
```

cron-job.org의 05:40 요청이 primary trigger다. Actions는 날짜별 발송 캐시를 먼저 확인하고,
미발송이면 06:00까지 대기한 뒤 준비 CLI와 Telegram API를 각각 한 번씩만 호출한다. 어느
단계든 실패하면 `GITHUB_TOKEN`으로 `dapa-morning-brief-retry` repository dispatch를 60초
뒤 요청하며 replacement 실행은 최대 5회다. 각 production job은 최대 120분 실행한다.

성공한 `scheduled-brief` job은 06:30 이전이면 해당 시각까지 대기한 뒤 Telegram Bot API를 한 번 호출한다. 06:30을 넘겼다면 즉시 한 번 호출한다. 호출 실패는 job 실패로 처리해 replacement workflow가 전체 실행을 다시 시작한다. 호출 성공 후에는 날짜별 완료 캐시를 저장하며 이후 요청이나 replacement 실행에서는 발송하지 않는다. Telegram 비밀값은 이 production job에만 주입한다. 사용자가 실행하는 `workflow_dispatch`는 기존 입력에 따라 preview 또는 명시적 resend를 수행한다.

Windows 작업 스케줄러, Linux cron, Hermes Cronjob에는 별도 운영 발송 일정을 등록하지 않는다. cron-job.org 이외의 중복 스케줄은 단일 기준을 깨뜨리고 불필요한 workflow 실행을 만들 수 있다.

## 18. 데이터 모델

```json
{
  "title": "기사 제목",
  "url": "https://example.com/article",
  "published_at": "2026-06-12T06:30:00+09:00",
  "source": "정책브리핑 방위사업청",
  "feed_url": "https://www.korea.kr/rss/dept_dapa.xml",
  "description": "RSS 설명",
  "section": "방위사업청·국방정책",
  "priority": 1,
  "canonical_url": "https://example.com/article",
  "is_agency_article": true,
  "agency_match_field": "title",
  "story_cluster_id": "kai-acquisition-2026-07"
}
```

## 19. 성공 지표

- 매일 06:30(KST) 목표 시각 내 Telegram API 호출 성공률 95% 이상
- 지연·일시 실패 발생 시 당일 Telegram API 최종 호출 성공률 99% 이상
- 공식/준공식 출처 비중 70% 이상
- 중복 기사 포함률 2% 이하
- 서로 다른 사건 오병합률 1% 이하
- 접근 가능한 필수 수집원과 기관 전용 쿼리 기준 방사청 기사 후보 수집 누락률 0%
- 주식/테마주성 기사 포함률 5% 이하
- 브리핑 1회당 읽는 시간 3분 이하

## 20. 운영 리스크와 대응

| 리스크 | 대응 |
|---|---|
| RSS 주소 변경 | 피드별 실패 로그와 주 1회 점검 |
| 기사 부족 | 기간을 3~5일로 확장하고 부족 사실 명시 |
| 동일 기획·연재 기사 반복 | 연재 머리말과 핵심 개체·사건으로 클러스터링하고 대표 기사 1건만 선정 |
| 방사청 기사 누락 | 필수 RSS와 기관 전용 쿼리를 독립 실행하고 후보 수·실패 상태를 기록 |
| 과도한 중복 제거 | 실제 발송본 회귀 데이터셋으로 서로 다른 사건 오병합률을 함께 측정 |
| Telegram 토큰 유출 | `.env`/Secrets 사용, 유출 시 BotFather에서 토큰 재발급 |
| 비공개 정보 혼입 | 공개 RSS만 입력으로 사용, 내부자료 업로드 금지 |
| 원문 왜곡 | 선택한 기사의 원문 제목과 URL을 그대로 사용하고 요약·합성·재작성 금지 |
| 외부 요청·Actions 실패 | cron-job.org가 05:40에 primary dispatch를 요청하고, 시작된 workflow의 실패는 60초 뒤 최대 5회 replacement로 복구하며 06:30 이후에는 즉시 1회 발송 시도 |

## 21. MVP 범위

1. RSS 피드 설정 파일 작성
2. RSS 수집 및 표준 JSON 변환
3. 키워드 포함/제외 필터
4. URL·제목·연재 머리말·사건 지문·RSS 설명 기반 중복 제거
5. 규칙 기반 분류 및 원문 제목·URL 보존
6. Telegram HTML 메시지 생성
7. 06:30(KST) 스케줄 발송
8. 실행 로그 저장
9. 방사청 필수수집 경로와 누락 감시
10. 실제 발송본 기반 중복 회귀 테스트

## 22. 향후 확장

- `/latest` 명령으로 최근 브리핑 재발송
- `/source` 명령으로 사용 중인 RSS 목록 확인
- 관리자 전용 `/test_send` 명령
- 중요도 높은 공식 발표 발생 시 즉시 알림

## 23. 참고 문서

- 구현 작업 목록: [`../TODOLIST.md`](../TODOLIST.md)
- Telegram Bot API: https://core.telegram.org/bots/api
- Telegram BotFather Tutorial: https://core.telegram.org/bots/tutorial
- pyTelegramBotAPI: https://github.com/eternnoir/pyTelegramBotAPI
- 정책브리핑 RSS: https://www.korea.kr/etc/rss.do
- 국방일보 RSS 안내: https://kookbang.dema.mil.kr/newsWeb/rss.do
- 뉴스와이어 RSS: https://www.newswire.co.kr/?md=A31
