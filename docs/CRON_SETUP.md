# 방산출근길 예약 실행 구성

## 실행 시간

목표 발송 시간은 매일 06:30 KST입니다.

- cron-job.org 요청: 매일 05:40 KST
- repository dispatch: `dapa-morning-brief`
- GitHub Actions는 06:00 전 시작 시 그 시각까지 대기한 뒤 뉴스·날씨·실무 참고 메시지를 준비합니다.
- 06:25 KST는 준비 완료 목표입니다.
- 준비 명령과 Telegram 발송은 Actions 실행당 각각 한 번만 시도합니다.
- 어느 단계든 실패해 job이 실패하면 60초 뒤 제한된 횟수의 replacement 실행을 요청합니다.
- 준비된 최종 메시지는 JSON으로 저장하며 기사 본문은 저장하지 않습니다.
- 같은 Actions 실행이 06:30까지 대기한 뒤 Telegram Bot API를 호출합니다.
- 이미 06:30을 지났다면 대기하지 않고 즉시 Telegram Bot API를 호출합니다.

## 필수 환경변수

```text
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TZ=Asia/Seoul
```

`TELEGRAM_CHAT_ID`는 쉼표로 구분해 여러 수신 대상을 지정할 수 있습니다.

```text
TELEGRAM_CHAT_ID=6015255978,-1004402722342
```

BotFather에서 Telegram bot token을 만들고, 봇을 채널 또는 단체방에 추가한 뒤
`TELEGRAM_CHAT_ID`를 설정합니다.

## 로컬 검증

```powershell
$env:PYTHONPATH = "src"
python -m dapa_morning_brief.cli --dry-run
```

실제 Telegram 발송 전에는 반드시 `--dry-run`으로 메시지 형태를 확인합니다.

## GitHub Actions

운영 스케줄의 단일 기준은 cron-job.org입니다. `.github/workflows/dapa-morning-brief.yml`은
`repository_dispatch`를 받아 production job을 실행합니다.

cron-job.org가 05:40 KST에 `dapa-morning-brief` 이벤트를 요청합니다. 각 production job은
준비 명령과 Telegram API를 한 번씩만 호출합니다. checkout·환경설정·준비·발송 중 어느
단계든 실패하면 `dapa-morning-brief-retry` 내부 이벤트를 60초 뒤 발생시켜 새 workflow
실행을 요청합니다. replacement 실행은 최대 5회로 제한하며, production job은 120분,
retry job은 15분 실행 한도를 사용합니다.

성공한 실행은 먼저 날짜별 발송 cache를 확인합니다. 이미 발송된 날이면 06:00 대기와
뉴스 수집을 건너뛰고 종료합니다. 미발송이면 `.dapa-prepared/morning-brief.json`을
생성하고 06:30까지 대기한 뒤 Telegram으로 전송합니다. production job은 공통 concurrency
group과 날짜별 발송 cache를 사용하므로 중복 요청이 발생해도 중복 발송하지 않습니다.
준비가 지연되어 06:30을 넘기면 준비가 끝나는 즉시 한 번 발송합니다. Telegram 호출이
실패하면 해당 job을 실패 처리하고 replacement workflow가 전체 실행을 다시 시작합니다.
Telegram 발송에 성공한 날짜는 완료 캐시에 기록하므로 이후 실행은 발송 단계를
건너뜁니다.

사용자가 실행하는 `workflow_dispatch`는 기존 입력에 따라 preview 또는 명시적 resend를
수행합니다. `dapa-morning-brief` repository dispatch는 production `scheduled-brief`로
연결되고, `dapa-morning-brief-retry`는 자동 복구용입니다.

과천시·대전시 당일 날씨는 KMA 단기예보 연결 프록시를 우선 사용하고, 실패하면
Open-Meteo 자동 모델로 재조회합니다. 업데이트가 중단된 KMA Seamless 모델은
호출하지 않습니다. 자동 모델의 일시적인 네트워크 오류·429·5xx는 최대 3회
시도하며 도시·제공자·실패 유형을 기록합니다. 대체 예보는 기상청 단독 데이터가
아닙니다. 모든 경로가 실패한 지역은 `수집 실패`로 표시하고 뉴스 발송은 계속합니다.

`DAPA_NEWS_TRACE=1`이면 검색 항목별 파싱 결정과 수집·검증·최종 선정 단계의
제목 및 발행 시각을 기록합니다. 본문과 인증 정보는 추적 로그에 저장하지 않습니다.
`--dry-run`도 실제 발송과 같은 본문 기반 중복 검사를 수행하되 요약 모델과
Telegram을 호출하지 않습니다. 기존 Actions 수동 preview는 Copilot 요약까지
포함해 미리보기를 만들며 Telegram 키는 제공하지 않습니다.

06:00 준비 실행에서는 Copilot CLI를 설치하고 최종 선정 기사 본문으로 20~30자의
실무 참고 메시지만 생성합니다. 최종 Telegram 메시지와 생성 건수만 준비 JSON에
저장하며 기사 본문은 저장하지 않습니다. Copilot 설치 실패, 사용 한도 초과,
응답 오류가 발생하면 기존 키워드 기반 실무 참고 메시지로 자동 대체합니다.
Copilot 인증에는 Actions가 발급하는 `GITHUB_TOKEN`을 사용하므로 별도 Copilot 토큰
secret은 필요하지 않습니다.

Repository Secrets에 다음 값을 등록합니다.

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
NAVER_API_HUB_CLIENT_ID
NAVER_API_HUB_CLIENT_SECRET
```

Actions는 위 네이버 Secrets를 실행 환경의 `NAVER_CLIENT_ID`와
`NAVER_CLIENT_SECRET`으로 전달합니다. 로컬 실행에서는 이 환경변수 이름을 사용합니다.

## 운영 환경

운영 발송은 cron-job.org의 `dapa-morning-brief` 요청만 사용하며 Windows PC의 전원
상태와 무관합니다. Linux cron과 Hermes Cronjob도 운영 발송에 사용하지 않습니다.

## 수집 우선순위

기본 실행은 공식 RSS·게시판, 인증 정보가 있는 네이버 검색 API,
Google News RSS를 함께 조회합니다. 네이버 인증 정보가 없으면 해당 경로를
건너뛰고 로그에 남깁니다. Google만 요청하는 `--google-only` 옵션도 있습니다.

최종 기사는 제공자 순서대로 무조건 채우지 않습니다. 발행 시각, 조회수·검색
순위 등 기존 정렬 기준을 사용하고 본문·제목 기반 중복 제거 후 카테고리별
5건을 선정합니다. 방위사업청 조달·계약 감시 보도는 기존 정원 안에서
대표 후보 1건을 보존합니다. 전체 검색 결과가 없을 때 넓은 OR 검색과
단일 키워드 Google 폴백을 시도합니다.

기사 부족 시 억지로 내용을 만들지 않고 `수집 기사 없음`을 표시합니다.
