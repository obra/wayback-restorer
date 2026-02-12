"""URL normalization and host-equivalence helpers for mirror recovery."""

from __future__ import annotations

from collections.abc import Collection
from urllib.parse import urlparse

DEFAULT_CANONICAL_SITE_HOST = "somethingpositive.net"
DEFAULT_EQUIVALENT_SITE_HOSTS = frozenset({"somethingpositive.net", "www.somethingpositive.net"})


def normalize_site_host(netloc: str) -> str:
    host = netloc.lower().strip()
    if "@" in host:
        host = host.rsplit("@", 1)[1]

    candidate_host = host
    if ":" in host:
        left, right = host.rsplit(":", 1)
        if right.isdigit() and right in {"80", "443"}:
            candidate_host = left

    return candidate_host.rstrip(".")


def _normalized_equivalent_hosts(
    *,
    canonical_host: str,
    equivalent_hosts: Collection[str],
) -> set[str]:
    normalized: set[str] = set()
    for host in equivalent_hosts:
        normalized_host = normalize_site_host(host)
        if normalized_host:
            normalized.add(normalized_host)
    normalized_canonical = normalize_site_host(canonical_host)
    if normalized_canonical:
        normalized.add(normalized_canonical)
    return normalized


def canonicalize_site_host(
    netloc: str,
    *,
    canonical_host: str = DEFAULT_CANONICAL_SITE_HOST,
    equivalent_hosts: Collection[str] = DEFAULT_EQUIVALENT_SITE_HOSTS,
) -> str:
    observed_host = normalize_site_host(netloc)
    normalized_canonical = normalize_site_host(canonical_host)
    if not normalized_canonical:
        normalized_canonical = observed_host
    equivalents = _normalized_equivalent_hosts(
        canonical_host=normalized_canonical,
        equivalent_hosts=equivalent_hosts,
    )
    if observed_host in equivalents and normalized_canonical:
        return normalized_canonical
    return observed_host


def is_internal_site_netloc(
    netloc: str,
    *,
    canonical_host: str = DEFAULT_CANONICAL_SITE_HOST,
    equivalent_hosts: Collection[str] = DEFAULT_EQUIVALENT_SITE_HOSTS,
) -> bool:
    host = normalize_site_host(netloc)
    equivalents = _normalized_equivalent_hosts(
        canonical_host=canonical_host,
        equivalent_hosts=equivalent_hosts,
    )
    return host in equivalents


def canonical_identity_key(
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
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{host}{path}{query}"


def _strip_mirror_host_prefix(path: str, *, equivalent_hosts: set[str]) -> str:
    if not path.startswith("/"):
        return path

    head = path[1:]
    first_segment, _, remainder = head.partition("/")
    if not first_segment:
        return path

    normalized_segment = normalize_site_host(first_segment)
    if normalized_segment and normalized_segment in equivalent_hosts:
        return f"/{remainder}" if remainder else "/"
    return path


def canonical_internal_url(
    original_url: str,
    *,
    canonical_host: str = DEFAULT_CANONICAL_SITE_HOST,
    equivalent_hosts: Collection[str] = DEFAULT_EQUIVALENT_SITE_HOSTS,
) -> str:
    parsed = urlparse(original_url)
    normalized_canonical = normalize_site_host(canonical_host) or DEFAULT_CANONICAL_SITE_HOST
    path = parsed.path or "/"
    normalized_equivalents = _normalized_equivalent_hosts(
        canonical_host=normalized_canonical,
        equivalent_hosts=equivalent_hosts,
    )
    path = _strip_mirror_host_prefix(path, equivalent_hosts=normalized_equivalents)
    return f"http://{normalized_canonical}{path}"
