# Wishlist Execution Plan - Solar Lead Scraper

**Created:** 2026-01-23
**Reference:** [Master Wishlist](../../ops-dashboard/MASTER_WISHLIST.md) | [Local Wishlist](./WISHLIST.md)

This plan aligns with the ecosystem-wide prioritization from the Master Wishlist while focusing on scraper-specific items.

---

## Phase 1: Security (Tier 1 from Master) - ✅ COMPLETED 2026-01-24

**Rationale:** Master Wishlist mandates security items block other work. Scraper has one Tier 1 item.

### 1.1 CSV Injection Prevention ✅ DONE
- **Master Wishlist:** Listed in Tier 1 Security & Stability
- **Local ref:** WISHLIST.md > Security > Prevent CSV injection
- **What:** Sanitize company names/descriptions before writing to CSV
- **Implementation:** Added `sanitize_csv_cell()` and `sanitize_dataframe_for_csv()` functions
- **Files:** `scraper.py:22-52` (utility functions), `scraper.py:1769` (applied before CSV write)

### 1.2 Mask Proxy Credentials in Logs ✅ DONE
- **Local ref:** WISHLIST.md > Code Quality > Mask proxy credentials
- **What:** Redact passwords from proxy URLs before logging
- **Implementation:** Added `mask_credentials()` helper using regex, applied to all error logging
- **Files:** `scraper.py:22-37` (helper function), applied at lines 1338, 1346, 1352, 1432, 1445

### 1.3 Redact Sensitive Data in Error Logs ✅ DONE
- **Local ref:** WISHLIST.md > Security > Redact sensitive data in error logs
- **What:** Don't print full `response.text` on API errors
- **Implementation:** Truncated response.text to 500 chars in all upload functions
- **Files:** `upload_results.py:68,70,137,138,517,518,567,568`

---

## Phase 2: Reliability & Error Handling (Tier 3 from Master) - PARTIAL ✅

**Rationale:** Master Wishlist lists two scraper items in Tier 3. These affect our ability to debug production issues.

### 2.1 Replace Silent Exception Handlers
- **Master Wishlist:** Listed in Tier 3 Reliability
- **Local ref:** WISHLIST.md > Error Handling > Replace silent exception handlers
- **What:** 60+ instances of `except Exception: pass` need at minimum logging
- **Focus area:** `camoufox_scraper.py` (27+ bare exceptions)
- **Approach:** Add `logging.debug()` or `logging.warning()` to each

**Claude's take:** ⚠️ **Do with caution.** I understand why these exist - browser scraping is flaky and you don't want one element-not-found to crash the whole run. But swallowing ALL exceptions means you never know why things fail. Suggestion: log at DEBUG level so you can enable verbose mode when debugging, but keep normal runs quiet.

### 2.2 Metrics/Alerting on Consecutive Failures
- **Master Wishlist:** Listed in Tier 3, coordinates with ops-dashboard
- **Local ref:** WISHLIST.md > Logging > Add metrics/alerting
- **What:** Scraper stops after 3 failures (`scraper.py:1335-1337`) with minimal visibility
- **Implementation:** Already uploading to `/api/scraper/errors` - just need ops-dashboard to alert

**Claude's take:** 🤔 **Maybe skip for now.** The scraper already reports errors to ops-dashboard. The alerting logic belongs in ops-dashboard, not here. Unless you want to add Slack/email directly from the scraper, which adds complexity.

### 2.3 Add Error Context Before Truncation ✅ DONE
- **Local ref:** WISHLIST.md > Error Handling > Add error context before truncation
- **What:** Error messages truncated to 500 chars before classification
- **Implementation:** Added `extract_error_context()` helper that extracts exception class name and HTTP status code BEFORE truncating. SearchError now includes `exception_class` and `status_code` fields.
- **Files:** `scraper.py:78-99` (helper), `scraper.py:94-133` (SearchError class), `scraper.py:1427-1438` (usage)

