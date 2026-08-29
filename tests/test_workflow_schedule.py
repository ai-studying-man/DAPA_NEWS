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
