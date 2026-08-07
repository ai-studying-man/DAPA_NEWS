from pathlib import Path


def test_workflow_restores_pre_0630_slots_and_exact_0630_kst_cron() -> None:
    # Given
    workflow_path = Path(".github/workflows/dapa-morning-brief.yml")

    # When
    workflow = workflow_path.read_text(encoding="utf-8")

    # Then
    assert '- cron: "30,45 20 * * *"' in workflow
    assert '- cron: "0,15,30 21 * * *"' in workflow
