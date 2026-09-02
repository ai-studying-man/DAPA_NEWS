# 방산출근길 예약 실행 구성

## 실행 시간

목표 발송 시간은 매일 06:30 KST입니다.

- cron-job.org 요청: 매일 05:30 KST
- repository dispatch: `dapa-morning-brief`
- GitHub Actions는 05:45 전 시작 시 그 시각까지 대기한 뒤 뉴스·날씨·실무 참고 메시지를 준비합니다.
- 06:20 KST는 준비 완료 목표입니다.
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

cron-job.org가 05:30 KST에 `dapa-morning-brief` 이벤트를 요청합니다. 각 production job은
준비 명령과 Telegram API를 한 번씩만 호출합니다. checkout·환경설정·준비·발송 중 어느
단계든 실패하면 `dapa-morning-brief-retry` 내부 이벤트를 60초 뒤 발생시켜 새 workflow
실행을 요청합니다. replacement 실행은 최대 5회로 제한하며, production job은 120분,
retry job은 15분 실행 한도를 사용합니다.

성공한 실행은 먼저 날짜별 발송 cache를 확인합니다. 이미 발송된 날이면 05:45 대기와
뉴스 수집을 건너뛰고 종료합니다. 미발송이면 `.dapa-prepared/morning-brief.json`을
생성하고 06:30까지 대기한 뒤 Telegram으로 전송합니다. production job은 공통 concurrency
group과 날짜별 발송 cache를 사용하므로 중복 요청이 발생해도 중복 발송하지 않습니다.
준비가 지연되어 06:30을 넘기면 준비가 끝나는 즉시 한 번 발송합니다. Telegram 호출이
실패하면 해당 job을 실패 처리하고 replacement workflow가 전체 실행을 다시 시작합니다.
Telegram 발송에 성공한 날짜는 완료 캐시에 기록하므로 이후 실행은 발송 단계를
건너뜁니다.

사용자가 실행하는 `workflow_dispatch`는 기존 입력에 따라 preview 또는 명시적 resend를
수행합니다. `dapa-morning-brief`와 `dapa-morning-brief-watchdog` repository dispatch는
production `scheduled-brief`로 연결되고, `dapa-morning-brief-retry`는 자동 복구용입니다.

과천시·대전시 당일 날씨는 Open-Meteo Forecast API의 KMA Seamless 모델을 우선
사용합니다. KMA 모델 값이 비어 있으면 KMA 단기예보 API 프록시에서 당일 시간별
예보를 조회해 최저·최고기온과 하늘상태를 계산합니다. 기상청 예보 API도 장애일
때만 Open-Meteo 자동 모델로 재조회하며, 그래도 실패한 지역은 `수집 실패`로
표시하고 전체 뉴스 발송은 계속합니다.

05:45 준비 실행에서는 Copilot CLI를 설치하고 최종 선정 기사 본문으로 20~30자의
실무 참고 메시지만 생성합니다. 최종 Telegram 메시지와 생성 건수만 준비 JSON에
저장하며 기사 본문은 저장하지 않습니다. Copilot 설치 실패, 사용 한도 초과,
응답 오류가 발생하면 기존 키워드 기반 실무 참고 메시지로 자동 대체합니다.
Copilot 인증에는 Actions가 발급하는 `GITHUB_TOKEN`을 사용하므로 별도 Copilot 토큰
secret은 필요하지 않습니다.

Repository Secrets에 다음 값을 등록합니다.

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

## Windows watchdog (비상용)

운영 발송은 cron-job.org가 담당하므로 Windows PC가 켜져 있거나 watchdog 프로그램이
실행 중일 필요가 없습니다. 기존 `dapa-morning-brief-watchdog` 이벤트와 PowerShell
스크립트는 비상용 호환 경로로 남겨두지만, cron-job.org가 안정적으로 확인되면 작업
스케줄러 등록 작업은 비활성화하는 것을 권장합니다. 기존 작업은 삭제하지 않아야
필요할 때 다시 활성화할 수 있습니다.

```powershell
Disable-ScheduledTask -TaskName "DAPA Morning Brief Watchdog"
```

복구가 필요하면 `Enable-ScheduledTask`를 사용합니다. Linux cron과 Hermes Cronjob은
운영 발송에 사용하지 않습니다.

## 수집 우선순위

1. 국방일보 방위사업 RSS
2. Google News RSS 섹션별 검색
3. 넓은 OR 검색과 단일 키워드 폴백

기사 부족 시 억지로 내용을 만들지 않고 `수집 기사 없음`을 표시합니다.
