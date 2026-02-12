from __future__ import annotations

from pathlib import Path

from sp_recovery.config import RecoveryConfig


def test_effective_to_timestamp_respects_modern_cutoff() -> None:
    config = RecoveryConfig(
        domain="somethingpositive.net",
        from_date="2001-01-01",
        to_date="2025-02-01",
        modern_cutoff_date="2020-01-01",
        output_root=Path("output/demo"),
        max_canonical=0,
        request_interval_seconds=2.0,
        only_missing_urls=set(),
    )

    assert config.from_timestamp == "20010101000000"
    assert config.to_timestamp == "20250201235959"
    assert config.effective_to_timestamp == "20191231235959"
    assert config.canonical_host == "somethingpositive.net"
    assert config.equivalent_hosts == frozenset({"somethingpositive.net", "www.somethingpositive.net"})
