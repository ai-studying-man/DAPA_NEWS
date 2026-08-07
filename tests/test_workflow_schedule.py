from pathlib import Path


def test_workflow_prepares_from_0600_and_sends_prepared_json_at_0630() -> None:
    # Given
    workflow_path = Path(".github/workflows/dapa-morning-brief.yml")

    # When
    workflow = workflow_path.read_text(encoding="utf-8")

    # Then
    assert '- cron: "0,15,30 21 * * *"' in workflow
    prepare_command = "--prepare-output .dapa-prepared/morning-brief.json"
    send_window = "target_epoch="
    send_command = "--prepared-input .dapa-prepared/morning-brief.json"
    assert prepare_command in workflow
    assert send_command in workflow
    assert workflow.index(prepare_command) < workflow.index(send_window)
    assert workflow.index(send_window) < workflow.index(send_command)
    assert (
        "run: uv run python -m dapa_morning_brief.cli --days 1 --fallback-days 2"
        not in workflow
    )


def test_workflow_bootstraps_and_saves_press_release_cache_before_send() -> None:
    # Given
    workflow = Path(".github/workflows/dapa-morning-brief.yml").read_text(
        encoding="utf-8",
    )

    # When
    seed = "data/initial-press-releases.json"
    save_cache = "Save latest official press releases"
    send_command = "--prepared-input .dapa-prepared/morning-brief.json"

    # Then
    assert seed in workflow
    assert workflow.index(save_cache) < workflow.index(send_command)
