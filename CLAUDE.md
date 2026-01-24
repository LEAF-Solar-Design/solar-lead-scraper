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

| Repo | Relationship |
|------|--------------|
| **ops-dashboard** | Receives lead CSV via POST /api/jobs/ingest |

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
DASHBOARD_API_KEY=     # API authentication
SCRAPER_BATCH=         # 0-3 (which batch)
SCRAPER_TOTAL_BATCHES= # 4 (total parallel)
```
