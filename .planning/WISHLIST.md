# Wishlist

Low-priority improvements to address when time permits. None of these block production use.

For actual issues that need fixing, see [ISSUES.md](ISSUES.md).

---

## Documentation

### Add `.env.example` file
- **Description:** Create a template showing required environment variables for local development
- **Current state:** Env vars are documented in CLAUDE.md, but no template file exists
- **Benefit:** Faster onboarding for new developers

### Add root `README.md`
- **Description:** Create a README that links to CLAUDE.md and DATA_ARCHITECTURE_PLAN.md
- **Current state:** Documentation exists but is split across multiple files
- **Benefit:** Standard entry point for GitHub visitors

---

## Repository Hygiene

### Add `output/.gitkeep`
- **Description:** Ensure output directory exists in repo with a `.gitkeep` placeholder
- **Current state:** Directory is created at runtime via `mkdir(exist_ok=True)`
- **Benefit:** Clearer repo structure

---

## Code Quality

### Refactor GitHub Actions merge step
- **Description:** Move inline Python from workflow YAML to a separate script
- **Current state:** 250+ lines of Python embedded in YAML via `-c` flag
- **Benefit:** Easier to test, debug, and maintain

### Add file operation timeouts
- **Description:** Large JSON/CSV reads could hang indefinitely
- **Current state:** No timeouts on file I/O
- **Benefit:** Prevent infinite hangs on slow/locked files

### Mask proxy credentials in logs
- **Description:** Proxy URLs with credentials could appear in CI logs
- **Current state:** No credential masking
- **Benefit:** Security hygiene

---

## Error Handling

### Replace silent exception handlers
- **Description:** 60+ instances of `except Exception: pass` swallow errors without logging
- **Current state:** Primarily in `camoufox_scraper.py` (27+ bare exceptions) - errors are hidden
- **Benefit:** Ability to debug failures; understand why browser scraping fails

### Add error context before truncation
- **Description:** In `scraper.py:1275-1281`, error messages truncated to 500 chars before classification
- **Current state:** Crucial diagnostic info may be lost
- **Benefit:** Better error analytics and debugging

### Log actual response on upload failures
- **Description:** In `upload_results.py:61-71`, JSON decode errors return generic `{"count": "unknown"}`
- **Current state:** Response body printed but not captured/logged properly
- **Benefit:** Better debugging of dashboard communication issues

---

## Configuration

### Add proxy URL validation
- **Description:** In `scraper.py:1196-1199`, malformed proxy strings silently accepted
- **Current state:** `for p in proxy_env.split(",") if p.strip()` - empty strings allowed
- **Benefit:** Fail fast on misconfiguration

### Add batch parameter bounds checking
- **Description:** `SCRAPER_BATCH` and `SCRAPER_TOTAL_BATCHES` converted to int with no validation
- **Current state:** `SCRAPER_BATCH=999` would create invalid indices
- **Benefit:** Prevent silent failures from misconfiguration

### Standardize boolean env var parsing
- **Description:** `ENABLE_BROWSER_SCRAPING` only works if exactly `"1"`, not `"true"` or `"yes"`
- **Current state:** Inconsistent with common patterns
- **Benefit:** Less confusing configuration

### Document threshold rationale
- **Description:** Scoring threshold of 50.0 has no explanation of why this value was chosen
- **Current state:** Magic number in config without documentation
- **Benefit:** Easier to tune; future maintainers understand the reasoning

---

## Performance

### Use vectorized pandas operations
- **Description:** In `scraper.py:1430-1455`, `.iterrows()` used (slowest pandas method)
- **Current state:** Could slow down processing with 1000+ rows
- **Benefit:** Faster filtering for large result sets

### Pre-compile regex patterns
- **Description:** 50+ patterns in `filter-config.json` re-parsed on every job
- **Current state:** String patterns used with `in` operator
- **Benefit:** Faster scoring, especially with many jobs

### Consider async search term processing
- **Description:** Search terms processed sequentially with 10-20s delays between
- **Current state:** 130 terms × 20s = 43 minutes minimum per batch (sequential)
- **Benefit:** Could significantly reduce scrape time with concurrent requests

---

## Security

### Prevent CSV injection
- **Description:** Company names/descriptions written directly to CSV without sanitization
- **Current state:** Malicious job descriptions with `=cmd.exe` could execute in Excel
- **Benefit:** Protect users who open CSVs in spreadsheet apps

