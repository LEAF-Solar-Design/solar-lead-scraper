# Solar Lead Scraper — Self-Description

Python ETL pipeline that scrapes job boards for solar design leads and uploads qualified results to ops-dashboard. Stateless — runs daily at 2am CT via GitHub Actions with 4 parallel batches.

## Tech Stack

Python 3.11, python-jobspy, pandas, Camoufox (browser automation for Cloudflare-protected sites)

## What It Does

1. Scrapes 4 job boards (Indeed, LinkedIn, ZipRecruiter, Glassdoor) for ~65 search terms
2. Scores and filters jobs using a 6-tier qualification system (threshold: score >= 50)
3. Deduplicates by company
4. Uploads qualified leads, run stats, errors, and analytics to ops-dashboard via API

Typical daily run: ~47k raw jobs -> ~4k qualified -> ~157 unique companies

## Data It Produces

### Leads CSV (POST /api/jobs/ingest)

| Column | Type | Description |
|--------|------|-------------|
| company | string | Company name from job posting |
| domain | string | Guessed company domain (best-effort) |
| job_title | string | Job title |
| location | string | City, state, country |
| confidence_score | float | Qualification score (50.0-100.0) |
| posting_url | string | Direct link to job posting |
| linkedin_managers | string | Google search URL for company managers |
| linkedin_hiring | string | Google search URL for recruiters |
| linkedin_role | string | Google search URL for specific role |
| google_enduser | string | Google search URL for CAD/design staff |
| date_scraped | string | YYYY-MM-DD |

### Errors JSON (POST /api/scraper/errors)

```json
{ "run_id": "...", "errors": [{ "search_term": "...", "site": "...", "error_type": "rate_limit|blocked|timeout|connection|unknown", "error_message": "...", "timestamp": "..." }] }
```

### Stats JSON (POST /api/scraper/stats)

```json
{ "run_id": "...", "total_searches": 65, "successful_searches": 63, "total_jobs_raw": 47776, "total_jobs_filtered": 3985, "unique_companies": 157, "filter_rate": 91.7, "run_duration_seconds": 5388, "site_breakdown": {...}, "qualification_tiers": {...} }
```

### Analytics JSON (POST /api/scraper/analytics) — optional

Deep diagnostics: per-search attempt timing, Cloudflare challenge stats, selector performance.

## API Contracts

All endpoints on ops-dashboard, authenticated with Bearer token (`DASHBOARD_API_KEY` here, `LEADS_API_KEY` on ops-dashboard):

| Endpoint | Format | Required? |
|----------|--------|-----------|
| POST /api/jobs/ingest | CSV (text/csv) | Yes |
| POST /api/scraper/errors | JSON | Yes |
| POST /api/scraper/stats | JSON | Yes |
| POST /api/scraper/analytics | JSON | No |

## Config Consumed

`config/filter-config.json` — scoring rules, exclusion patterns, company blocklist. Ops-dashboard can push changes to this file via GitHub PR (filter suggestions feedback loop).

## Environment Variables

```
DASHBOARD_URL          — ops-dashboard base URL
DASHBOARD_API_KEY      — API auth (maps to LEADS_API_KEY on ops-dashboard)
SCRAPER_BATCH          — 0-3 (which batch this worker runs)
SCRAPER_TOTAL_BATCHES  — 4 (total parallel workers)
SCRAPER_PROXIES        — Optional proxy list
ENABLE_BROWSER_SCRAPING — Enable Camoufox for ZipRecruiter/Glassdoor
```

## Key Files

| File | Purpose |
|------|---------|
| scraper.py | Main ETL: search terms, scoring, filtering, dedup (~2000 lines) |
| upload_results.py | API upload to ops-dashboard (4 endpoints) |
| camoufox_scraper.py | Browser automation for Cloudflare-protected sites |
| config/filter-config.json | Scoring rules, exclusions, blocklist |
| .github/workflows/scrape-leads.yml | CI: 4 parallel batch jobs |

## Key Functions

| Function | File | Description |
|----------|------|-------------|
| `scrape_solar_jobs()` | scraper.py ~L991 | Main scraping entry point |
| `score_job()` | scraper.py ~L706 | 6-tier qualification scoring |
| `classify_error()` | scraper.py ~L960 | Error categorization |
| `process_jobs()` | scraper.py ~L1547 | Deduplication and output formatting |
| `upload_to_dashboard()` | upload_results.py | POST CSV to /api/jobs/ingest |
| `upload_search_errors()` | upload_results.py | POST errors JSON |
| `upload_run_stats()` | upload_results.py | POST stats JSON |
| `upload_deep_analytics()` | upload_results.py | POST analytics JSON |

## Scoring System

6-tier scoring with instant-reject exclusions:
- Tier 1 (100pts): Solar-specific tools (Helioscope, Aurora Solar, PVSyst)
- Tier 2 (60pts): Strong signals + design context
- Tier 3 (40pts): CAD + project + design context
- Tier 4 (80pts): Explicit solar titles
- Tier 5 (30pts): CAD + design role (generic)
- Tier 6 (20pts): General design titles

Exclusions: tennis/racquet sports, aerospace, semiconductor, installation field roles, sales/marketing, management

Blocklist: Boeing, SpaceX, Northrop Grumman, Intel, Nvidia, AMD, TSMC, Tesla, etc.

## Error Types

`rate_limit` | `blocked` | `timeout` | `connection` | `unknown`

## Output Files (in output/)

- `solar_leads_{timestamp}.csv` — Qualified leads
- `run_stats_{timestamp}.json` — Run statistics
- `search_errors_{timestamp}.json` — Failed searches
- `deep_analytics_{timestamp}.json` — Detailed diagnostics

## Testing

The scraper takes a long time to run (65 search terms x 4 sites). For quick testing:
- Check existing output files in `output/`
- Run `pytest tests/` for unit tests (scoring, batch slicing)
- Build check: `python -m py_compile scraper.py upload_results.py camoufox_scraper.py`
