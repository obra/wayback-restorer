from __future__ import annotations

from pathlib import Path

from sp_recovery.discovery import CaptureRecord
from sp_recovery.recover import (
    ProvenanceRecord,
    build_wayback_replay_url,
    local_relpath_from_original,
    recover_capture,
)


def test_local_relpath_from_original_is_deterministic() -> None:
    assert (
        local_relpath_from_original("http://www.somethingpositive.net/sp02012024.html")
        == "somethingpositive.net/sp02012024.html"
    )
    assert (
        local_relpath_from_original("http://somethingpositive.net/")
        == "somethingpositive.net/index.html"
    )
    assert (
        local_relpath_from_original("http://www.somethingpositive.net:80/sp02012024.html")
        == "somethingpositive.net/sp02012024.html"
    )
    assert (
        local_relpath_from_original("https://somethingpositive.net:443/sp02012024.html")
        == "somethingpositive.net/sp02012024.html"
    )


def test_build_wayback_replay_url_uses_id_mode() -> None:
    assert (
        build_wayback_replay_url(
            "20240201120000", "http://www.somethingpositive.net/sp02012024.html"
        )
        == "https://web.archive.org/web/20240201120000id_/http://www.somethingpositive.net/sp02012024.html"
    )


def test_recover_capture_skips_existing_files(tmp_path: Path) -> None:
    capture = CaptureRecord(
        timestamp="20240201120000",
        original="http://www.somethingpositive.net/sp02012024.html",
        mimetype="text/html",
        statuscode=200,
        digest="D",
    )
    existing_path = tmp_path / "somethingpositive.net" / "sp02012024.html"
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    existing_path.write_bytes(b"already here")

    def fetcher(_: str) -> tuple[int, bytes]:
        raise AssertionError("fetcher should not be called for existing files")

    result = recover_capture(capture, output_root=tmp_path, fetcher=fetcher)

    assert result.status == "skipped_existing"
    assert result.local_path.endswith("somethingpositive.net/sp02012024.html")


def test_recover_capture_emits_provenance_fields(tmp_path: Path) -> None:
    capture = CaptureRecord(
        timestamp="20240201120000",
        original="http://www.somethingpositive.net/sp02012024.html",
        mimetype="text/html",
        statuscode=200,
        digest="D",
    )

    def fetcher(_: str) -> tuple[int, bytes]:
        return (200, b"<html>hello</html>")

    result = recover_capture(capture, output_root=tmp_path, fetcher=fetcher)

    assert isinstance(result, ProvenanceRecord)
    payload = result.as_dict()
    assert payload["original_url"] == capture.original
    assert payload["timestamp"] == capture.timestamp
    assert payload["source_url"] == build_wayback_replay_url(capture.timestamp, capture.original)
    assert payload["status"] == "recovered"
    assert payload["sha256"]


def test_recover_capture_retries_after_transient_fetch_error(tmp_path: Path) -> None:
    capture = CaptureRecord(
        timestamp="20240201120000",
        original="http://www.somethingpositive.net/sp02012024.html",
        mimetype="text/html",
        statuscode=200,
        digest="D",
    )
    attempts = {"count": 0}

    def fetcher(_: str) -> tuple[int, bytes]:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise TimeoutError("temporary issue")
        return (200, b"<html>ok</html>")

    result = recover_capture(capture, output_root=tmp_path, fetcher=fetcher)

    assert attempts["count"] == 2
    assert result.status == "recovered"
