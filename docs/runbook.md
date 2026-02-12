# Runbook

## Purpose

Provide a repeatable, low-impact process to rebuild an independently hostable mirror of Something Positive from lawful public archives.

## Inputs

- Target domain: `somethingpositive.net` (+ `www.somethingpositive.net`)
- Preferred capture window: `2023-01-01` to `2025-02-01`
- Expansion window: `2021-01-01` to `2025-02-01`
- Legacy fallback window: pre-2021 only for unresolved gaps

## Operational Safeguards

### Rate Limiting

- Use single-threaded requests by default.
- Enforce minimum delay between requests (start at `2.0s`).
- Retry conservatively with bounded attempts.
- Skip already-recovered local files to avoid redundant upstream traffic.

### Provenance

- Log one provenance record per artifact with original URL, capture timestamp, replay URL, hash, and recovery status.
- Preserve source snapshot references in exportable manifest files.
- Never mark inferred placeholders as recovered originals.

### Deduplication

- Keep one canonical recovered copy per original URL.
- Prefer highest-confidence capture in preferred windows.
- Avoid repeated broad re-harvesting; target unresolved gaps only.

## Recovery Execution

1. Discovery
- Enumerate captures with CDX API.
- Save discovered candidates and canonical selections under `state/`.

2. Recovery
- Fetch canonical captures through replay URLs in `id_` mode.
- Store locally using deterministic path mapping.

3. Rewrite
- Rewrite internal links (`href`, `src`) to local mirror paths.
- Record unresolved internal references to `state/unresolved_links.csv`.

4. Reporting
- Write coverage report (`coverage_report.md`).
- Write gap register (`gap_register.csv`).
- Write provenance manifest (`provenance_manifest.csv`).

## Rerun Strategy

- Rerun phase 1 (`2023-01-01` to `2025-02-01`) only when new canonical URLs are discovered.
- For missing items, rerun with expansion window (`2021-01-01` to `2025-02-01`) using gap-targeted mode.
- For persistent gaps, run focused legacy lookups for specific URLs, not broad full-history sweeps.

## Compliance Checklist

- Respect source terms and archive access boundaries.
- Keep creator credit and publication context where available.
- Maintain explicit source attribution for each recovered item.
- Escalate rights questions to site owner before publication.

## Go-Live Recommendation

### Hosting Pattern

- Serve recovered mirror from static object storage + CDN.
- Suggested stack: Cloudflare R2 (or S3-compatible bucket) + Cloudflare CDN + immutable asset caching.

### Why this setup

- Low ongoing cost for mostly static historical content.
- High cache hit rates for strip images and HTML pages.
- Keeps normal reader traffic off Internet Archive endpoints.

### Deployment Notes

- Publish mirror output as versioned releases.
- Keep prior release snapshot available for rollback.
- Expose `/reports/coverage_report.md` and `/reports/gap_register.csv` for transparency.
