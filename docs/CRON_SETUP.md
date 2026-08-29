# 방산출근길 예약 실행 구성

## 실행 시간

목표 발송 시간은 매일 06:30 KST입니다.

- 한국 시간대 최초 실행: 05:45 KST
- 한국 시간대 백업 실행: 05:50부터 06:15까지 5분 간격
- UTC 기준 Actions cron: `45,50,55 20 * * *`, `0,5,10,15 21 * * *`
- GitHub Actions는 05:45부터 뉴스·날씨·실무 참고 메시지를 준비합니다.
- 06:20 KST는 준비 완료 목표입니다.
- 준비 명령과 Telegram 발송은 Actions 실행당 각각 한 번만 시도합니다.
- 어느 단계든 실패해 job이 실패하면 60초 뒤 replacement 실행을 요청합니다.
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

운영 스케줄의 단일 기준은 `.github/workflows/dapa-morning-brief.yml`입니다.
GitHub Actions cron은 UTC 기준입니다.

```cron
45,50,55 20 * * *  # 05:45, 05:50, 05:55 KST
0,5,10,15 21 * * * # 06:00, 06:05, 06:10, 06:15 KST
```

05:45가 최초 실행이며 나머지 예약은 GitHub의 예약 누락을 보강합니다. GitHub 예약은
1분 간격을 지원하지 않으므로 예약 보강은 최소 허용 간격인 5분을 사용합니다. 각
production job은 준비 명령과 Telegram API를 한 번씩만 호출합니다. checkout·환경설정·
준비·발송 중 어느 단계든 실패하면 `dapa-morning-brief-retry` 내부 이벤트를 60초 뒤
발생시켜 새 workflow 실행을 요청합니다. replacement 실행도 실패하면 같은 규칙을
반복하며, replacement 횟수는 최대 360회로 제한합니다. 각 production job은
GitHub-hosted runner 한도에 맞춰 최대 360분 실행됩니다.

성공한 실행은 `.dapa-prepared/morning-brief.json`을 같은 runner에 유지하고 06:30까지
대기한 뒤 Telegram으로 전송합니다. production job은 공통 concurrency group과 날짜별
발송 캐시를 사용하므로 백업 실행이 중복 발송하지 않습니다. 예약 이벤트나 준비가
지연되어 06:30을 넘기면 준비가 끝나는 즉시 한 번 발송합니다. Telegram 호출이
실패하면 해당 job을 실패 처리하고 replacement workflow가 전체 실행을 다시 시작합니다.
Telegram 발송에 성공한 날짜는 완료 캐시에 기록하므로 이후 실행은 발송 단계를
건너뜁니다.

사용자가 실행하는 `workflow_dispatch`와 `dapa-morning-brief` repository dispatch는
Telegram 비밀값을 주입하지 않는 미리보기 전용입니다. 자동 복구용
`dapa-morning-brief-retry` dispatch만 예약 `scheduled-brief` job으로 연결됩니다.

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

## Windows watchdog

GitHub `schedule` 이벤트 누락에 대비해 운영 PC의 Windows 작업 스케줄러가 매일
05:45 KST에 `scripts/invoke_github_watchdog.ps1`을 실행합니다. 이 작업은 PC를
절전 상태에서 깨우고 `dapa-morning-brief-watchdog` repository dispatch를 GitHub에
요청합니다. 요청 실패 시 1분 간격으로 최대 360회 재시도합니다.

PC는 Telegram을 직접 호출하지 않습니다. watchdog 이벤트로 시작된 Actions가 기존
production job과 날짜별 발송 완료 캐시를 그대로 사용하므로 GitHub cron과 watchdog이
동시에 실행되어도 Telegram 발송은 최초 성공 1회로 제한됩니다.

작업 등록 또는 갱신 명령은 다음과 같습니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\register_github_watchdog_task.ps1
```

등록 작업은 `WakeToRun`, `StartWhenAvailable`, 실패 시 1분 간격 재시작을 사용합니다.
Windows 작업 스케줄러는 절전·최대절전 상태의 PC를 깨울 수 있습니다. 완전히 종료된
PC를 자동으로 켜려면 메인보드 BIOS의 `Resume By RTC Alarm`도 별도로 설정해야 합니다.
Linux cron과 Hermes Cronjob은 운영 발송에 사용하지 않습니다.

## 수집 우선순위

1. 국방일보 방위사업 RSS
2. Google News RSS 섹션별 검색
3. 넓은 OR 검색과 단일 키워드 폴백

기사 부족 시 억지로 내용을 만들지 않고 `수집 기사 없음`을 표시합니다.
