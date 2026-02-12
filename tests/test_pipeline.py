from __future__ import annotations

import json
from pathlib import Path

from sp_recovery.config import RecoveryConfig
from sp_recovery.discovery import CaptureRecord
from sp_recovery.pipeline import run_pipeline


def test_run_pipeline_creates_mirror_state_and_reports(tmp_path: Path) -> None:
    captures = [
        CaptureRecord(
            timestamp="20180201120000",
            original="http://www.somethingpositive.net/sp02012018.html",
            mimetype="text/html",
            statuscode=200,
            digest="A",
        ),
        CaptureRecord(
            timestamp="20180201120000",
            original="http://www.somethingpositive.net/arch/sp02012018.gif",
            mimetype="image/gif",
            statuscode=200,
            digest="B",
        ),
    ]

    def fetcher(url: str) -> tuple[int, bytes]:
        if url.endswith(".html"):
            return (200, b'<html><body><img src="arch/sp02012018.gif"></body></html>')
        return (200, b"GIF89a")

    config = RecoveryConfig(
        domain="somethingpositive.net",
        from_date="2001-01-01",
        to_date="2019-12-31",
        output_root=tmp_path,
        max_canonical=50,
        request_interval_seconds=0.0,
        only_missing_urls=set(),
        modern_cutoff_date="2020-01-01",
    )

    run_pipeline(config, discovered_records=captures, fetcher=fetcher)

    assert (tmp_path / "state" / "discovered_captures.jsonl").exists()
    assert (tmp_path / "state" / "canonical_urls.jsonl").exists()
    assert (tmp_path / "state" / "provenance.jsonl").exists()

    assert (tmp_path / "reports" / "coverage_report.md").exists()
    assert (tmp_path / "reports" / "gap_register.csv").exists()
    assert (tmp_path / "reports" / "provenance_manifest.csv").exists()

    html_file = tmp_path / "somethingpositive.net" / "sp02012018.html"
    assert html_file.exists()
    assert b"/somethingpositive.net/arch/sp02012018.gif" in html_file.read_bytes()


def test_run_pipeline_can_target_only_missing_urls(tmp_path: Path) -> None:
    captures = [
        CaptureRecord(
            timestamp="20181201120000",
            original="http://www.somethingpositive.net/sp1.html",
            mimetype="text/html",
            statuscode=200,
            digest="A",
        ),
        CaptureRecord(
            timestamp="20181201120000",
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
        from_date="2001-01-01",
        to_date="2019-12-31",
        output_root=tmp_path,
        max_canonical=50,
        request_interval_seconds=0.0,
        only_missing_urls={"http://www.somethingpositive.net/sp2.html"},
        modern_cutoff_date="2020-01-01",
    )

    run_pipeline(config, discovered_records=captures, fetcher=fetcher)

    provenance_lines = (tmp_path / "state" / "provenance.jsonl").read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(line) for line in provenance_lines]

    assert len(parsed) == 1
    assert parsed[0]["original_url"] == "http://www.somethingpositive.net/sp2.html"



def test_run_pipeline_excludes_post_modern_cutoff_captures(tmp_path: Path) -> None:
    captures = [
        CaptureRecord(
            timestamp="20181201120000",
            original="http://www.somethingpositive.net/sp12012018.html",
            mimetype="text/html",
            statuscode=200,
            digest="OLD",
        ),
        CaptureRecord(
            timestamp="20240201120000",
            original="https://somethingpositive.net/comic/new-scheme/",
            mimetype="text/html",
            statuscode=200,
            digest="NEW",
        ),
    ]

    def fetcher(url: str) -> tuple[int, bytes]:
        return (200, b"<html></html>")

    config = RecoveryConfig(
        domain="somethingpositive.net",
        from_date="2001-01-01",
        to_date="2025-02-01",
        modern_cutoff_date="2020-01-01",
        output_root=tmp_path,
        max_canonical=50,
        request_interval_seconds=0.0,
        only_missing_urls=set(),
    )

    run_pipeline(config, discovered_records=captures, fetcher=fetcher)

    provenance_lines = (tmp_path / "state" / "provenance.jsonl").read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(line) for line in provenance_lines]

    assert len(parsed) == 1
    assert parsed[0]["original_url"] == "http://www.somethingpositive.net/sp12012018.html"

