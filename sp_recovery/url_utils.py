"""URL normalization helpers for Something Positive mirror recovery."""

from __future__ import annotations

import re
from urllib.parse import urlparse

CANONICAL_SITE_HOST = "somethingpositive.net"
_MIRROR_PREFIX_RE = re.compile(r"^/(?:www\.)?somethingpositive\.net(?P<rest>/.*)?$", re.IGNORECASE)


def normalize_site_host(netloc: str) -> str:
    host = netloc.lower().strip()
    if "@" in host:
        host = host.rsplit("@", 1)[1]

    candidate_host = host
    if ":" in host:
        left, right = host.rsplit(":", 1)
        if right.isdigit() and right in {"80", "443"}:
            candidate_host = left

    host = candidate_host.rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def is_internal_site_netloc(netloc: str) -> bool:
    return normalize_site_host(netloc) == CANONICAL_SITE_HOST


def canonical_identity_key(original_url: str) -> str:
    parsed = urlparse(original_url)
    host = normalize_site_host(parsed.netloc)
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{host}{path}{query}"


def canonical_internal_url(original_url: str) -> str:
    parsed = urlparse(original_url)
    path = parsed.path or "/"
    mirror_match = _MIRROR_PREFIX_RE.match(path)
    if mirror_match:
        path = mirror_match.group("rest") or "/"
    return f"http://{CANONICAL_SITE_HOST}{path}"
