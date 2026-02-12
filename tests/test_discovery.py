from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from sp_recovery.discovery import (
    CaptureRecord,
    build_cdx_query_url,
    canonicalize_by_original_url,
    choose_canonical_capture,
    fetch_cdx_records,
    parse_cdx_rows,
    split_cdx_rows_and_resume_key,
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


def test_canonicalize_by_original_url_dedupes_www_and_default_port() -> None:
    captures = [
        CaptureRecord(
            timestamp="20020206141527",
            original="http://www.somethingpositive.net:80/sp01012002.html",
            mimetype="text/html",
            statuscode=200,
            digest="A",
        ),
        CaptureRecord(
            timestamp="20020206142000",
            original="http://somethingpositive.net/sp01012002.html",
            mimetype="text/html",
            statuscode=200,
            digest="B",
        ),
    ]

    canonical = canonicalize_by_original_url(captures)

    assert len(canonical) == 1
    selected = next(iter(canonical.values()))
    assert selected.original in {
        "http://www.somethingpositive.net:80/sp01012002.html",
        "http://somethingpositive.net/sp01012002.html",
    }


def test_split_cdx_rows_and_resume_key_handles_wayback_json_shape() -> None:
    payload = [
        ["timestamp", "original", "mimetype", "statuscode", "digest"],
        ["20020206001945", "http://www.somethingpositive.net:80/", "text/html", "200", "A"],
        [],
        ["opaque-resume-key"],
    ]

    rows, resume_key = split_cdx_rows_and_resume_key(payload)

    assert rows == [
        ["timestamp", "original", "mimetype", "statuscode", "digest"],
        ["20020206001945", "http://www.somethingpositive.net:80/", "text/html", "200", "A"],
    ]
    assert resume_key == "opaque-resume-key"


def test_fetch_cdx_records_paginates_with_resume_key_until_limit() -> None:
    calls: list[str] = []

    def fetcher(url: str) -> list[object]:
        calls.append(url)
        query = parse_qs(urlparse(url).query)
        resume_key = query.get("resumeKey", [None])[0]
        if resume_key is None:
            return [
                ["timestamp", "original", "mimetype", "statuscode", "digest"],
                ["20020206001945", "http://www.somethingpositive.net:80/", "text/html", "200", "A"],
                ["20020206002000", "http://www.somethingpositive.net:80/sp01012002.html", "text/html", "200", "B"],
                [],
                ["k1"],
            ]
        if resume_key == "k1":
            return [
                ["timestamp", "original", "mimetype", "statuscode", "digest"],
                ["20020206003000", "http://www.somethingpositive.net:80/sp01022002.html", "text/html", "200", "C"],
                [],
                ["k2"],
            ]
        raise AssertionError(f"unexpected resume key: {resume_key}")

    records = fetch_cdx_records(
        domain="somethingpositive.net",
        from_timestamp="20020101000000",
        to_timestamp="20021231235959",
        limit=3,
        fetcher=fetcher,
    )

    assert len(records) == 3
    assert [record.original for record in records] == [
        "http://www.somethingpositive.net:80/",
        "http://www.somethingpositive.net:80/sp01012002.html",
        "http://www.somethingpositive.net:80/sp01022002.html",
    ]
    assert len(calls) == 2
    first_query = parse_qs(urlparse(calls[0]).query)
    second_query = parse_qs(urlparse(calls[1]).query)
    assert first_query["limit"] == ["3"]
    assert "resumeKey" not in first_query
    assert second_query["resumeKey"] == ["k1"]
    assert second_query["limit"] == ["1"]


def test_fetch_cdx_records_stops_when_resume_key_repeats() -> None:
    calls: list[str] = []

    def fetcher(url: str) -> list[object]:
        calls.append(url)
        query = parse_qs(urlparse(url).query)
        resume_key = query.get("resumeKey", [None])[0]
        if resume_key is None:
            return [
                ["timestamp", "original", "mimetype", "statuscode", "digest"],
                ["20020206001945", "http://www.somethingpositive.net:80/", "text/html", "200", "A"],
                [],
                ["k1"],
            ]
        return [
            ["timestamp", "original", "mimetype", "statuscode", "digest"],
            ["20020206002000", "http://www.somethingpositive.net:80/sp01012002.html", "text/html", "200", "B"],
            [],
            ["k1"],
        ]

    records = fetch_cdx_records(
        domain="somethingpositive.net",
        from_timestamp="20020101000000",
        to_timestamp="20021231235959",
        limit=50,
        fetcher=fetcher,
    )

    assert len(records) == 2
    assert len(calls) == 2
