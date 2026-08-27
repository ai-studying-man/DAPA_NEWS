# 방산출근길 예약 실행 구성

## 실행 시간

목표 발송 시간은 매일 06:30 KST입니다.

- 한국 시간대 Actions cron: `45 5 * * *`
- UTC 기준 Actions cron: `45 20 * * *`
- GitHub Actions는 05:45부터 뉴스·날씨·실무 참고 메시지를 준비합니다.
- 준비된 최종 메시지는 JSON으로 저장하며 기사 본문은 저장하지 않습니다.
- 준비 단계는 06:20 KST 마감 검사를 통과해야 합니다.
- 같은 Actions 실행이 06:30까지 대기한 뒤 Telegram Bot API를 호출합니다.
- 06:30 발송 분을 놓친 실행은 늦게 보내지 않고 실패합니다.

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
45 20 * * *  # 준비 시작: 05:45 KST
```

예약 실행은 05:45에 수집과 Copilot 실무 참고 생성을 시작하고 06:20 마감 검사를
통과한 `.dapa-prepared/morning-brief.json`을 같은 runner에 유지합니다. 이후 06:30까지
대기한 뒤 Telegram으로 전송합니다. 같은 날짜에 이미 발송한 기록이 있으면 발송을
건너뜁니다. 예약 이벤트가 지연되어 06:20 준비 마감이나 06:30 발송 분을 놓치면
오래된 메시지를 늦게 보내지 않고 실패 상태로 남깁니다.

`workflow_dispatch`와 `repository_dispatch`는 Telegram 비밀값을 주입하지 않는
미리보기 전용 실행입니다. 운영 Telegram 발송은 예약 `scheduled-brief` job에서만
가능합니다.

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

## 다른 스케줄러

Windows 작업 스케줄러, Linux cron, Hermes Cronjob은 현재 운영 발송에 사용하지
않습니다. 이 도구에 별도 발송 일정을 등록하면 GitHub Actions와 중복되거나 06:30
외 시간에 전송될 수 있으므로 운영 기준으로 추가하지 않습니다.

## 수집 우선순위

1. 국방일보 방위사업 RSS
2. Google News RSS 섹션별 검색
3. 넓은 OR 검색과 단일 키워드 폴백

기사 부족 시 억지로 내용을 만들지 않고 `수집 기사 없음`을 표시합니다.