def test_run_pipeline_prioritizes_strip_pages_before_archive_indexes(tmp_path: Path) -> None:
    captures = [
        CaptureRecord(
            timestamp="20181201120000",
            original="http://www.somethingpositive.net/archive/2001/",
            mimetype="text/html",
            statuscode=200,
            digest="ARCHIVE",
        ),
        CaptureRecord(
            timestamp="20181201120000",
            original="http://www.somethingpositive.net/sp01012001.html",
            mimetype="text/html",
            statuscode=200,
            digest="STRIP",
        ),
    ]

    def fetcher(_: str) -> tuple[int, bytes]:
        return (200, b"<html></html>")

    config = RecoveryConfig(
        domain="somethingpositive.net",
        from_date="2001-01-01",
        to_date="2019-12-31",
        modern_cutoff_date="2020-01-01",
        output_root=tmp_path,
        max_canonical=1,
        request_interval_seconds=0.0,
        only_missing_urls=set(),
    )

    run_pipeline(config, discovered_records=captures, fetcher=fetcher)

    provenance_lines = (tmp_path / "state" / "provenance.jsonl").read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(line) for line in provenance_lines]

    assert len(parsed) == 1
    assert parsed[0]["original_url"] == "http://www.somethingpositive.net/sp01012001.html"


def test_run_pipeline_orders_strips_by_comic_date_ascending(tmp_path: Path) -> None:
    captures = [
        CaptureRecord(
            timestamp="20181201120000",
            original="http://www.somethingpositive.net/sp12312001.html",
            mimetype="text/html",
            statuscode=200,
            digest="LATE2001",
        ),
        CaptureRecord(
            timestamp="20181201120000",
            original="http://www.somethingpositive.net/sp01012002.html",
            mimetype="text/html",
            statuscode=200,
            digest="EARLY2002",
        ),
    ]

    def fetcher(_: str) -> tuple[int, bytes]:
        return (200, b"<html></html>")

    config = RecoveryConfig(
        domain="somethingpositive.net",
        from_date="2001-01-01",
        to_date="2019-12-31",
        modern_cutoff_date="2020-01-01",
        output_root=tmp_path,
        max_canonical=2,
        request_interval_seconds=0.0,
        only_missing_urls=set(),
    )

    run_pipeline(config, discovered_records=captures, fetcher=fetcher)

    provenance_lines = (tmp_path / "state" / "provenance.jsonl").read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(line) for line in provenance_lines]

    assert [row["original_url"] for row in parsed] == [
        "http://www.somethingpositive.net/sp12312001.html",
        "http://www.somethingpositive.net/sp01012002.html",
    ]

def test_run_pipeline_ignores_query_and_fragment_url_variants(tmp_path: Path) -> None:
    captures = [
        CaptureRecord(
            timestamp="20181201120000",
            original="http://www.somethingpositive.net/#lastfive",
            mimetype="text/html",
            statuscode=200,
            digest="A",
        ),
        CaptureRecord(
            timestamp="20181201120000",
            original="http://www.somethingpositive.net/?tracking=1",
            mimetype="text/html",
            statuscode=200,
            digest="B",
        ),
        CaptureRecord(
            timestamp="20181201120000",
            original="http://www.somethingpositive.net/1stcomic-page1.html",
            mimetype="text/html",
            statuscode=200,
            digest="C",
        ),
    ]

    def fetcher(_: str) -> tuple[int, bytes]:
        return (200, b"<html></html>")

    config = RecoveryConfig(
        domain="somethingpositive.net",
        from_date="2001-01-01",
        to_date="2019-12-31",
        modern_cutoff_date="2020-01-01",
        output_root=tmp_path,
        max_canonical=10,
        request_interval_seconds=0.0,
        only_missing_urls=set(),
    )

    run_pipeline(config, discovered_records=captures, fetcher=fetcher)

    provenance_lines = (tmp_path / "state" / "provenance.jsonl").read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(line) for line in provenance_lines]

    assert [row["original_url"] for row in parsed] == [
        "http://www.somethingpositive.net/1stcomic-page1.html",
    ]