### 2.4 Log Actual Response on Upload Failures ✅ DONE (Phase 1.3)
- **Local ref:** WISHLIST.md > Error Handling > Log actual response
- **What:** JSON decode errors return generic `{"count": "unknown"}`
- **Implementation:** Already done in Phase 1.3 - upload_results.py truncates response.text to 500 chars
- **Files:** `upload_results.py:65,72,138,139,517,518,567,568`

---

## Phase 3: Configuration Hardening - PARTIAL ✅

**Rationale:** Fail fast on misconfiguration rather than producing garbage results.

### 3.1 Add Batch Parameter Bounds Checking ✅ DONE
- **Local ref:** WISHLIST.md > Configuration > Add batch parameter bounds checking
- **What:** Validate `SCRAPER_BATCH` < `SCRAPER_TOTAL_BATCHES`
- **Implementation:** Added validation after batch env var parsing. Raises `ValueError` with clear message if batch >= total_batches, batch < 0, or total_batches < 1.
- **Files:** `scraper.py:1753-1758`

### 3.2 Add Proxy URL Validation
- **Local ref:** WISHLIST.md > Configuration > Add proxy URL validation
- **What:** Validate proxy strings before using them
- **Files:** `scraper.py:1196-1199`

**Claude's take:** 🤔 **Low priority.** If proxy is misconfigured, requests will fail immediately anyway. But a validation with clear error message is nicer.

### 3.3 Standardize Boolean Env Var Parsing
- **Local ref:** WISHLIST.md > Configuration > Standardize boolean env var parsing
- **What:** Accept `"1"`, `"true"`, `"yes"` for `ENABLE_BROWSER_SCRAPING`

**Claude's take:** ❌ **Skip this.** You control the env vars in GitHub Actions. Just document that it's `"1"` and move on. Adding flexibility here adds code for no real benefit.

### 3.4 Document Threshold Rationale ✅ DONE
- **Local ref:** WISHLIST.md > Configuration > Document threshold rationale
- **What:** Explain why scoring threshold is 50.0
- **Implementation:** Added 3-line comment explaining threshold filters ~96% of jobs. Breakdown: company_score (25-35) + role_score (25-40) for qualified leads.
- **Files:** `scraper.py:804-806`

---

## Phase 4: Code Quality (Tier 4 from Master) - PARTIAL ✅

**Rationale:** Technical debt cleanup. Do when you have time, not urgent.

### 4.1 Consolidate Browser Scraper Files ✅ DONE
- **Master Wishlist:** Listed in Tier 4
- **Local ref:** WISHLIST.md > Code Organization > Consolidate browser scraper files
- **What:** `camoufox_scraper.py` vs `camoufox_scraper_optimized.py`
- **Implementation:** Investigated and found `camoufox_scraper_optimized.py` was a 147-line development experiment (optimized `dismiss_popups_fast` function with test harness). Never imported anywhere - only `camoufox_scraper.py` is used in production. Deleted the unused file.
- **Files removed:** `camoufox_scraper_optimized.py` (147 lines of dead code)

### 4.2 Switch print() to Structured Logging
- **Master Wishlist:** Listed in Tier 4
- **Local ref:** WISHLIST.md > Logging > Switch from print() to structured logging
- **What:** Replace all `print()` with `logging` module

**Claude's take:** 🤔 **Consider carefully.** This is a big change touching every file. Benefits are real (filtering, levels, JSON output for log aggregation). But it's a lot of churn for a scraper that runs once daily. I'd say **do it if you're planning more development**, skip if scraper is "done".

### 4.3 Refactor GitHub Actions Merge Step ✅ DONE
- **Local ref:** WISHLIST.md > Code Quality > Refactor GitHub Actions merge step
- **What:** Move 250+ lines of inline Python from YAML to a script
- **Implementation:** Created `.github/scripts/merge_batch_results.py` with proper functions and docstrings. Workflow now calls `python .github/scripts/merge_batch_results.py` instead of inline `python -c "..."`.
- **Files:** `.github/scripts/merge_batch_results.py` (new, 330 lines), `.github/workflows/scrape-leads.yml` (reduced by ~260 lines)

