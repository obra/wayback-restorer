"""Artifact recovery from canonical archive captures."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
from urllib.request import urlopen

from sp_recovery.discovery import CaptureRecord
from sp_recovery.io_utils import sha256_hex, write_bytes

Fetcher = Callable[[str], tuple[int, bytes]]


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


def local_relpath_from_original(original_url: str) -> str:
    parsed = urlparse(original_url)
    host = parsed.netloc
    path = parsed.path or "/"
    if path.endswith("/"):
        path = f"{path}index.html"

    normalized_path = path.lstrip("/")
    return f"{host}/{normalized_path}"


def _default_fetcher(source_url: str) -> tuple[int, bytes]:
    with urlopen(source_url, timeout=30) as response:
        return response.status, response.read()


def recover_capture(
    capture: CaptureRecord,
    *,
    output_root: Path,
    fetcher: Fetcher | None = None,
) -> ProvenanceRecord:
    local_relpath = local_relpath_from_original(capture.original)
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
    status_code, payload = active_fetcher(source_url)

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