def test_run_pipeline_prioritizes_firstcomic_pages_before_homepage(tmp_path: Path) -> None:
    captures = [
        CaptureRecord(
            timestamp="20181201120000",
            original="http://www.somethingpositive.net/",
            mimetype="text/html",
            statuscode=200,
            digest="HOME",
        ),
        CaptureRecord(
            timestamp="20181201120000",
            original="http://www.somethingpositive.net/1stcomic-page1.html",
            mimetype="text/html",
            statuscode=200,
            digest="C1",
        ),
    ]

    def fetcher(_: str) -> tuple[int, bytes]:
        return (200, b"<html></html>")

    config = RecoveryConfig(
        domain="somethingpositive.net",
        from_date="2001-01-01",
        to_date="2019-12-31",
        modern_cutoff_date="2020-01-01",
        output_root=tmp_path,
        max_canonical=1,
        request_interval_seconds=0.0,
        only_missing_urls=set(),
    )

    run_pipeline(config, discovered_records=captures, fetcher=fetcher)

    provenance_lines = (tmp_path / "state" / "provenance.jsonl").read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(line) for line in provenance_lines]

    assert len(parsed) == 1
    assert parsed[0]["original_url"] == "http://www.somethingpositive.net/1stcomic-page1.html"


def test_run_pipeline_recovers_referenced_strip_images(tmp_path: Path) -> None:
    captures = [
        CaptureRecord(
            timestamp="20020206141527",
            original="http://www.somethingpositive.net:80/sp01012002.html",
            mimetype="text/html",
            statuscode=200,
            digest="PAGE",
        )
    ]

    def fetcher(url: str) -> tuple[int, bytes]:
        if url.endswith("/http://www.somethingpositive.net:80/sp01012002.html"):
            return (200, b'<html><body><img src="arch/sp01012002.gif"></body></html>')
        if url.endswith("/http://somethingpositive.net/arch/sp01012002.gif"):
            return (200, b"GIF89a")
        return (404, b"")

    config = RecoveryConfig(
        domain="somethingpositive.net",
        from_date="2001-01-01",
        to_date="2019-12-31",
        modern_cutoff_date="2020-01-01",
        output_root=tmp_path,
        max_canonical=1,
        request_interval_seconds=0.0,
        only_missing_urls=set(),
    )

    run_pipeline(config, discovered_records=captures, fetcher=fetcher)

    image_path = tmp_path / "somethingpositive.net" / "arch" / "sp01012002.gif"
    assert image_path.exists()

    provenance_lines = (tmp_path / "state" / "provenance.jsonl").read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(line) for line in provenance_lines]
    assert any(row["local_path"] == "somethingpositive.net/arch/sp01012002.gif" for row in parsed)


def test_run_pipeline_recovers_root_relative_strip_images(tmp_path: Path) -> None:
    captures = [
        CaptureRecord(
            timestamp="20020206141527",
            original="http://www.somethingpositive.net:80/sp01012002.html",
            mimetype="text/html",
            statuscode=200,
            digest="PAGE",
        )
    ]

    def fetcher(url: str) -> tuple[int, bytes]:
        if url.endswith("/http://www.somethingpositive.net:80/sp01012002.html"):
            return (200, b'<html><body><img src="/arch/sp01012002.gif"></body></html>')
        if url.endswith("/http://somethingpositive.net/arch/sp01012002.gif"):
            return (200, b"GIF89a")
        return (404, b"")

    config = RecoveryConfig(
        domain="somethingpositive.net",
        from_date="2001-01-01",
        to_date="2019-12-31",
        modern_cutoff_date="2020-01-01",
        output_root=tmp_path,
        max_canonical=1,
        request_interval_seconds=0.0,
        only_missing_urls=set(),
    )

    run_pipeline(config, discovered_records=captures, fetcher=fetcher)

    image_path = tmp_path / "somethingpositive.net" / "arch" / "sp01012002.gif"
    assert image_path.exists()
