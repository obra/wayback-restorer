# Something Positive Recovery Toolkit

This repository contains a repeatable, archive-friendly recovery workflow for rebuilding a hostable mirror of the publicly archived `somethingpositive.net` site.

## Goals

- Recover the highest possible percentage of strip pages and assets.
- Rebuild local browsing continuity for recovered pages.
- Reduce everyday reader dependence on live archive endpoints.
- Keep legal and provenance trails explicit.

## Current Status

Core tooling and tests are present for:

- CDX discovery parsing and canonical capture selection.
- Artifact recovery with deterministic local path mapping.
- Internal link rewriting for local browsing.
- Coverage, gap, and provenance reporting.

## Workflow (High Level)

1. Run discovery to enumerate candidate captures.
2. Select one canonical capture per original URL.
3. Recover canonical artifacts with conservative pacing.
4. Rewrite internal links for standalone browsing.
5. Generate coverage report, gap register, and provenance manifest.

See `docs/runbook.md` for the complete operational workflow.

## Legal Notes

See `docs/legal-notes.md` for rights and attribution boundaries.
