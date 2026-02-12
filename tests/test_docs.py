from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runbook_contains_required_sections() -> None:
    runbook = (ROOT / "docs" / "runbook.md").read_text(encoding="utf-8").lower()

    assert "rate limiting" in runbook
    assert "provenance" in runbook
    assert "rerun" in runbook
    assert "go-live" in runbook
