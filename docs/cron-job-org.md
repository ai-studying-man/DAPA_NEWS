# cron-job.org 운영 설정

이 프로젝트의 주 스케줄러는 GitHub Actions `schedule`이 아니라 cron-job.org입니다.
Windows PC가 꺼져 있어도 cron-job.org가 GitHub REST API를 호출해
workflow를 시작합니다.

## Schedule

cron-job.org에서 다음과 같이 설정합니다.

```text
Schedule: Every day
Time: 05:40
Timezone: Asia/Seoul
```

05:40에 Actions를 먼저 시작하고, workflow가 06:00 KST까지 대기한 뒤 뉴스 수집을
시작합니다. 준비가 06:25 이전에 끝나면 06:30까지 대기하고, 늦게 끝나면 즉시
Telegram으로 발송합니다.

## HTTP request

```text
Method: POST
URL: https://api.github.com/repos/ai-studying-man/DAPA_NEWS/dispatches
```

Headers:

```text
Accept: application/vnd.github+json
Authorization: Bearer <GITHUB_FINE_GRAINED_PAT>
Content-Type: application/json
X-GitHub-Api-Version: 2026-03-10
```

Request body:

```json
{
  "event_type": "dapa-morning-brief"
}
```

정상 요청은 `HTTP 204 No Content`를 반환합니다. GitHub REST API의 repository
dispatch endpoint는 fine-grained PAT의 대상 저장소에 `Contents: write` 권한을
요구합니다.

## PAT 보안

- Fine-grained personal access token을 사용합니다.
- Repository access는 `Only select repositories`로 제한하고 `DAPA_NEWS`만 선택합니다.
- 토큰은 cron-job.org의 Secret/Header 저장 기능에만 입력합니다.
- 토큰을 소스 코드, YAML, README, `.env` 커밋, JSON 파일에 저장하지 않습니다.
- 이 문서의 `<GITHUB_FINE_GRAINED_PAT>`는 실제 토큰으로 바꾸어 커밋하지 않습니다.

## 확인 방법

1. cron-job.org의 `Test run`으로 POST를 실행합니다.
2. GitHub Actions에서 `dapa-morning-brief` 실행이 생성되는지 확인합니다.
3. 실행 로그에 `Trigger: repository_dispatch / dapa-morning-brief`가 표시되는지 확인합니다.
4. 이미 당일 발송 cache가 있으면 뉴스 수집과 Telegram 발송이 건너뛰어질 수 있습니다.

GitHub Actions의 `workflow_dispatch`는 수동 실행용으로 유지합니다. 일상 운영에는
cron-job.org의 `dapa-morning-brief`만 사용합니다.
