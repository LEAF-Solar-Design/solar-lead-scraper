# Claude Code Context: Solar Lead Scraper

## Project Overview

Python ETL pipeline that scrapes job boards for solar design leads and uploads to ops-dashboard.

**Tech Stack:** Python 3.11, python-jobspy, pandas, Camoufox

**Schedule:** Daily at 2am CT via GitHub Actions (4 parallel batches)

---

## Cross-Repository Ecosystem

**IMPORTANT:** This repository is part of a connected ecosystem. Before making changes to data flows, output schemas, or API contracts, check:

1. **[DATA_ARCHITECTURE_PLAN.md](./DATA_ARCHITECTURE_PLAN.md)** - This repo's data flows
2. **[ops-dashboard/CROSS_REPO_COORDINATION.md](../ops-dashboard/CROSS_REPO_COORDINATION.md)** - Cross-repo change coordination

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
