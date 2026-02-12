from __future__ import annotations

from pathlib import Path

from sp_recovery.reporting import (
    CoverageSummary,
    GapEntry,
    build_gap_register,
    compute_coverage,
    render_coverage_report,
    write_reports,
)


def test_compute_coverage_counts_recovered_and_missing() -> None:
    discovered_urls = {
        "http://www.somethingpositive.net/sp1.html",
        "http://www.somethingpositive.net/sp2.html",
        "http://www.somethingpositive.net/sp3.html",
        "http://www.somethingpositive.net/sp4.html",
    }
    provenance = [
        {"original_url": "http://www.somethingpositive.net/sp1.html", "status": "recovered"},
        {
            "original_url": "http://www.somethingpositive.net/sp2.html",
            "status": "skipped_existing",
        },
        {
            "original_url": "http://www.somethingpositive.net/sp3.html",
            "status": "fetch_failed_404",
        },
    ]

    summary = compute_coverage(discovered_urls, provenance)

    assert summary == CoverageSummary(
        total_discovered=4,
        recovered_count=2,
        missing_count=2,
        recovery_percentage=50.0,
    )


def test_build_gap_register_includes_missing_and_failed_urls() -> None:
    discovered_urls = {
        "http://www.somethingpositive.net/sp1.html",
        "http://www.somethingpositive.net/sp2.html",
    }
    provenance = [
        {
            "original_url": "http://www.somethingpositive.net/sp1.html",
            "status": "fetch_failed_500",
        }
    ]

    gaps = build_gap_register(discovered_urls, provenance)

    assert gaps == [
        GapEntry(
            original_url="http://www.somethingpositive.net/sp1.html",
            reason="fetch_failed_500",
            likely_sources="Expand timestamp window; verify alternate captures",
        ),
        GapEntry(
            original_url="http://www.somethingpositive.net/sp2.html",
            reason="missing_provenance_record",
            likely_sources="Re-run discovery; check older captures and mirrors",
        ),
    ]


def test_render_coverage_report_contains_required_sections() -> None:
    summary = CoverageSummary(
        total_discovered=10,
        recovered_count=8,
        missing_count=2,
        recovery_percentage=80.0,
    )

    rendered = render_coverage_report(
        summary,
        date_range_notes=[
            "2023-01-01 to 2025-02-01: High confidence",
            "2021-01-01 to 2022-12-31: Medium confidence",
        ],
    )

    assert "# Coverage Report" in rendered
    assert "- Total discovered pages/assets: 10" in rendered
    assert "- Recovered count: 8" in rendered
    assert "- Missing count: 2" in rendered
    assert "- Recovery percentage: 80.0%" in rendered
    assert "## Date-Range Confidence Notes" in rendered


def test_write_reports_creates_required_files(tmp_path: Path) -> None:
    summary = CoverageSummary(
        total_discovered=2,
        recovered_count=1,
        missing_count=1,
        recovery_percentage=50.0,
    )
    gaps = [
        GapEntry(
            original_url="http://www.somethingpositive.net/sp2.html",
            reason="missing_provenance_record",
            likely_sources="Re-run discovery; check older captures and mirrors",
        )
    ]
    provenance = [
        {
            "original_url": "http://www.somethingpositive.net/sp1.html",
            "timestamp": "20240201120000",
            "source_url": "https://web.archive.org/web/20240201120000id_/http://www.somethingpositive.net/sp1.html",
            "sha256": "abc",
            "status": "recovered",
        }
    ]

    write_reports(
        output_root=tmp_path,
        summary=summary,
        gaps=gaps,
        provenance_rows=provenance,
        date_range_notes=["2023-01-01 to 2025-02-01: High confidence"],
    )

    assert (tmp_path / "reports" / "coverage_report.md").exists()
    assert (tmp_path / "reports" / "gap_register.csv").exists()
    assert (tmp_path / "reports" / "provenance_manifest.csv").exists()
