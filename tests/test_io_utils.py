from __future__ import annotations

from pathlib import Path

from sp_recovery.io_utils import write_bytes


def test_write_bytes_creates_parent_dirs_and_writes_payload(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "path" / "asset.gif"

    write_bytes(target, b"GIF89a")

    assert target.exists()
    assert target.read_bytes() == b"GIF89a"


def test_write_bytes_replaces_existing_file_without_temp_leak(tmp_path: Path) -> None:
    target = tmp_path / "mirror" / "sp02012024.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"old")

    write_bytes(target, b"new")

    assert target.read_bytes() == b"new"
    leftovers = [
        path
        for path in target.parent.iterdir()
        if path.name.startswith(f".{target.name}.") and path.name.endswith(".tmp")
    ]
    assert leftovers == []