### Redact sensitive data in error logs
- **Description:** In `upload_results.py:517,566`, full `response.text` printed on errors
- **Current state:** Response might contain sensitive data
- **Benefit:** Prevent accidental secret exposure in logs

### Evaluate regex patterns for ReDoS
- **Description:** Long alternation patterns in filter-config.json could be vulnerable
- **Current state:** `["cadence", "synopsys", ... 50+ items]` patterns
- **Benefit:** Prevent potential denial-of-service on pathological input

---

## Testing

### Add integration tests
- **Description:** No end-to-end tests of scraper → filter → upload flow
- **Current state:** Only unit tests for `score_job()`
- **Benefit:** Catch breaking changes before deployment

### Consolidate test files
- **Description:** 11 test files scattered across repo root with unclear status
- **Current state:** Multiple `test_ziprecruiter*.py`, `test_glassdoor*.py` variants
- **Benefit:** Clearer which tests are current; easier maintenance

### Add batch mode tests
- **Description:** Batch splitting logic (`scraper.py:1142-1152`) not covered by tests
- **Current state:** No tests verify batch division works correctly
- **Benefit:** Confidence in parallel execution

### Add pytest fixtures for config
- **Description:** Tests use tempfile ad-hoc instead of proper fixtures
- **Current state:** `tests/test_edge_cases.py` creates temp files manually
- **Benefit:** Cleaner, more reusable test setup

---

## Logging & Observability

### Switch from print() to structured logging
- **Description:** All files use `print()` statements
- **Current state:** Can't filter, parse, or aggregate logs
- **Benefit:** Better log management, filtering, and alerting

### Add metrics/alerting on consecutive failures
- **Description:** In `scraper.py:1335-1337`, stops after 3 failures with minimal logging
- **Current state:** May give up prematurely on transient errors
- **Benefit:** Better visibility into scraper health

### Document deep_analytics purpose
- **Description:** `deep_analytics` exported but purpose unclear
- **Current state:** Contains raw attempts but no automatic analysis
- **Benefit:** Clarity on what this data is for; potential alerting

---

## Code Organization

### Consolidate browser scraper files
- **Description:** Both `camoufox_scraper.py` (1,982 lines) and `camoufox_scraper_optimized.py` exist
- **Current state:** Unclear which is canonical; suggests incomplete refactoring
- **Benefit:** Single source of truth; less confusion

### Extract merge logic to reusable module
- **Description:** Merge logic duplicated between `scraper.py` and workflow YAML
- **Current state:** `merge_deep_analytics()`, `merge_run_stats()` etc. copied in workflow
- **Benefit:** Single place to maintain; reduce divergence risk

### Simplify score_role() function
- **Description:** 112 lines of nested conditionals for role scoring (`scraper.py:613-724`)
- **Current state:** Hard to follow tier matching logic
- **Benefit:** Easier to maintain and extend scoring rules

---

## Incomplete Features

### Investigate LinkedIn description fetch
- **Description:** `linkedin_fetch_description: True` passed to jobspy but unclear if working
- **Current state:** No verification it's actually retrieving descriptions
- **Benefit:** Confirm feature works or remove dead code

### Make rejection export limits configurable
- **Description:** `export_rejected_leads()` hardcoded to max 100 leads, 2000 char descriptions
- **Current state:** No ability to configure limits
- **Benefit:** Flexibility for different analysis needs

### Improve site blocking logic
- **Description:** Once a site is blocked, entire batch stops trying it
- **Current state:** May be blocked on specific search term, not globally
- **Benefit:** More resilient scraping; don't abandon sites prematurely

### Re-evaluate Google Jobs support
- **Description:** Comment states "Requires manual query syntax calibration (Issue #302)"
- **Current state:** Feature abandoned/disabled
- **Benefit:** Either fix or formally remove to reduce confusion

---

## GitHub Actions

### Add workflow timeout protection
- **Description:** `camoufox fetch` retry loop has no overall timeout
- **Current state:** Could timeout entire matrix job if CDN is slow
- **Benefit:** Fail fast instead of consuming runner minutes

### Add lint/test step to workflow
- **Description:** Workflow has no `pytest` or code quality checks
- **Current state:** Broken code could be deployed
- **Benefit:** Catch issues before production

### Improve matrix download coordination
- **Description:** Staggered sleep avoids simultaneous Camoufox downloads but timing fragile
- **Current state:** Race condition possible
- **Benefit:** More reliable parallel execution

---

*Last updated: 2026-01-23*
