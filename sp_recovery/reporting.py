"""Coverage, gap, and provenance reporting for recovery runs."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from sp_recovery.io_utils import ensure_parent_dir

RECOVERED_STATUSES = {"recovered", "skipped_existing"}


@dataclass(frozen=True, slots=True)
class CoverageSummary:
    total_discovered: int
    recovered_count: int
    missing_count: int
    recovery_percentage: float


@dataclass(frozen=True, slots=True)
class GapEntry:
    original_url: str
    reason: str
    likely_sources: str


def compute_coverage(
    discovered_urls: set[str],
    provenance_rows: Iterable[dict[str, str]],
) -> CoverageSummary:
    status_by_url = {
        row["original_url"]: row.get("status", "unknown")
        for row in provenance_rows
        if row.get("original_url")
    }

    recovered_count = sum(
        1
        for original_url in discovered_urls
        if status_by_url.get(original_url) in RECOVERED_STATUSES
    )
    total = len(discovered_urls)
    missing_count = total - recovered_count
    recovery_percentage = round((recovered_count / total) * 100, 2) if total else 0.0

    return CoverageSummary(
        total_discovered=total,
        recovered_count=recovered_count,
        missing_count=missing_count,
        recovery_percentage=recovery_percentage,
    )


def build_gap_register(
    discovered_urls: set[str],
    provenance_rows: Iterable[dict[str, str]],
) -> list[GapEntry]:
    status_by_url = {
        row["original_url"]: row.get("status", "unknown")
        for row in provenance_rows
        if row.get("original_url")
    }

    gaps: list[GapEntry] = []
    for original_url in sorted(discovered_urls):
        status = status_by_url.get(original_url)
        if status in RECOVERED_STATUSES:
            continue

        if status is None:
            gaps.append(
                GapEntry(
                    original_url=original_url,
                    reason="missing_provenance_record",
                    likely_sources="Re-run discovery; check older captures and mirrors",
                )
            )
            continue

        gaps.append(
            GapEntry(
                original_url=original_url,
                reason=status,
                likely_sources="Expand timestamp window; verify alternate captures",
            )
        )

    return gaps


def render_coverage_report(
    summary: CoverageSummary,
    *,
    date_range_notes: list[str],
) -> str:
    lines = [
        "# Coverage Report",
        "",
        "## Summary",
        f"- Total discovered pages/assets: {summary.total_discovered}",
        f"- Recovered count: {summary.recovered_count}",
        f"- Missing count: {summary.missing_count}",
        f"- Recovery percentage: {summary.recovery_percentage}%",
        "",
        "## Date-Range Confidence Notes",
    ]

    for note in date_range_notes:
        lines.append(f"- {note}")

    return "\n".join(lines) + "\n"


def _write_gap_csv(path: Path, gaps: list[GapEntry]) -> None:
    ensure_parent_dir(path)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["original_url", "reason", "likely_source_options"])
        for gap in gaps:
            writer.writerow([gap.original_url, gap.reason, gap.likely_sources])


def _write_provenance_csv(path: Path, provenance_rows: list[dict[str, str]]) -> None:
    ensure_parent_dir(path)
    columns = ["original_url", "timestamp", "source_url", "sha256", "status", "local_path"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in provenance_rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def write_reports(
    *,
    output_root: Path,
    summary: CoverageSummary,
    gaps: list[GapEntry],
    provenance_rows: list[dict[str, str]],
    date_range_notes: list[str],
) -> None:
    reports_dir = output_root / "reports"
    coverage_report = reports_dir / "coverage_report.md"
    gap_register = reports_dir / "gap_register.csv"
    provenance_manifest = reports_dir / "provenance_manifest.csv"

    ensure_parent_dir(coverage_report)
    coverage_report.write_text(
        render_coverage_report(summary, date_range_notes=date_range_notes),
        encoding="utf-8",
    )
    _write_gap_csv(gap_register, gaps)
    _write_provenance_csv(provenance_manifest, provenance_rows)
