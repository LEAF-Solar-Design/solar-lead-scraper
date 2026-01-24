# Claude Code Context: Solar Lead Scraper

## Master Data Architecture

**This repo is part of a 5-repo ecosystem with ops-dashboard as the central hub.**

Key architecture documents (in ops-dashboard):
- **[DATA_ARCHITECTURE_PLAN.md](../ops-dashboard/DATA_ARCHITECTURE_PLAN.md)** - Master data flows, Neon schema, sync triggers
- **[CROSS_REPO_COORDINATION.md](../ops-dashboard/CROSS_REPO_COORDINATION.md)** - Change propagation matrix
- **[MASTER_WISHLIST.md](../ops-dashboard/MASTER_WISHLIST.md)** - Cross-repo prioritized wishlist
- **[WISH_EXECUTION_PLAN.md](../ops-dashboard/WISH_EXECUTION_PLAN.md)** - Current execution status

## Wishlist Execution Status

**Last Updated:** 2026-01-24

### Phase 1: Security - COMPLETED ✅

| Item | Status | Notes |
|------|--------|-------|
| 1.1 CSV injection prevention | ✅ DONE | `sanitize_dataframe_for_csv()` in scraper.py |
| 1.2 Mask proxy credentials in logs | ✅ DONE | `mask_credentials()` helper, applied to all error logging |
| 1.3 Redact sensitive data in error logs | ✅ DONE | upload_results.py truncates response.text to 500 chars |

### Quick Wins - COMPLETED ✅

| Item | Status | Notes |
|------|--------|-------|
| Add .env.example | ✅ DONE | Template for environment variables |
| Add output/.gitkeep | ✅ DONE | Ensures output directory exists in repo |

### Phase 2: Reliability - PARTIAL ✅

| Item | Status | Notes |
|------|--------|-------|
| 2.3 Error context before truncation | ✅ DONE | `extract_error_context()` + SearchError fields |
| 2.4 Log response on upload failures | ✅ DONE | Done in 1.3 (truncated response logging) |

### Phase 3: Configuration - COMPLETED ✅

| Item | Status | Notes |
|------|--------|-------|
| 3.1 Batch parameter bounds checking | ✅ DONE | Validates SCRAPER_BATCH < SCRAPER_TOTAL_BATCHES |
| 3.4 Document threshold rationale | ✅ DONE | Comment explaining 50.0 threshold logic |

### Phase 4: Code Quality - PARTIAL ✅

| Item | Status | Notes |
|------|--------|-------|
| 4.1 Consolidate browser scraper files | ✅ DONE | Deleted unused `camoufox_scraper_optimized.py` (147 lines dead code) |
| 4.3 Refactor GitHub Actions inline Python | ✅ DONE | `.github/scripts/merge_batch_results.py` |

### Phase 7: Testing - COMPLETED ✅

| Item | Status | Notes |
|------|--------|-------|
| 7.1 Batch mode tests | ✅ DONE | `get_batch_slice()` helper + 13 tests in `test_edge_cases.py` |
| 7.2 Consolidate test files | ✅ DONE | Moved 9 dev scripts to `scripts/`, kept 2 pytest files in `tests/` |

### Pending Items

From [MASTER_WISHLIST.md](../ops-dashboard/MASTER_WISHLIST.md):

**Tier 3 (Reliability):**
- [ ] Replace silent exception handlers (60+) in camoufox_scraper.py (27+ bare exceptions)
- [ ] Metrics/alerting on consecutive failures (alerting belongs in ops-dashboard)

**Tier 4 (Code Quality):**
- [ ] Switch print() to structured logging

**Full plan:** [.planning/WISH_EXECUTION_PLAN.md](.planning/WISH_EXECUTION_PLAN.md)

Local wishlist: [.planning/WISHLIST.md](.planning/WISHLIST.md)

---

## Project Overview

Python ETL pipeline that scrapes job boards for solar design leads and uploads to ops-dashboard.

**Tech Stack:** Python 3.11, python-jobspy, pandas, Camoufox

**Schedule:** Daily at 2am CT via GitHub Actions (4 parallel batches)

---

## Cross-Repository Ecosystem

**IMPORTANT:** This repository is part of a connected ecosystem. Before making changes to data flows, output schemas, or API contracts, check:

1. **[DATA_ARCHITECTURE_PLAN.md](./DATA_ARCHITECTURE_PLAN.md)** - This repo's data flows
2. **[ops-dashboard/CROSS_REPO_COORDINATION.md](../ops-dashboard/CROSS_REPO_COORDINATION.md)** - Cross-repo change coordination

