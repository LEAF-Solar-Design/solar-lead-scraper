# Technology Stack

**Analysis Date:** 2026-01-18

## Languages

**Primary:**
- Python 3.11 - All application code

**Secondary:**
- YAML - CI/CD workflow configuration

## Runtime

**Environment:**
- Python 3.11 (specified in GitHub Actions workflow)
- No `.python-version` or `pyproject.toml` present

**Package Manager:**
- pip (standard Python package manager)
- Lockfile: Not present (only `requirements.txt` with unpinned versions)

## Frameworks

**Core:**
- python-jobspy (latest) - Job board scraping library for Indeed, ZipRecruiter, Glassdoor
- pandas (latest) - Data manipulation and CSV export

**Testing:**
- None configured

**Build/Dev:**
- GitHub Actions - CI/CD automation

## Key Dependencies

**Critical:**
- `python-jobspy` - Core scraping functionality; scrapes job postings from multiple job boards
- `pandas` - DataFrame operations, CSV I/O, data filtering
- `requests` - HTTP client for dashboard API uploads (installed separately in CI)

**Infrastructure:**
- None (no database, no caching, no message queues)

## Configuration

**Environment:**
- Environment variables loaded via `os.environ.get()` in `upload_results.py`
- Required env vars:
  - `DASHBOARD_URL` - Base URL for ops-dashboard API
  - `DASHBOARD_API_KEY` - Bearer token for API authentication
- `.env` file supported locally (in `.gitignore`)

**Build:**
- `requirements.txt` - Python dependencies
- `.github/workflows/scrape-leads.yml` - CI/CD workflow

## Platform Requirements

**Development:**
- Python 3.11+
- pip
- No additional system dependencies

**Production:**
- Runs on GitHub Actions (ubuntu-latest)
- Scheduled execution via cron (daily at 4am CT / 10:00 UTC)
- Manual trigger available via workflow_dispatch

---

*Stack analysis: 2026-01-18*
