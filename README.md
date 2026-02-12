# Wayback Mirror Recovery Toolkit (sp-recovery)

This project rebuilds a hostable, browseable mirror of a public website using Internet Archive Wayback Machine captures, with conservative request pacing and explicit provenance.

It started as a recovery effort for Something Positive. The name stuck. The tool is general.

## What This Tool Does

The pipeline does six things:
1. Queries CDX (with pagination) for captures in a defined date window.
2. Selects one canonical capture per original URL.
3. Downloads captures through replay URLs in `id_` mode with conservative pacing.
4. Recovers referenced internal assets from recovered HTML (strip images, static resources).
5. Rewrites internal links to local relative paths for standalone browsing.
6. Writes coverage, gap, and provenance reports.

## What This Tool Does Not Do

- No access-control bypasses.
- No private/admin/system recovery.
- No new editorial content.
- No claim that missing/inferred content is recovered original content.

## Requirements

- Python `3.11+`
- Network access to `web.archive.org`

No third-party runtime dependencies are required.

## Full Run Command

Run this from the repository root (replace the placeholders):

```bash
python3 -m sp_recovery.cli run \
  --domain example.org \
  --canonical-host example.org \
  --equivalent-host example.org \
  --equivalent-host www.example.org \
  --from-date 2000-01-01 \
  --to-date 2024-01-01 \
  --modern-cutoff-date 2024-01-01 \
  --max-canonical 0 \
  --request-interval-seconds 2.0 \
  --output-root output/example-mirror
```

Notes:
- `--max-canonical 0` means "no cap" (recover all selected canonical URLs).
- `--modern-cutoff-date` acts as a restore-as-of boundary (captures on/after this date are excluded).
- Host equivalence is explicit. If you omit `--equivalent-host`, the default is `{canonical_host, www.<canonical_host>}`.

## Safe Resume

To resume after interruption, run the same command again with the same `--output-root`.

Why this is safe:
- recovered files are skipped when already present and non-empty,
- provenance is appended incrementally during recovery,
- downloads use atomic replace (`temp + rename`) to avoid partial-file corruption.

## Gap-Focused Rerun

After a baseline run, target only known gaps:

```bash
python3 -m sp_recovery.cli run \
  --domain example.org \
  --canonical-host example.org \
  --equivalent-host example.org \
  --equivalent-host www.example.org \
  --from-date 2000-01-01 \
  --to-date 2024-01-01 \
  --modern-cutoff-date 2024-01-01 \
  --max-canonical 0 \
  --request-interval-seconds 2.0 \
  --only-missing-from output/example-mirror/reports/gap_register.csv \
  --output-root output/example-mirror
```

## Output Layout

Example output tree:

```text
output/example-mirror/
  example.org/...
  reports/
    coverage_report.md
    gap_register.csv
    provenance_manifest.csv
  state/
    discovered_captures.jsonl
    canonical_urls.jsonl
    provenance.jsonl
    unresolved_links.csv
```

## State Files and Debugging

Use these files to inspect behavior and failures:

- `state/discovered_captures.jsonl`: raw discovered capture candidates in-window.
- `state/canonical_urls.jsonl`: one chosen capture per canonical URL identity.
- `state/provenance.jsonl`: one row per recovery attempt, appended incrementally.
- `state/unresolved_links.csv`: internal links referenced by HTML but not present locally.

Common provenance statuses:
- `recovered`
- `skipped_existing`
- `fetch_failed_<http_code>`
- `fetch_error`

## Reports

- `reports/coverage_report.md`: discovered/recovered/missing totals and percentage.
- `reports/gap_register.csv`: unresolved original URLs and likely next source actions.
- `reports/provenance_manifest.csv`: exportable source mapping and hashes for recovered artifacts.

## Serving the Mirror Locally

Internal links are rewritten to relative paths, so direct `file://` browsing works for most flows.

If you prefer a local web server:

```bash
cd output/example-mirror
python3 -m http.server 8000
```

Then open:
- `http://127.0.0.1:8000/example.org/`

## CLI Commands

- `discover`: discovery + canonical selection only.
- `recover`: recover from existing `state/canonical_urls.jsonl`.
- `report`: regenerate reports from existing state/provenance files.
- `run`: full end-to-end pipeline.

Get command help:

```bash
python3 -m sp_recovery.cli --help
python3 -m sp_recovery.cli run --help
```

## Key Flags

- `--domain`: CDX query domain scope.
- `--canonical-host`: local canonical host path namespace.
- `--equivalent-host`: repeatable host-equivalence list for dedupe/rewrite/recovery.
- `--from-date` / `--to-date`: query date bounds (`YYYY-MM-DD`).
- `--modern-cutoff-date`: restore-as-of boundary (exclude captures on/after date).
- `--max-canonical`: cap selected canonical URLs (`0` means uncapped).
- `--request-interval-seconds`: delay between requests.
- `--only-missing-from`: gap register CSV to target known missing URLs.
- `--output-root`: output directory for mirror, state, and reports.

## Operational Guidance

- Keep request pacing conservative (default `2.0s`).
- Avoid repeated broad reruns when gap-targeted reruns are sufficient.
- Keep host equivalence explicit to avoid duplicate recovery for host aliases.
- Keep the same `--output-root` for resumability and clean audit trails.

## Worked Example: Something Positive (Pre-Modern Scheme Cutoff)

This is the original use case that shaped the defaults and tests.

Full run:

```bash
python3 -m sp_recovery.cli run \
  --domain somethingpositive.net \
  --canonical-host somethingpositive.net \
  --equivalent-host somethingpositive.net \
  --equivalent-host www.somethingpositive.net \
  --from-date 2001-01-01 \
  --to-date 2025-02-01 \
  --modern-cutoff-date 2025-02-01 \
  --max-canonical 0 \
  --request-interval-seconds 2.0 \
  --output-root output/full-pre2025
```

Gap-focused rerun:

```bash
python3 -m sp_recovery.cli run \
  --domain somethingpositive.net \
  --canonical-host somethingpositive.net \
  --equivalent-host somethingpositive.net \
  --equivalent-host www.somethingpositive.net \
  --from-date 2001-01-01 \
  --to-date 2025-02-01 \
  --modern-cutoff-date 2025-02-01 \
  --max-canonical 0 \
  --request-interval-seconds 2.0 \
  --only-missing-from output/full-pre2025/reports/gap_register.csv \
  --output-root output/full-pre2025
```

## Verification

Run tests:

```bash
python3 -m pytest -q
```

## Legal and Compliance

See:
- `docs/legal-notes.md`
- `docs/runbook.md`

Key policy:
- preserve creator credit and publication context,
- keep provenance explicit for every recovered artifact,
- escalate rights/publication questions to owner review.
