"""End-to-end recovery pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Sequence
from urllib.parse import urlparse

from sp_recovery.config import RecoveryConfig
from sp_recovery.discovery import (
    CaptureRecord,
    canonicalize_by_original_url,
    capture_to_dict,
    fetch_cdx_records,
)
from sp_recovery.io_utils import read_jsonl, write_jsonl
from sp_recovery.recover import Fetcher, ProvenanceRecord, recover_captures
from sp_recovery.reporting import build_gap_register, compute_coverage, write_reports
from sp_recovery.rewrite import rewrite_recovered_html_files


@dataclass(frozen=True, slots=True)
class PipelineRunResult:
    discovered_count: int
    canonical_count: int
    recovered_count: int


_STRIP_PAGE_RE = re.compile(r"^/sp(?P<month>\d{2})(?P<day>\d{2})(?P<year>\d{4})\.html$", re.IGNORECASE)
_STRIP_ASSET_RE = re.compile(
    r"^/arch/sp(?P<month>\d{2})(?P<day>\d{2})(?P<year>\d{4})\.[A-Za-z0-9]+$",
    re.IGNORECASE,
)
_FIRST_COMIC_PAGE_RE = re.compile(r"^/1stcomic-page(?P<page>\d+)\.html$", re.IGNORECASE)
_ARCHIVE_YEAR_RE = re.compile(r"^/archive/(?P<year>\d{4})/?$")


def _record_in_window(record: CaptureRecord, config: RecoveryConfig) -> bool:
    parsed = urlparse(record.original)
    if parsed.query or parsed.fragment:
        return False
    return config.from_timestamp <= record.timestamp <= config.effective_to_timestamp


def _recovery_order_key(record: CaptureRecord) -> tuple[int, tuple[int, int, int], int, str]:
    parsed = urlparse(record.original)
    path = parsed.path or "/"

    strip_page = _STRIP_PAGE_RE.match(path)
    if strip_page:
        year = int(strip_page.group("year"))
        month = int(strip_page.group("month"))
        day = int(strip_page.group("day"))
        return (0, (year, month, day), int(record.timestamp), record.original)

    strip_asset = _STRIP_ASSET_RE.match(path)
    if strip_asset:
        year = int(strip_asset.group("year"))
        month = int(strip_asset.group("month"))
        day = int(strip_asset.group("day"))
        return (1, (year, month, day), int(record.timestamp), record.original)

    first_comic = _FIRST_COMIC_PAGE_RE.match(path)
    if first_comic:
        page_number = int(first_comic.group("page"))
        return (2, (2001, 1, page_number), int(record.timestamp), record.original)

    archive_year = _ARCHIVE_YEAR_RE.match(path)
    if archive_year:
        year = int(archive_year.group("year"))
        return (3, (year, 1, 1), int(record.timestamp), record.original)

    if path in {"/", "/index.html"}:
        return (6, (9999, 12, 31), int(record.timestamp), record.original)

    if path.lower().endswith(".html") or path.endswith("/"):
        return (4, (9999, 12, 31), int(record.timestamp), record.original)

    return (5, (9999, 12, 31), int(record.timestamp), record.original)


def _capture_rows_to_records(rows: Sequence[dict[str, object]]) -> list[CaptureRecord]:
    converted: list[CaptureRecord] = []
    for row in rows:
        converted.append(
            CaptureRecord(
                timestamp=str(row.get("timestamp", "")),
                original=str(row.get("original", "")),
                mimetype=str(row.get("mimetype", "application/octet-stream")),
                statuscode=int(row.get("statuscode", 0) or 0),
                digest=str(row.get("digest") or "") or None,
            )
        )
    return converted


def _provenance_from_rows(rows: Sequence[dict[str, object]]) -> list[ProvenanceRecord]:
    parsed: list[ProvenanceRecord] = []
    for row in rows:
        parsed.append(
            ProvenanceRecord(
                original_url=str(row.get("original_url", "")),
                timestamp=str(row.get("timestamp", "")),
                source_url=str(row.get("source_url", "")),
                local_path=str(row.get("local_path", "")),
                sha256=str(row.get("sha256", "")),
                status=str(row.get("status", "unknown")),
            )
        )
    return parsed


def discover_phase(config: RecoveryConfig) -> tuple[list[CaptureRecord], list[CaptureRecord]]:
    discovered = fetch_cdx_records(
        domain=config.domain,
        from_timestamp=config.from_timestamp,
        to_timestamp=config.effective_to_timestamp,
        limit=max(config.max_canonical * 20, 5000) if config.max_canonical else 50000,
    )

    canonical_map = canonicalize_by_original_url(discovered)
    canonical_all = sorted(canonical_map.values(), key=_recovery_order_key)

    if config.only_missing_urls:
        canonical_all = [
            record
            for record in canonical_all
            if record.original in config.only_missing_urls
        ]

    if config.max_canonical > 0:
        canonical_selected = canonical_all[: config.max_canonical]
    else:
        canonical_selected = canonical_all

    return discovered, canonical_selected


def recover_phase(
    config: RecoveryConfig,
    canonical_records: Sequence[CaptureRecord],
    *,
    fetcher: Fetcher | None = None,
) -> list[ProvenanceRecord]:
    return recover_captures(
        canonical_records,
        output_root=config.output_root,
        request_interval_seconds=config.request_interval_seconds,
        fetcher=fetcher,
    )


def report_phase(
    config: RecoveryConfig,
    canonical_records: Sequence[CaptureRecord],
    provenance_records: Sequence[ProvenanceRecord],
) -> None:
    discovered_urls = {record.original for record in canonical_records}
    provenance_rows = [record.as_dict() for record in provenance_records]

    summary = compute_coverage(discovered_urls, provenance_rows)
    gaps = build_gap_register(discovered_urls, provenance_rows)

    write_reports(
        output_root=config.output_root,
        summary=summary,
        gaps=gaps,
        provenance_rows=provenance_rows,
        date_range_notes=[
            (
                f"{config.from_date} to {config.to_date}: Requested query window "
                f"(captures on/after {config.modern_cutoff_date} are excluded)."
            ),
            "Older captures can be queried in targeted gap-focused reruns.",
        ],
    )


def run_pipeline(
    config: RecoveryConfig,
    *,
    discovered_records: Sequence[CaptureRecord] | None = None,
    fetcher: Fetcher | None = None,
) -> PipelineRunResult:
    state_dir = config.output_root / "state"
    discovered_file = state_dir / "discovered_captures.jsonl"
    canonical_file = state_dir / "canonical_urls.jsonl"
    provenance_file = state_dir / "provenance.jsonl"

    if discovered_records is None:
        discovered, canonical = discover_phase(config)
    else:
        discovered = [record for record in discovered_records if _record_in_window(record, config)]
        canonical_map = canonicalize_by_original_url(discovered)
        canonical = sorted(canonical_map.values(), key=_recovery_order_key)
        if config.only_missing_urls:
            canonical = [record for record in canonical if record.original in config.only_missing_urls]
        if config.max_canonical > 0:
            canonical = canonical[: config.max_canonical]

    write_jsonl(discovered_file, [capture_to_dict(record) for record in discovered])
    write_jsonl(canonical_file, [capture_to_dict(record) for record in canonical])

    recovered = recover_phase(config, canonical, fetcher=fetcher)
    write_jsonl(provenance_file, [record.as_dict() for record in recovered])

    rewrite_recovered_html_files(
        config.output_root,
        recovered,
        unresolved_csv_path=state_dir / "unresolved_links.csv",
    )

    report_phase(config, canonical, recovered)

    return PipelineRunResult(
        discovered_count=len(discovered),
        canonical_count=len(canonical),
        recovered_count=sum(1 for row in recovered if row.status in {"recovered", "skipped_existing"}),
    )


def run_report_only(config: RecoveryConfig) -> None:
    state_dir = config.output_root / "state"
    canonical_rows = read_jsonl(state_dir / "canonical_urls.jsonl")
    provenance_rows = read_jsonl(state_dir / "provenance.jsonl")

    canonical_records = _capture_rows_to_records(canonical_rows)
    provenance_records = _provenance_from_rows(provenance_rows)
    report_phase(config, canonical_records, provenance_records)