**Recent ecosystem updates (Jan 2026):**
- **solar-lead-scraper (this repo):** Completed Tier 1 security fixes (CSV injection, credential masking, log redaction)
- **linkedin-hubspot-extension:** Completed Tier 1 + Tier 3 (DEBUG mode, timeouts, error handling)
- **leaf_website:** Completed Tier 1 security fixes (price validation, BigQuery singleton)
- **ops-dashboard:** Fixed SQL injection and empty catch blocks

### Connected Repositories

| Repo | Path | Relationship to Scraper |
|------|------|------------------------|
| **ops-dashboard** | `../ops-dashboard` | Receives leads, stats, errors via API. Central hub. |
| **leaf_website** | `../leaf_website` | No direct connection. Shares customers via ops-dashboard. |
| **linkedin-hubspot-extension** | `../linkedin-hubspot-extension` | No direct connection. May contact leads we find. |
| **cable-sizing (plugin)** | `../cable-sizing/beta-v1/beta-v1` | No direct connection. End users of the product. |

**Ecosystem Architecture:**
```
ops-dashboard (Hub) ← Neon DB (source of truth)
     ↑
     ├── scraper (this) → sends leads
     ├── leaf_website → sends signups/subscriptions
     ├── linkedin-hubspot-extension → sends CRM activity
     └── cable-sizing plugin → sends usage telemetry
```

### API Contract

This scraper sends data to ops-dashboard. When changing output format:

1. Check if ops-dashboard expects the current format
2. Coordinate changes with ops-dashboard `/api/jobs/ingest` endpoint
3. Deploy ops-dashboard changes first
4. Then deploy scraper changes

---

## When to Check Other Repos

Check the coordination guide when changing:

- CSV column names or types
- New fields being captured
- API endpoint format
- Error/stats reporting format

---

## Key Files

- `scraper.py` - Main ETL script
- `upload_results.py` - Dashboard upload script
- `config/filter-config.json` - Filter rules
- `.github/workflows/scrape-leads.yml` - GitHub Actions workflow

---

## Environment Variables

```bash
DASHBOARD_URL=         # ops-dashboard base URL
DASHBOARD_API_KEY=     # API authentication (uses LEADS_API_KEY on ops-dashboard side)
SCRAPER_BATCH=         # 0-3 (which batch)
SCRAPER_TOTAL_BATCHES= # 4 (total parallel)
```

---

## Quick Reference

### Build Verification
```bash
# Syntax check all Python files
python -m py_compile scraper.py upload_results.py camoufox_scraper.py

# Verify imports work
python -c "import scraper; import upload_results; print('OK')"

# Validate config
python -c "import json; json.load(open('config/filter-config.json')); print('OK')"
```

### Key Functions (scraper.py)
- `scrape_solar_jobs()` - Main scraping entry point (line ~991)
- `score_job()` - Qualification scoring (line ~706)
- `classify_error()` - Error categorization (line ~960)
- `process_jobs()` - Deduplication and output formatting (line ~1547)

### Key Functions (upload_results.py)
- `upload_to_dashboard()` - POST CSV to /api/jobs/ingest
- `upload_search_errors()` - POST JSON to /api/scraper/errors
- `upload_run_stats()` - POST JSON to /api/scraper/stats
- `upload_deep_analytics()` - POST JSON to /api/scraper/analytics

### Output Files (in output/)
- `solar_leads_{timestamp}.csv` - Qualified leads
- `run_stats_{timestamp}.json` - Run statistics
- `search_errors_{timestamp}.json` - Failed searches
- `deep_analytics_{timestamp}.json` - Detailed diagnostics

### Error Types
The scraper classifies errors as: `rate_limit | blocked | timeout | connection | unknown`

### API Endpoints (ops-dashboard)
All endpoints use Bearer token auth with `LEADS_API_KEY`:
- `POST /api/jobs/ingest` - CSV upload (required)
- `POST /api/scraper/errors` - Error reporting
- `POST /api/scraper/stats` - Run statistics
- `POST /api/scraper/analytics` - Deep diagnostics (optional)

---

## Testing Locally

The scraper takes a long time to run (65 search terms × 4 sites). For quick testing:
- Check existing output files in `output/` directory
- Recent run stats show ~47k raw jobs → ~4k qualified → ~157 unique companies
