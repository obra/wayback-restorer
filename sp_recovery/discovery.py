"""CDX discovery and capture selection helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
DEFAULT_FIELDS = ("timestamp", "original", "mimetype", "statuscode", "digest")
# Preferred by Jesse: prioritize latest pre-outage captures first.
DEFAULT_PREFERRED_WINDOWS = (
    ("20230101000000", "20250201235959"),
    ("20210101000000", "20250201235959"),
)


@dataclass(frozen=True, slots=True)
class CaptureRecord:
    timestamp: str
    original: str
    mimetype: str
    statuscode: int
    digest: str | None = None


CDXFetcher = Callable[[str], list[list[str]]]


def parse_cdx_rows(rows: Sequence[Sequence[str]]) -> list[CaptureRecord]:
    if not rows:
        return []

    field_names: Sequence[str]
    data_rows: Sequence[Sequence[str]]

    first_row = rows[0]
    if first_row and first_row[0] == "timestamp":
        field_names = first_row
        data_rows = rows[1:]
    else:
        field_names = DEFAULT_FIELDS
        data_rows = rows

    parsed: list[CaptureRecord] = []
    for row in data_rows:
        row_map = {
            field_names[index]: value
            for index, value in enumerate(row)
            if index < len(field_names)
        }
        if "timestamp" not in row_map or "original" not in row_map:
            continue

        parsed.append(
            CaptureRecord(
                timestamp=row_map["timestamp"],
                original=row_map["original"],
                mimetype=row_map.get("mimetype", "application/octet-stream"),
                statuscode=int(row_map.get("statuscode", "0") or 0),
                digest=row_map.get("digest"),
            )
        )

    return parsed


def build_cdx_query_url(
    *,
    url_pattern: str,
    from_timestamp: str,
    to_timestamp: str,
    resume_key: str | None = None,
    fields: Iterable[str] = DEFAULT_FIELDS,
    limit: int | None = None,
) -> str:
    params: dict[str, str] = {
        "url": url_pattern,
        "from": from_timestamp,
        "to": to_timestamp,
        "output": "json",
        "fl": ",".join(fields),
        "showResumeKey": "true",
        "matchType": "domain",
        "filter": "statuscode:200",
        "collapse": "urlkey",
    }
    if resume_key:
        params["resumeKey"] = resume_key
    if limit and limit > 0:
        params["limit"] = str(limit)

    return f"{CDX_ENDPOINT}?{urlencode(params)}"


def _window_rank(timestamp: str, preferred_windows: Sequence[tuple[str, str]]) -> int:
    for index, (start, end) in enumerate(preferred_windows):
        if start <= timestamp <= end:
            return index
    return len(preferred_windows)


def _mimetype_rank(mimetype: str) -> int:
    if mimetype == "text/html" or mimetype.startswith("image/"):
        return 0
    return 1


def choose_canonical_capture(
    captures: Sequence[CaptureRecord],
    *,
    preferred_windows: Sequence[tuple[str, str]] = DEFAULT_PREFERRED_WINDOWS,
) -> CaptureRecord | None:
    if not captures:
        return None

    def rank(record: CaptureRecord) -> tuple[int, int, int, int]:
        status_rank = 0 if record.statuscode == 200 else 1
        mime_rank = _mimetype_rank(record.mimetype)
        window_rank = _window_rank(record.timestamp, preferred_windows)
        # Prefer newer captures within the same quality/window bucket.
        recency_rank = -int(record.timestamp)
        return (status_rank, mime_rank, window_rank, recency_rank)

    return min(captures, key=rank)


def canonicalize_by_original_url(
    captures: Sequence[CaptureRecord],
    *,
    preferred_windows: Sequence[tuple[str, str]] = DEFAULT_PREFERRED_WINDOWS,
) -> dict[str, CaptureRecord]:
    grouped: dict[str, list[CaptureRecord]] = {}
    for capture in captures:
        grouped.setdefault(capture.original, []).append(capture)

    canonical: dict[str, CaptureRecord] = {}
    for original_url, options in grouped.items():
        selected = choose_canonical_capture(options, preferred_windows=preferred_windows)
        if selected is not None:
            canonical[original_url] = selected

    return canonical


def capture_to_dict(capture: CaptureRecord) -> dict[str, Any]:
    return {
        "timestamp": capture.timestamp,
        "original": capture.original,
        "mimetype": capture.mimetype,
        "statuscode": capture.statuscode,
        "digest": capture.digest or "",
    }


def capture_from_dict(payload: dict[str, Any]) -> CaptureRecord:
    return CaptureRecord(
        timestamp=str(payload["timestamp"]),
        original=str(payload["original"]),
        mimetype=str(payload.get("mimetype", "application/octet-stream")),
        statuscode=int(payload.get("statuscode", 0)),
        digest=str(payload.get("digest") or "") or None,
    )


def _fetch_cdx_rows(url: str) -> list[list[str]]:
    request = Request(url, headers={"User-Agent": "sp-recovery/0.1 (+archive-friendly)"})
    with urlopen(request, timeout=60) as response:
        payload = response.read().decode("utf-8")
    parsed = json.loads(payload)
    if not isinstance(parsed, list):
        return []
    return parsed


def fetch_cdx_records(
    *,
    domain: str,
    from_timestamp: str,
    to_timestamp: str,
    limit: int,
    fetcher: CDXFetcher | None = None,
) -> list[CaptureRecord]:
    url = build_cdx_query_url(
        url_pattern=f"{domain}/*",
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        limit=limit if limit > 0 else None,
    )

    active_fetcher = fetcher or _fetch_cdx_rows
    try:
        rows = active_fetcher(url)
    except (HTTPError, URLError, TimeoutError):
        return []

    return parse_cdx_rows(rows)
