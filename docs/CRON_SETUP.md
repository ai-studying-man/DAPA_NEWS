# 방산출근길 예약 실행 구성

## 실행 시간

목표 실행 시간은 매일 06:30 KST입니다.

- 한국 시간대 cron: `30 6 * * *`
- UTC 기준 cron: `30 21 * * *`
- 발송 기준은 06:30 KST로 고정합니다.
- GitHub Actions는 예약 실행이 지연될 수 있으므로 05:30부터 여러 번 깨워 두고,
  실행된 runner가 06:30 KST까지 대기한 뒤 발송합니다.

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

## Windows 작업 스케줄러

작업 만들기에서 다음 값을 사용합니다.

- 트리거: 매일 06:30
- 프로그램: `powershell.exe`
- 인수:

```text
-NoProfile -ExecutionPolicy Bypass -File C:\Users\dusgh\Desktop\DAPA_NEWS\scripts\run_morning_brief.ps1
```

환경변수는 사용자 환경변수 또는 작업 스케줄러의 실행 계정에 설정합니다.

## Linux cron

`crontab -e`에 아래 줄을 추가합니다.

```cron
30 6 * * * cd /path/to/DAPA_NEWS && . .venv/bin/activate && python -m dapa_morning_brief.cli >> logs/dapa_morning_brief.log 2>&1
```

`uv`를 사용하는 서버라면 다음 형태도 가능합니다.

```cron
30 6 * * * cd /path/to/DAPA_NEWS && uv run dapa-morning-brief >> logs/dapa_morning_brief.log 2>&1
```

## GitHub Actions

GitHub Actions cron은 UTC 기준입니다. 다만 scheduled workflow는 GitHub 큐 상황에
따라 지연될 수 있으므로 `.github/workflows/dapa-morning-brief.yml`은 아래 UTC
일정으로 runner를 미리 시작합니다.

```cron
30,45 20 * * *
0,15,30 21 * * *
```

위 일정은 05:30, 05:45, 06:00, 06:15, 06:30 KST에 해당합니다. workflow 내부에서
06:30 KST 전이면 `sleep`으로 대기하고, 같은 날짜에 이미 발송한 기록이 있으면
추가 발송을 건너뜁니다.

국방부·방사청 보도자료는 성공적으로 확인한 최신값을 Actions 캐시에 저장합니다.
공식 게시판이 일시적으로 응답하지 않으면 직전 최신값을 사용하며, 저장값도 없으면
잘못된 `없음` 메시지를 보내지 않고 다음 예약 실행에서 다시 시도합니다.

실제 발송 실행에서는 Copilot CLI를 설치하고 최종 선정 기사 본문을 한 번에
요약합니다. Copilot 설치 실패, 사용 한도 초과, 응답 오류가 발생하면 기존
키워드 기반 실무 참고 메시지로 자동 대체합니다. Copilot 인증에는 Actions가
발급하는 `GITHUB_TOKEN`을 사용하므로 별도 Copilot 토큰 secret은 필요하지 않습니다.

Repository Secrets에 다음 값을 등록합니다.

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

## Hermes Cronjob

Hermes Cronjob에는 다음 형태로 등록합니다.

```text
이름: 방산출근길 뉴스레터
스케줄: 매일 06:30 Asia/Seoul
명령: uv run dapa-morning-brief --days 1 --fallback-days 2
전달: Telegram Bot API
환경변수: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TZ=Asia/Seoul
```

## 수집 우선순위

1. 정책브리핑 방위사업청 RSS
2. 정책브리핑 국방부 RSS
3. 정책브리핑 보도자료 RSS
4. 국방일보 방위사업 RSS
5. Google News RSS 섹션별 검색
6. 넓은 OR 검색과 단일 키워드 폴백

기사 부족 시 억지로 내용을 만들지 않고 `수집 기사 없음`을 표시합니다.
