# Runbook

## Purpose

Provide a repeatable, low-impact process to rebuild an independently hostable mirror of Something Positive from lawful public archives.

## Inputs

- Target domain: `somethingpositive.net` (+ `www.somethingpositive.net`)
- Default capture window: `2001-01-01` to `2019-12-31`
- Pre-modern cutoff: captures on/after `2020-01-01` are excluded
- Recovery order: earliest comic pages first (chronological), then related assets/pages

## Operational Safeguards

### Rate Limiting

- Use single-threaded requests by default.
- Enforce minimum delay between requests (start at `2.0s`).
- Retry conservatively with bounded attempts.
- Skip already-recovered local files to avoid redundant upstream traffic.

### Provenance

- Log one provenance record per artifact with original URL, capture timestamp, replay URL, hash, and recovery status.
- Append provenance records incrementally during recovery to support interruption forensics and safe reruns.
- Preserve source snapshot references in exportable manifest files.
- Never mark inferred placeholders as recovered originals.

### Deduplication

- Keep one canonical recovered copy per original URL.
- Collapse CDX discovery by URL key to reduce duplicates at source.
- Ignore query/fragment URL variants during recovery target selection.
- Normalize host variants (`somethingpositive.net`, `www.somethingpositive.net`, default ports) to one mirror identity.
- Write recovered artifacts via atomic replace to avoid partial-file corruption on interruption.
- Avoid repeated broad re-harvesting; target unresolved gaps only.

## Recovery Execution

1. Discovery
- Enumerate captures with CDX API.
- Save discovered candidates and canonical selections under `state/`.

2. Recovery
- Fetch canonical captures through replay URLs in `id_` mode.
- Store locally using deterministic path mapping.
- Run an internal-asset pass for recovered HTML pages so strip images and required static resources are mirrored locally.

3. Rewrite
- Rewrite internal links (`href`, `src`) to local mirror paths.
- Record unresolved internal references to `state/unresolved_links.csv`.

4. Reporting
- Write coverage report (`coverage_report.md`).
- Write gap register (`gap_register.csv`).
- Write provenance manifest (`provenance_manifest.csv`).

## Rerun Strategy

- Run baseline recovery in the pre-modern window (`2001-01-01` to `2019-12-31`).
- For missing items, rerun gap-targeted discovery/recovery using `--only-missing-from` against the latest `gap_register.csv`.
- For persistent gaps, run focused URL-level lookups before expanding query range.
- If owner explicitly approves broader recovery windows, keep the pre-modern cutoff guard unless policy changes.

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
