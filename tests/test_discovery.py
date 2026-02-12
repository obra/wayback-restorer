from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from sp_recovery.discovery import (
    CaptureRecord,
    build_cdx_query_url,
    choose_canonical_capture,
    parse_cdx_rows,
)


def test_parse_cdx_rows_builds_capture_records() -> None:
    rows = [
        ["timestamp", "original", "mimetype", "statuscode", "digest"],
        [
            "20240201000000",
            "http://www.somethingpositive.net/sp02012024.html",
            "text/html",
            "200",
            "ABC",
        ],
    ]

    parsed = parse_cdx_rows(rows)

    assert parsed == [
        CaptureRecord(
            timestamp="20240201000000",
            original="http://www.somethingpositive.net/sp02012024.html",
            mimetype="text/html",
            statuscode=200,
            digest="ABC",
        )
    ]


def test_build_cdx_query_url_adds_resume_key_only_when_present() -> None:
    url = build_cdx_query_url(
        url_pattern="somethingpositive.net/*",
        from_timestamp="20230101000000",
        to_timestamp="20250201000000",
        resume_key="opaque-key",
    )

    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert query["url"] == ["somethingpositive.net/*"]
    assert query["from"] == ["20230101000000"]
    assert query["to"] == ["20250201000000"]
    assert query["showResumeKey"] == ["true"]
    assert query["collapse"] == ["urlkey"]
    assert query["resumeKey"] == ["opaque-key"]


def test_choose_canonical_prefers_preferred_window_then_latest() -> None:
    captures = [
        CaptureRecord(
            timestamp="20221231120000",
            original="http://www.somethingpositive.net/sp12312022.html",
            mimetype="text/html",
            statuscode=200,
            digest="A",
        ),
        CaptureRecord(
            timestamp="20240201120000",
            original="http://www.somethingpositive.net/sp02012024.html",
            mimetype="text/html",
            statuscode=200,
            digest="B",
        ),
    ]

    canonical = choose_canonical_capture(captures)

    assert canonical is not None
    assert canonical.original == "http://www.somethingpositive.net/sp02012024.html"


def test_choose_canonical_prefers_200_over_non_200() -> None:
    captures = [
        CaptureRecord(
            timestamp="20240101120000",
            original="http://www.somethingpositive.net/sp01012024.html",
            mimetype="text/html",
            statuscode=500,
            digest="A",
        ),
        CaptureRecord(
            timestamp="20231231120000",
            original="http://www.somethingpositive.net/sp12312023.html",
            mimetype="text/html",
            statuscode=200,
            digest="B",
        ),
    ]

    canonical = choose_canonical_capture(captures)

    assert canonical is not None
    assert canonical.original == "http://www.somethingpositive.net/sp12312023.html"