### 4.4 Simplify score_role() Function
- **Local ref:** WISHLIST.md > Code Organization > Simplify score_role()
- **What:** 112 lines of nested conditionals

**Claude's take:** 🤔 **Low priority.** It works. It's tested. Unless you're actively changing scoring logic, leave it alone.

---

## Phase 5: Quick Wins (Documentation & Hygiene) - ✅ COMPLETED 2026-01-24

**Rationale:** These take 5 minutes each and improve developer experience.

### 5.1 Add `.env.example` ✅ DONE
- **Local ref:** WISHLIST.md > Documentation
- **What:** Template for environment variables
- **Implementation:** Created `.env.example` with all environment variables documented

### 5.2 Add `output/.gitkeep` ✅ DONE
- **Local ref:** WISHLIST.md > Repository Hygiene
- **What:** Placeholder so output directory exists
- **Implementation:** Created `output/.gitkeep`, updated `.gitignore` to allow it

### 5.3 Add Root README.md
- **Local ref:** WISHLIST.md > Documentation
- **What:** Standard entry point linking to other docs

**Claude's take:** 🤔 **Optional.** CLAUDE.md already serves this purpose. A README that just says "see CLAUDE.md" is pointless. Either write a proper README or skip.

---

## Phase 6: Performance (When Needed)

**Rationale:** Only optimize if you're hitting actual performance problems.

### 6.1 Use Vectorized Pandas Operations
- **Local ref:** WISHLIST.md > Performance > Use vectorized pandas
- **What:** Replace `.iterrows()` with vectorized operations

**Claude's take:** ❌ **Skip unless slow.** You process ~4k qualified leads. That takes milliseconds even with iterrows. Premature optimization.

### 6.2 Pre-compile Regex Patterns
- **Local ref:** WISHLIST.md > Performance > Pre-compile regex
- **What:** Cache compiled patterns from filter-config.json

**Claude's take:** ❌ **Skip.** The patterns use `in` operator (string matching), not regex. If you wanted regex, you'd need to change the matching logic too. Not worth it.

### 6.3 Async Search Term Processing
- **Local ref:** WISHLIST.md > Performance > Consider async
- **What:** Process search terms concurrently

**Claude's take:** ⚠️ **Don't do this.** Job boards will rate-limit or block you faster if you hit them concurrently. The delays between requests are intentional. You already run 4 parallel batches via GitHub Actions matrix - that's the right level of parallelism.

---

## Phase 7: Testing Improvements - COMPLETED ✅

**Rationale:** Catch regressions before they hit production.

### 7.1 Add Batch Mode Tests ✅ DONE
- **Local ref:** WISHLIST.md > Testing > Add batch mode tests
- **What:** Test that batch splitting works correctly
- **Implementation:** Extracted `get_batch_slice()` helper function from inline code. Added 13 comprehensive tests covering: even/uneven splits, edge cases (empty lists, single batch, more batches than items), validation (negative batch, batch >= total), and real-world scenario (65 terms / 4 batches).
- **Files:** `scraper.py:109-149` (new function), `tests/test_edge_cases.py:TestGetBatchSlice` (13 tests)

### 7.2 Consolidate Test Files ✅ DONE
- **Local ref:** WISHLIST.md > Testing > Consolidate test files
- **What:** 11 test files scattered, unclear which are current
- **Implementation:** Moved 9 development/debugging scripts from root to `scripts/` directory. These are manual test scripts for browser scraping (not pytest unit tests). Kept only proper unit tests in `tests/` directory.
- **Files:** `scripts/test_*.py` (9 files moved), `tests/` (2 pytest test files: `test_jobs.py`, `test_edge_cases.py`)

### 7.3 Add Integration Tests
- **Local ref:** WISHLIST.md > Testing > Add integration tests

