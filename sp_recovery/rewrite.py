"""HTML rewriting utilities for standalone mirror browsing."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from urllib.parse import urljoin, urlparse

from sp_recovery.io_utils import ensure_parent_dir
from sp_recovery.recover import ProvenanceRecord, local_relpath_from_original
from sp_recovery.url_utils import canonical_internal_url, is_internal_site_netloc

_ATTR_PATTERN = re.compile(
    r"(?P<attr>href|src)=(?P<quote>['\"])(?P<value>.*?)(?P=quote)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class RewriteResult:
    html: str
    unresolved_targets: list[tuple[str, str]]


@dataclass(frozen=True, slots=True)
class InternalTarget:
    normalized_url: str
    local_path: str
    fragment: str


def _extract_wayback_original(absolute_url: str) -> str:
    parsed = urlparse(absolute_url)
    if parsed.netloc not in {"web.archive.org", "www.web.archive.org"}:
        return absolute_url
    if not parsed.path.startswith("/web/"):
        return absolute_url

    parts = parsed.path.split("/", maxsplit=3)
    if len(parts) < 4:
        return absolute_url

    candidate = parts[3]
    if candidate.startswith("http://") or candidate.startswith("https://"):
        return candidate
    return absolute_url


def _resolve_internal_target(raw_value: str, page_original_url: str) -> InternalTarget | None:
    lowered = raw_value.lower()
    if lowered.startswith(("#", "mailto:", "javascript:", "data:")):
        return None

    absolute = urljoin(page_original_url, raw_value)
    original = _extract_wayback_original(absolute)
    parsed = urlparse(original)

    if parsed.scheme not in {"http", "https"}:
        return None
    if not is_internal_site_netloc(parsed.netloc):
        return None
    if parsed.query:
        return None

    normalized_url = canonical_internal_url(original)
    local_path = local_relpath_from_original(normalized_url)
    fragment = parsed.fragment
    return InternalTarget(
        normalized_url=normalized_url,
        local_path=local_path,
        fragment=fragment,
    )


def rewrite_html(
    html: str,
    *,
    page_original_url: str,
    known_local_paths: set[str],
) -> RewriteResult:
    unresolved: list[tuple[str, str]] = []

    def replace(match: re.Match[str]) -> str:
        attr = match.group("attr")
        quote = match.group("quote")
        raw_value = match.group("value")

        resolved = _resolve_internal_target(raw_value, page_original_url)
        if resolved is None:
            return match.group(0)

        suffix = f"#{resolved.fragment}" if resolved.fragment else ""
        local_path = resolved.local_path
        if local_path not in known_local_paths:
            unresolved.append((page_original_url, local_path))

        rewritten = f"/{local_path}{suffix}"
        return f"{attr}={quote}{rewritten}{quote}"

    rewritten_html = _ATTR_PATTERN.sub(replace, html)
    return RewriteResult(html=rewritten_html, unresolved_targets=unresolved)


def extract_internal_asset_urls(html: str, *, page_original_url: str) -> list[str]:
    assets: list[str] = []
    for match in _ATTR_PATTERN.finditer(html):
        attr = match.group("attr").lower()
        if attr != "src":
            continue
        raw_value = match.group("value")
        resolved = _resolve_internal_target(raw_value, page_original_url)
        if resolved is None:
            continue
        assets.append(resolved.normalized_url)

    return list(dict.fromkeys(assets))


def write_unresolved_links_csv(path: Path, unresolved_targets: list[tuple[str, str]]) -> None:
    ensure_parent_dir(path)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source_url", "target_local_path"])
        for source_url, target in unresolved_targets:
            writer.writerow([source_url, target])


def rewrite_recovered_html_files(
    output_root: Path,
    provenance_records: Sequence[ProvenanceRecord],
    *,
    unresolved_csv_path: Path,
) -> list[tuple[str, str]]:
    known_local_paths = {
        record.local_path
        for record in provenance_records
        if record.status in {"recovered", "skipped_existing"}
    }
    unresolved: list[tuple[str, str]] = []

    for record in provenance_records:
        if record.status not in {"recovered", "skipped_existing"}:
            continue
        if not record.local_path.lower().endswith((".html", ".htm")):
            continue

        page_path = output_root / record.local_path
        if not page_path.exists():
            continue

        original_html = page_path.read_text(encoding="utf-8", errors="ignore")
        result = rewrite_html(
            original_html,
            page_original_url=record.original_url,
            known_local_paths=known_local_paths,
        )
        if result.html != original_html:
            page_path.write_text(result.html, encoding="utf-8")
        unresolved.extend(result.unresolved_targets)

    deduped = list(dict.fromkeys(unresolved))
    write_unresolved_links_csv(unresolved_csv_path, deduped)
    return deduped
