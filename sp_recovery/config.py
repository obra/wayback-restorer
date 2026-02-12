"""Configuration models and helpers for recovery runs."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_DOMAIN = "somethingpositive.net"
DEFAULT_FROM_DATE = "2001-01-01"
DEFAULT_TO_DATE = "2019-12-31"
DEFAULT_MODERN_CUTOFF_DATE = "2020-01-01"


@dataclass(frozen=True, slots=True)
class RecoveryConfig:
    domain: str
    from_date: str
    to_date: str
    output_root: Path
    max_canonical: int
    request_interval_seconds: float
    only_missing_urls: set[str]
    modern_cutoff_date: str = DEFAULT_MODERN_CUTOFF_DATE

    @property
    def from_timestamp(self) -> str:
        parsed = datetime.strptime(self.from_date, "%Y-%m-%d")
        return parsed.strftime("%Y%m%d000000")

    @property
    def to_timestamp(self) -> str:
        parsed = datetime.strptime(self.to_date, "%Y-%m-%d")
        return parsed.strftime("%Y%m%d235959")

    @property
    def effective_to_timestamp(self) -> str:
        to_date = datetime.strptime(self.to_date, "%Y-%m-%d")
        cutoff_start = datetime.strptime(self.modern_cutoff_date, "%Y-%m-%d")
        cutoff_last_allowed = cutoff_start - timedelta(days=1)
        effective = min(to_date, cutoff_last_allowed)
        return effective.strftime("%Y%m%d235959")


def load_missing_urls_from_gap_csv(path: Path | None) -> set[str]:
    if path is None:
        return set()
    if not path.exists():
        return set()

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {
            row.get("original_url", "").strip()
            for row in reader
            if row.get("original_url", "").strip()
        }
