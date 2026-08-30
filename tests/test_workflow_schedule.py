from pathlib import Path


def test_workflow_targets_0620_and_sends_at_or_after_0630() -> None:
    # Given
    workflow_path = Path(".github/workflows/dapa-morning-brief.yml")

    # When
    workflow = workflow_path.read_text(encoding="utf-8")

    # Then
    assert '- cron: "45,50,55 20 * * *"' in workflow
    assert '- cron: "30 21 * * *"' not in workflow
    assert "scheduled-brief:" in workflow
    prepare_command = "--prepare-output .dapa-prepared/morning-brief.json"
    prepare_target = "06:20:00"
    send_command = "--prepared-input .dapa-prepared/morning-brief.json"
    assert prepare_command in workflow
    assert send_command in workflow
    assert prepare_target in workflow
    prepare_step = workflow.index("- name: Prepare complete morning brief")
    wait_step = workflow.index("- name: Wait until 06:30 KST when early")
    assert prepare_step < workflow.index(prepare_command) < wait_step
    assert wait_step < workflow.index(send_command)
    assert "06:30:00" in workflow
    assert "sending immediately" in workflow
    assert "Telegram will not be called" not in workflow
    assert "restricted to 06:30" not in workflow


def test_workflow_restarts_failed_run_and_sends_once_per_run() -> None:
    # Given
    workflow = Path(".github/workflows/dapa-morning-brief.yml").read_text(
        encoding="utf-8",
    )

    # When
    production_job = workflow.split("  scheduled-brief:\n", maxsplit=1)[1].split(
        "  retry-failed-run:\n",
        maxsplit=1,
    )[0]
    retry_dispatch = "dapa-morning-brief-retry"

    # Then
    assert '- cron: "45,50,55 20 * * *"' in workflow
    assert '- cron: "0,5,10,15 21 * * *"' in workflow
    assert retry_dispatch in workflow
    assert "retry-failed-run:" in workflow
    assert "contents: write" in workflow
    assert "group: dapa-morning-brief-delivery" in workflow
    assert "timeout-minutes: 360" in workflow
    assert production_job.count("--prepare-output") == 1
    assert production_job.count("--prepared-input") == 1
    assert "while true" not in production_job
    assert "sleep 60" not in production_job
    assert "timeout --foreground" in workflow
    assert "MAX_RETRY_RUNS: 360" in workflow
    retry_job = workflow.split("  retry-failed-run:\n", maxsplit=1)[1].split(
        "  manual-preview:\n",
        maxsplit=1,
    )[0]
    assert "needs.scheduled-brief.result == 'failure'" in retry_job
    assert "sleep 60" in retry_job
    assert "--prepared-input" not in retry_job


def test_windows_watchdog_dispatch_routes_to_production_and_retries_failures() -> None:
    # Given
    workflow = Path(".github/workflows/dapa-morning-brief.yml").read_text(
        encoding="utf-8",
    )
    watchdog_dispatch = "dapa-morning-brief-watchdog"

    # When
    production_job = workflow.split("  scheduled-brief:\n", maxsplit=1)[1].split(
        "  retry-failed-run:\n",
        maxsplit=1,
    )[0]
    retry_job = workflow.split("  retry-failed-run:\n", maxsplit=1)[1].split(
        "  manual-preview:\n",
        maxsplit=1,
    )[0]
    manual_job = workflow.split("  manual-preview:\n", maxsplit=1)[1]

    # Then
    assert watchdog_dispatch in workflow
    assert watchdog_dispatch in production_job
    assert watchdog_dispatch in retry_job
    assert watchdog_dispatch not in manual_job


def test_windows_watchdog_task_wakes_at_0545_and_retries_every_minute() -> None:
    # Given
    watchdog = Path("scripts/invoke_github_watchdog.ps1")
    registration = Path("scripts/register_github_watchdog_task.ps1")

    # When
    watchdog_script = watchdog.read_text(encoding="utf-8")
    registration_script = registration.read_text(encoding="utf-8")

    # Then
    assert "dapa-morning-brief-watchdog" in watchdog_script
    assert "Start-Sleep -Seconds 60" in watchdog_script
    assert "MaxAttempts = 360" in watchdog_script
    assert "05:45" in registration_script
    assert "WakeToRun = $true" in registration_script
    assert "StartWhenAvailable = $true" in registration_script
    assert '"-WindowStyle Hidden"' in registration_script
    assert "-RestartInterval (New-TimeSpan -Minutes 1)" in registration_script
    assert "-RestartCount 360" in registration_script


def test_windows_watchdog_confirms_run_and_records_failure_details() -> None:
    # Given
    watchdog_script = Path("scripts/invoke_github_watchdog.ps1").read_text(
        encoding="utf-8",
    )

    # When
    # Then
    assert "github_watchdog_failures.jsonl" in watchdog_script
    assert "actions/workflows/dapa-morning-brief.yml/runs" in watchdog_script
    assert "actions/runs/$RunId/jobs" in watchdog_script
    assert "([DateTime]$candidate.created_at).ToUniversalTime()" in watchdog_script
    assert "accepted but no matching Actions run was created" in watchdog_script
    assert "Write-FailureRecord" in watchdog_script


