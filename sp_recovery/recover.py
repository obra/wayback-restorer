"""Artifact recovery from canonical archive captures."""

from __future__ import annotations

import time
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from sp_recovery.discovery import CaptureRecord
from sp_recovery.io_utils import sha256_hex, write_bytes
from sp_recovery.url_utils import (
    DEFAULT_CANONICAL_SITE_HOST,
    DEFAULT_EQUIVALENT_SITE_HOSTS,
    canonicalize_site_host,
)

Fetcher = Callable[[str], tuple[int, bytes]]
ProvenanceCallback = Callable[["ProvenanceRecord"], None]
DEFAULT_FETCH_RETRIES = 3


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    original_url: str
    timestamp: str
    source_url: str
    local_path: str
    sha256: str
    status: str

    def as_dict(self) -> dict[str, str]:
        return {
            "original_url": self.original_url,
            "timestamp": self.timestamp,
            "source_url": self.source_url,
            "local_path": self.local_path,
            "sha256": self.sha256,
            "status": self.status,
        }


def build_wayback_replay_url(timestamp: str, original_url: str) -> str:
    return f"https://web.archive.org/web/{timestamp}id_/{original_url}"


def local_relpath_from_original(
    original_url: str,
    *,
    canonical_host: str = DEFAULT_CANONICAL_SITE_HOST,
    equivalent_hosts: Collection[str] = DEFAULT_EQUIVALENT_SITE_HOSTS,
) -> str:
    parsed = urlparse(original_url)
    host = canonicalize_site_host(
        parsed.netloc,
        canonical_host=canonical_host,
        equivalent_hosts=equivalent_hosts,
    )
    path = parsed.path or "/"
    if path.endswith("/"):
        path = f"{path}index.html"

    normalized_path = path.lstrip("/")
    return f"{host}/{normalized_path}"


def _default_fetcher(source_url: str) -> tuple[int, bytes]:
    request = Request(source_url, headers={"User-Agent": "sp-recovery/0.1 (+archive-friendly)"})
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


def recover_capture(
    capture: CaptureRecord,
    *,
    output_root: Path,
    fetcher: Fetcher | None = None,
    max_retries: int = DEFAULT_FETCH_RETRIES,
    canonical_host: str = DEFAULT_CANONICAL_SITE_HOST,
    equivalent_hosts: Collection[str] = DEFAULT_EQUIVALENT_SITE_HOSTS,
) -> ProvenanceRecord:
    local_relpath = local_relpath_from_original(
        capture.original,
        canonical_host=canonical_host,
        equivalent_hosts=equivalent_hosts,
    )
    destination = output_root / local_relpath
    source_url = build_wayback_replay_url(capture.timestamp, capture.original)

    if destination.exists() and destination.stat().st_size > 0:
        payload = destination.read_bytes()
        return ProvenanceRecord(
            original_url=capture.original,
            timestamp=capture.timestamp,
            source_url=source_url,
            local_path=local_relpath,
            sha256=sha256_hex(payload),
            status="skipped_existing",
        )

    active_fetcher = fetcher or _default_fetcher
    attempts = max(1, max_retries)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            status_code, payload = active_fetcher(source_url)
            break
        except Exception as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(0.5)
            continue
    else:
        return ProvenanceRecord(
            original_url=capture.original,
            timestamp=capture.timestamp,
            source_url=source_url,
            local_path=local_relpath,
            sha256=f"{type(last_error).__name__}:{last_error}" if last_error else "",
            status="fetch_error",
        )

    status = "recovered" if status_code == 200 else f"fetch_failed_{status_code}"
    if status_code == 200:
        write_bytes(destination, payload)

    return ProvenanceRecord(
        original_url=capture.original,
        timestamp=capture.timestamp,
        source_url=source_url,
        local_path=local_relpath,
        sha256=sha256_hex(payload),
        status=status,
    )


def recover_captures(
    captures: Sequence[CaptureRecord],
    *,
    output_root: Path,
    request_interval_seconds: float,
    fetcher: Fetcher | None = None,
    canonical_host: str = DEFAULT_CANONICAL_SITE_HOST,
    equivalent_hosts: Collection[str] = DEFAULT_EQUIVALENT_SITE_HOSTS,
    on_record: ProvenanceCallback | None = None,
) -> list[ProvenanceRecord]:
    recovered: list[ProvenanceRecord] = []
    for index, capture in enumerate(captures):
        if index > 0 and request_interval_seconds > 0:
            time.sleep(request_interval_seconds)

        record = recover_capture(
            capture,
            output_root=output_root,
            fetcher=fetcher,
            canonical_host=canonical_host,
            equivalent_hosts=equivalent_hosts,
        )
        recovered.append(record)
        if on_record is not None:
            on_record(record)

    return recovered
