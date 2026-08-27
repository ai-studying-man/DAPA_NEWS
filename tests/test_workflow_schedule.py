from pathlib import Path


def test_workflow_prepares_before_0620_and_sends_prepared_json_at_0630() -> None:
    # Given
    workflow_path = Path(".github/workflows/dapa-morning-brief.yml")

    # When
    workflow = workflow_path.read_text(encoding="utf-8")

    # Then
    assert '- cron: "45 20 * * *"' in workflow
    assert '- cron: "30 21 * * *"' in workflow
    assert "prepare-brief:" in workflow
    assert "send-brief:" in workflow
    prepare_command = "--prepare-output .dapa-prepared/morning-brief.json"
    prepare_deadline = "06:20:00"
    send_command = "--prepared-input .dapa-prepared/morning-brief.json"
    assert prepare_command in workflow
    assert send_command in workflow
    assert prepare_deadline in workflow
    assert workflow.index(prepare_command) < workflow.index(prepare_deadline)
    assert workflow.index("prepare-brief:") < workflow.index("send-brief:")
    assert "actions/cache/save@v4" in workflow
    assert "dapa-prepared-${{ steps.kst-date.outputs.today }}" in workflow


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