def test_failed_actions_run_uploads_diagnostics_before_retry() -> None:
    # Given
    workflow = Path(".github/workflows/dapa-morning-brief.yml").read_text(
        encoding="utf-8",
    )

    # When
    retry_job = workflow.split("  retry-failed-run:\n", maxsplit=1)[1].split(
        "  manual-preview:\n",
        maxsplit=1,
    )[0]

    # Then
    assert "actions: read" in retry_job
    assert "failure-report.json" in retry_job
    assert "GITHUB_STEP_SUMMARY" in retry_job
    assert "actions/upload-artifact@v4" in retry_job
    assert "retention-days: 30" in retry_job
    diagnostics_step = retry_job.index("Collect failed-run diagnostics")
    retry_step = retry_job.index("Re-dispatch failed workflow run after one minute")
    assert diagnostics_step < retry_step


def test_successful_run_retains_exact_prepared_brief_for_diagnostics() -> None:
    # Given
    workflow = Path(".github/workflows/dapa-morning-brief.yml").read_text(
        encoding="utf-8",
    )

    # When
    production_job = workflow.split("  scheduled-brief:\n", maxsplit=1)[1].split(
        "  retry-failed-run:\n",
        maxsplit=1,
    )[0]

    # Then
    assert "Upload prepared brief diagnostics" in production_job
    assert "dapa-prepared-${{ github.run_id }}" in production_job
    assert "path: .dapa-prepared/morning-brief.json" in production_job
    assert "retention-days: 30" in production_job


def test_manual_workflow_is_preview_only() -> None:
    # Given
    workflow = Path(".github/workflows/dapa-morning-brief.yml").read_text(
        encoding="utf-8",
    )

    # When
    manual_job = workflow.split("  manual-preview:\n", maxsplit=1)[1]

    # Then
    assert "--dry-run" in manual_job
    assert "TELEGRAM_BOT_TOKEN" not in manual_job
    assert "TELEGRAM_CHAT_ID" not in manual_job


def test_copilot_smoke_test_calls_model_without_telegram_delivery() -> None:
    # Given
    workflow = Path(".github/workflows/dapa-morning-brief.yml").read_text(
        encoding="utf-8",
    )

    # When
    smoke_job = workflow.split("  copilot-smoke-test:\n", maxsplit=1)[1].split(
        "  scheduled-brief:\n",
        maxsplit=1,
    )[0]
    manual_job = workflow.split("  manual-preview:\n", maxsplit=1)[1]

    # Then
    assert "copilot_test:" in workflow
    assert "inputs.copilot_test == true" in smoke_job
    assert "copilot-requests: write" in smoke_job
    assert "GITHUB_TOKEN: ${{ github.token }}" in smoke_job
    assert "npm install -g @github/copilot" in smoke_job
    assert 'Reply with exactly COPILOT_OK and nothing else.' in smoke_job
    assert "COPILOT_OK" in smoke_job
    assert "actions/upload-artifact@v4" in smoke_job
    assert "TELEGRAM_BOT_TOKEN" not in smoke_job
    assert "TELEGRAM_CHAT_ID" not in smoke_job
    assert "dapa_morning_brief.cli" not in smoke_job
    assert "inputs.copilot_test != true" in manual_job


def test_explicit_resend_bypasses_daily_cache_and_retries_delivery() -> None:
    # Given
    workflow = Path(".github/workflows/dapa-morning-brief.yml").read_text(
        encoding="utf-8",
    )

    # When
    production_job = workflow.split("  scheduled-brief:\n", maxsplit=1)[1].split(
        "  retry-failed-run:\n",
        maxsplit=1,
    )[0]
    retry_job = workflow.split("  retry-failed-run:\n", maxsplit=1)[1].split(
        "  manual-preview:\n",
        maxsplit=1,
    )[0]
    manual_job = workflow.split("  manual-preview:\n", maxsplit=1)[1]

    # Then
    assert "resend:" in workflow
    assert "type: boolean" in workflow
    assert "FORCE_DELIVERY:" in production_job
    assert "inputs.resend" in production_job
    assert production_job.count("env.FORCE_DELIVERY == 'true'") >= 7
    assert "client_payload[force_send]" in retry_job
    assert "inputs.resend" in retry_job
    assert "inputs.resend != true" in manual_job


def test_workflow_does_not_bootstrap_press_release_cache() -> None:
    # Given
    workflow = Path(".github/workflows/dapa-morning-brief.yml").read_text(
        encoding="utf-8",
    )

    # When
    # Then
    assert "DAPA_PRESS_RELEASE_CACHE" not in workflow
    assert "official press release cache" not in workflow.casefold()
    assert "initial-press-releases.json" not in workflow
