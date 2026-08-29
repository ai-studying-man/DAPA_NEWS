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

- 국방일보 RSS와 Google News RSS를 수집원으로 사용합니다.
- 정책브리핑 및 국방부 RSS는 사용하지 않습니다.
- 최근 1일 기사를 기본 대상으로 하며, 부족하면 2일까지 확장할 수 있습니다.
- 섹션별 최대 5건을 선정하되, 동일 사건의 유사 기사는 언론사가 달라도 1건만 남깁니다.
- GitHub Actions에서는 05:45부터 기사를 수집하고 Copilot CLI로 20~30자의 실무
  참고 메시지를 생성해 06:20을 목표로 최종 Telegram 메시지를 JSON으로 준비합니다.
- 05:45 예약 누락에 대비해 05:50부터 06:15까지 5분 간격 백업 예약을 두며,
  준비와 Telegram 발송은 Actions 실행당 각각 한 번만 시도합니다. 어느 단계든
  실패하면 60초 뒤 replacement 실행을 요청합니다.
- Windows PC 작업 스케줄러도 매일 05:45 KST에 PC를 깨우고
  `dapa-morning-brief-watchdog` 이벤트를 GitHub에 요청합니다. GitHub 요청이 실패하면
  PC에서 1분 간격으로 최대 360회 재시도하며, Telegram 발송은 계속 Actions에서만
  수행합니다.
- 준비 JSON에는 최종 메시지와 생성 건수만 저장하며 기사 본문은 저장하지 않습니다.
- 같은 예약 Actions 실행이 준비된 JSON을 보관한 채 06:30까지 대기합니다. 이미
  06:30을 지났다면 즉시 한 번 발송합니다. 성공한 날짜는 발송 완료로 기록해 백업
  예약이나 replacement 실행에서 다시 발송하지 않습니다.
- 과천시·대전시의 당일 날씨는 Open-Meteo Forecast API에서 수집해 메시지 상단에
  표시합니다.
- Open-Meteo KMA Seamless 값이 비어 있으면 기상청 단기예보 API를 우선 사용합니다.
  기상청 예보 API도 장애일 때만 Open-Meteo 자동 모델로 재조회합니다.
- Copilot CLI를 사용할 수 없거나 한도를 초과하면 기존 제목·키워드 기반 실무 참고
  메시지를 사용합니다.
- 기사 전문은 복제하지 않고 제목, 출처, 날짜, 링크 중심으로만 전송합니다.

## 예약 실행

자세한 설정은 [docs/CRON_SETUP.md](docs/CRON_SETUP.md)를 참고하세요.
