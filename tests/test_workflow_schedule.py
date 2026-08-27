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


def test_workflow_recovers_missed_start_and_retries_until_delivery() -> None:
    # Given
    workflow = Path(".github/workflows/dapa-morning-brief.yml").read_text(
        encoding="utf-8",
    )

    # When
    retry_dispatch = "dapa-morning-brief-retry"

    # Then
    assert '- cron: "45,50,55 20 * * *"' in workflow
    assert '- cron: "0,5,10,15 21 * * *"' in workflow
    assert retry_dispatch in workflow
    assert "retry-failed-run:" in workflow
    assert "contents: write" in workflow
    assert "group: dapa-morning-brief-delivery" in workflow
    assert "timeout-minutes: 360" in workflow
    assert workflow.count("sleep 60") >= 3
    assert "next_retry_epoch" in workflow
    assert "attempt=$((attempt + 1))" in workflow
    assert "timeout --foreground" in workflow
    assert "delivery_attempt=$((delivery_attempt + 1))" in workflow
    assert "MAX_RETRY_RUNS: 360" in workflow
    retry_job = workflow.split("  retry-failed-run:\n", maxsplit=1)[1].split(
        "  manual-preview:\n",
        maxsplit=1,
    )[0]
    assert "--prepared-input" not in retry_job


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