**Claude's take:** 🤔 **Nice to have but hard.** End-to-end tests require mocking external job boards. Lots of setup for uncertain value. Unit tests on scoring/filtering are more bang for buck.

### 7.4 Add Pytest Fixtures
- **Local ref:** WISHLIST.md > Testing > Add pytest fixtures

**Claude's take:** ❌ **Skip.** You have like 3 test files. Fixtures are overkill. Just keep it simple.

---

## Phase 8: Incomplete Features (Evaluate & Decide)

**Rationale:** Either fix these or formally remove them.

### 8.1 Investigate LinkedIn Description Fetch
- **Local ref:** WISHLIST.md > Incomplete Features
- **What:** Unclear if `linkedin_fetch_description: True` actually works

**Claude's take:** ✅ **Investigate.** Check a recent output CSV - do LinkedIn jobs have descriptions? If not, either fix or remove the option.

### 8.2 Re-evaluate Google Jobs Support
- **Local ref:** WISHLIST.md > Incomplete Features
- **What:** Disabled/abandoned feature

**Claude's take:** ✅ **Decide.** If you're not going to fix it, remove the code and comments. Dead code is confusing.

### 8.3 Site Blocking Logic
- **Local ref:** WISHLIST.md > Incomplete Features
- **What:** Once blocked, entire batch abandons a site

**Claude's take:** 🤔 **Investigate before changing.** The current behavior might be intentional - if Indeed blocks you, hammering it more won't help. But worth reviewing the logic.

---

## Recommended Execution Order

Based on priority tiers from Master Wishlist and practical value:

```
WEEK 1 (Security + Quick Wins) ✅ COMPLETED
├── Phase 1: All security items (1.1, 1.2, 1.3) ✅
├── Phase 5.1: .env.example ✅
└── Phase 5.2: output/.gitkeep ✅

WEEK 2 (Reliability) ✅ PARTIAL
├── Phase 2.1: Silent exception handlers (start with logging.debug) - PENDING
├── Phase 2.3: Error context before truncation ✅
└── Phase 2.4: Log response on upload failures ✅ (done in 1.3)

WEEK 3 (Configuration + Code Quality) ✅ COMPLETED
├── Phase 3.1: Batch bounds checking ✅
├── Phase 3.4: Document threshold rationale ✅
└── Phase 4.3: Refactor GitHub Actions inline Python ✅

WEEK 4 (Testing + Cleanup) ✅ COMPLETED
├── Phase 7.1: Batch mode tests ✅ (get_batch_slice() + 13 tests)
├── Phase 7.2: Consolidate test files ✅ (moved 9 dev scripts to scripts/)
└── Phase 4.1: Consolidate browser scraper files ✅ (deleted unused optimized version)

BACKLOG (As Needed)
├── Phase 4.2: Structured logging (if more development planned)
├── Phase 8.x: Feature decisions
└── Phase 6.x: Performance (only if actually slow)
```

---

## Items Explicitly Skipped

| Item | Reason |
|------|--------|
| Standardize boolean env vars | You control the config; just document it |
| Vectorized pandas | Not a bottleneck at current scale |
| Pre-compile regex | Patterns aren't regex, they're string matches |
| Async search processing | Would trigger rate limits faster |
| Pytest fixtures | Overkill for small test suite |
| score_role() refactor | Works fine, well-tested, don't touch it |

---

## Coordination Notes

From Master Wishlist:

1. **Metrics/alerting on consecutive failures** - Alerting logic belongs in ops-dashboard, not scraper. Scraper already reports to `/api/scraper/errors`.

2. **Domain matching for lead-contact association** - Listed as Tier 2, coordinates with ops-dashboard and extension. This is an ops-dashboard feature that would consume scraper data; no scraper changes needed.

3. **Error standardization** - Master Wishlist proposes unified error format across repos. If implementing, follow the target format:
   ```json
   {"success": false, "code": "ERROR_CODE", "message": "Human readable"}
   ```

---

*This plan will be updated as items are completed or priorities change.*
