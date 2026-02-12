# Something Positive Mirror Recovery Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an archive-friendly recovery pipeline that reconstructs a hostable Something Positive mirror with provenance, coverage reporting, and explicit gap tracking.

**Architecture:** Use a single Python CLI package to run deterministic phases: discover capture metadata from CDX, select one canonical capture per URL, recover artifacts with conservative pacing, rewrite HTML links for local browsing, and generate reports/manifests. Canonical selection is pre-modern guarded: default to `2001-01-01` through `2019-12-31`, and exclude captures on/after `2020-01-01` unless policy changes. Persist all intermediate state in JSONL/CSV so reruns only fetch missing items.

**Tech Stack:** Python 3.11+, pytest, standard library networking/parsing plus BeautifulSoup4 for robust HTML rewriting.

---

### Task 1: Scaffold package and command interface

**Files:**
- Create: `pyproject.toml`
- Create: `src/sp_recovery/__init__.py`
- Create: `src/sp_recovery/cli.py`
- Create: `src/sp_recovery/config.py`
- Create: `tests/test_cli.py`

**Step 1: Write the failing test**
- Add `tests/test_cli.py` asserting `python -m sp_recovery.cli --help` exits `0` and includes subcommands `discover`, `recover`, `report`, `run`.

**Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_cli.py -q`
Expected: FAIL due to missing package/CLI.

**Step 3: Write minimal implementation**
- Add package skeleton and argparse CLI wiring with empty handlers.

**Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_cli.py -q`
Expected: PASS.

**Step 5: Commit**
Run:
```bash
git add pyproject.toml src/sp_recovery/__init__.py src/sp_recovery/cli.py src/sp_recovery/config.py tests/test_cli.py
git commit -m "feat: scaffold sp recovery cli"
```

### Task 2: Implement discovery with CDX pagination and canonical selection

**Files:**
- Create: `src/sp_recovery/discovery.py`
- Create: `tests/test_discovery.py`
- Modify: `src/sp_recovery/cli.py`

**Step 1: Write the failing tests**
- Add tests for:
  - parsing CDX JSON rows into records
  - resumption-key pagination request construction
  - canonical capture scoring preferring `200` HTML/image within pre-modern cutoff constraints

**Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_discovery.py -q`
Expected: FAIL.

**Step 3: Write minimal implementation**
- Add discovery module with `discover_captures()` and `choose_canonical_capture()`.
- Output `state/discovered_captures.jsonl` and `state/canonical_urls.jsonl`.

**Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_discovery.py -q`
Expected: PASS.

**Step 5: Commit**
Run:
```bash
git add src/sp_recovery/discovery.py src/sp_recovery/cli.py tests/test_discovery.py
git commit -m "feat: add cdx discovery and canonical capture selection"
```

### Task 3: Implement archive-friendly recovery and provenance capture

**Files:**
- Create: `src/sp_recovery/recover.py`
- Create: `src/sp_recovery/io_utils.py`
- Create: `tests/test_recover.py`
- Modify: `src/sp_recovery/cli.py`

**Step 1: Write the failing tests**
- Add tests for:
  - deterministic local path mapping from original URL
  - Wayback replay URL formatting using `id_`
  - skip-existing behavior to avoid redundant fetches
  - provenance row fields (`original_url`, `timestamp`, `source_url`, `sha256`, `status`)

**Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_recover.py -q`
Expected: FAIL.

**Step 3: Write minimal implementation**
- Add single-threaded paced fetcher (`min_request_interval_seconds`), timeout/retry, file write, and provenance JSONL emission.

**Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_recover.py -q`
Expected: PASS.

**Step 5: Commit**
Run:
```bash
git add src/sp_recovery/recover.py src/sp_recovery/io_utils.py src/sp_recovery/cli.py tests/test_recover.py
git commit -m "feat: recover canonical artifacts with provenance logging"
```

### Task 4: Rebuild internal browsing continuity for recovered HTML

