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

- 정책브리핑 방위사업청/국방부 RSS와 국방일보 RSS를 우선 수집합니다.
- Google News RSS를 보조 수집원으로 사용합니다.
- 최근 1일 기사를 기본 대상으로 하며, 부족하면 2일까지 확장할 수 있습니다.
- 섹션별 최대 3건을 선정합니다.
- 기사 제목 기반으로 30~40자 내외의 짧은 요약을 생성합니다.
- 기사 전문은 복제하지 않고 제목, 출처, 날짜, 링크 중심으로만 전송합니다.

## 예약 실행

자세한 설정은 [docs/CRON_SETUP.md](docs/CRON_SETUP.md)를 참고하세요.
