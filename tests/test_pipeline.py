from __future__ import annotations

import json
from pathlib import Path

from sp_recovery.config import RecoveryConfig
from sp_recovery.discovery import CaptureRecord
from sp_recovery.pipeline import run_pipeline


def test_run_pipeline_creates_mirror_state_and_reports(tmp_path: Path) -> None:
    captures = [
        CaptureRecord(
            timestamp="20240201120000",
            original="http://www.somethingpositive.net/sp02012024.html",
            mimetype="text/html",
            statuscode=200,
            digest="A",
        ),
        CaptureRecord(
            timestamp="20240201120000",
            original="http://www.somethingpositive.net/arch/sp02012024.gif",
            mimetype="image/gif",
            statuscode=200,
            digest="B",
        ),
    ]

    def fetcher(url: str) -> tuple[int, bytes]:
        if url.endswith(".html"):
            return (200, b'<html><body><img src="arch/sp02012024.gif"></body></html>')
        return (200, b"GIF89a")

    config = RecoveryConfig(
        domain="somethingpositive.net",
        from_date="2023-01-01",
        to_date="2025-02-01",
        output_root=tmp_path,
        max_canonical=50,
        request_interval_seconds=0.0,
        only_missing_urls=set(),
    )

    run_pipeline(config, discovered_records=captures, fetcher=fetcher)

    assert (tmp_path / "state" / "discovered_captures.jsonl").exists()
    assert (tmp_path / "state" / "canonical_urls.jsonl").exists()
    assert (tmp_path / "state" / "provenance.jsonl").exists()

    assert (tmp_path / "reports" / "coverage_report.md").exists()
    assert (tmp_path / "reports" / "gap_register.csv").exists()
    assert (tmp_path / "reports" / "provenance_manifest.csv").exists()

    html_file = tmp_path / "www.somethingpositive.net" / "sp02012024.html"
    assert html_file.exists()
    assert b"/www.somethingpositive.net/arch/sp02012024.gif" in html_file.read_bytes()


def test_run_pipeline_can_target_only_missing_urls(tmp_path: Path) -> None:
    captures = [
        CaptureRecord(
            timestamp="20240201120000",
            original="http://www.somethingpositive.net/sp1.html",
            mimetype="text/html",
            statuscode=200,
            digest="A",
        ),
        CaptureRecord(
            timestamp="20240201120000",
            original="http://www.somethingpositive.net/sp2.html",
            mimetype="text/html",
            statuscode=200,
            digest="B",
        ),
    ]

    def fetcher(_: str) -> tuple[int, bytes]:
        return (200, b"<html></html>")

    config = RecoveryConfig(
        domain="somethingpositive.net",
        from_date="2021-01-01",
        to_date="2025-02-01",
        output_root=tmp_path,
        max_canonical=50,
        request_interval_seconds=0.0,
        only_missing_urls={"http://www.somethingpositive.net/sp2.html"},
    )

    run_pipeline(config, discovered_records=captures, fetcher=fetcher)

    provenance_lines = (tmp_path / "state" / "provenance.jsonl").read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(line) for line in provenance_lines]

    assert len(parsed) == 1
    assert parsed[0]["original_url"] == "http://www.somethingpositive.net/sp2.html"