**Files:**
- Create: `src/sp_recovery/rewrite.py`
- Create: `tests/test_rewrite.py`
- Modify: `src/sp_recovery/recover.py`

**Step 1: Write the failing tests**
- Add tests for rewriting archived/internal links to local paths and preserving external links.
- Add test ensuring unresolved internal references are tracked in `state/unresolved_links.csv`.

**Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_rewrite.py -q`
Expected: FAIL.

**Step 3: Write minimal implementation**
- Parse HTML with BeautifulSoup, rewrite `href/src`, and emit unresolved internal targets.

**Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_rewrite.py -q`
Expected: PASS.

**Step 5: Commit**
Run:
```bash
git add src/sp_recovery/rewrite.py src/sp_recovery/recover.py tests/test_rewrite.py
git commit -m "feat: rewrite internal links for standalone mirror browsing"
```

### Task 5: Generate coverage report, gap register, and provenance manifest export

**Files:**
- Create: `src/sp_recovery/reporting.py`
- Create: `tests/test_reporting.py`
- Modify: `src/sp_recovery/cli.py`

**Step 1: Write the failing tests**
- Add tests for recovery percentage math, missing item extraction, and markdown report rendering.

**Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_reporting.py -q`
Expected: FAIL.

**Step 3: Write minimal implementation**
- Emit:
  - `output/reports/coverage_report.md`
  - `output/reports/gap_register.csv`
  - `output/reports/provenance_manifest.csv`

**Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_reporting.py -q`
Expected: PASS.

**Step 5: Commit**
Run:
```bash
git add src/sp_recovery/reporting.py src/sp_recovery/cli.py tests/test_reporting.py
git commit -m "feat: add recovery coverage and gap reporting outputs"
```

### Task 6: Ship runbook, compliance safeguards, and go-live recommendation

**Files:**
- Create: `README.md`
- Create: `docs/runbook.md`
- Create: `docs/legal-notes.md`

**Step 1: Write the failing doc checks**
- Add a small script/test that asserts runbook includes `rate limiting`, `provenance`, `rerun`, and `go-live` sections.

**Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/test_docs.py -q`
Expected: FAIL.

**Step 3: Write minimal implementation**
- Document end-to-end workflow, safety defaults, legal review boundaries, and low-cost hosting recommendation.

**Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/test_docs.py -q`
Expected: PASS.

**Step 5: Commit**
Run:
```bash
git add README.md docs/runbook.md docs/legal-notes.md tests/test_docs.py
git commit -m "docs: add sp recovery runbook and go-live guidance"
```

### Task 7: Verification and seeded dry run

**Files:**
- Create: `config/recovery.example.toml`
- Create: `output/.gitkeep`

**Step 1: Run full verification**
Run: `python3 -m pytest -q`
Expected: PASS.

**Step 2: Run a low-volume dry run against IA (pre-modern window)**
Run:
```bash
python3 -m sp_recovery.cli run \
  --domain somethingpositive.net \
  --from-date 2001-01-01 \
  --to-date 2019-12-31 \
  --modern-cutoff-date 2020-01-01 \
  --max-canonical 25 \
  --request-interval-seconds 2.0 \
  --output-root output/demo
```
Expected: Creates mirror sample + reports without high request volume.

**Step 2b: Gap-focused expansion (optional once phase 1 gaps are known)**
Run:
```bash
python3 -m sp_recovery.cli run \
  --domain somethingpositive.net \
  --from-date 2001-01-01 \
  --to-date 2019-12-31 \
  --modern-cutoff-date 2020-01-01 \
  --only-missing-from output/demo/reports/gap_register.csv \
  --request-interval-seconds 2.0 \
  --output-root output/demo
```
Expected: Improves coverage while avoiding broad re-harvesting.

**Step 3: Commit**
Run:
```bash
git add config/recovery.example.toml output/.gitkeep
git commit -m "chore: add example config and verified dry-run workflow"
```
