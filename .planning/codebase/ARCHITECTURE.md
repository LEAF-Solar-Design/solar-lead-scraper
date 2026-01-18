# Architecture

**Analysis Date:** 2026-01-18

## Pattern Overview

**Overall:** Pipeline/ETL Script Architecture

**Key Characteristics:**
- Single-purpose data extraction and transformation pipeline
- Two-stage execution: scrape then upload
- Stateless processing with file-based intermediate storage
- Scheduled execution via GitHub Actions cron job

## Layers

**Data Acquisition Layer:**
- Purpose: Fetch raw job listings from external job boards
- Location: `scraper.py` (functions: `scrape_solar_jobs`)
- Contains: Job board API integration via python-jobspy library
- Depends on: python-jobspy external library
- Used by: Main orchestration function

**Filtering Layer:**
- Purpose: Apply multi-tier content filtering to identify qualified solar design job leads
- Location: `scraper.py` (functions: `description_matches`)
- Contains: 6-tier qualification logic with inclusion/exclusion rules
- Depends on: Raw job data from acquisition layer
- Used by: Data acquisition layer (applied during scraping)

**Transformation Layer:**
- Purpose: Clean, deduplicate, and enrich job data into sales leads
- Location: `scraper.py` (functions: `process_jobs`, `clean_company_name`, `guess_domain`, `generate_linkedin_*`)
- Contains: Company deduplication, domain guessing, LinkedIn search URL generation
- Depends on: Filtered job DataFrame
- Used by: Main orchestration function

**Persistence Layer:**
- Purpose: Store processed leads as CSV files
- Location: `scraper.py` (main function), `output/` directory
- Contains: Timestamped CSV file writing
- Depends on: Transformed DataFrame
- Used by: Upload layer, GitHub Actions artifact storage

**Upload Layer:**
- Purpose: Send processed leads to external dashboard API
- Location: `upload_results.py`
- Contains: CSV file discovery, HTTP POST to dashboard API
- Depends on: CSV files in `output/` directory, environment variables for auth
- Used by: GitHub Actions workflow

## Data Flow

**Primary Scrape Flow:**

1. `main()` in `scraper.py` initiates execution
2. `scrape_solar_jobs()` iterates through 40+ search terms
3. For each term, calls `jobspy.scrape_jobs()` to fetch from Indeed, ZipRecruiter, Glassdoor
4. `description_matches()` filters each job against 6-tier qualification criteria
5. Results concatenated into single DataFrame
6. `process_jobs()` dedupes by company, adds domain guesses and LinkedIn search URLs
7. Final DataFrame saved to `output/solar_leads_{timestamp}.csv`

**Upload Flow:**

1. `main()` in `upload_results.py` initiates execution
2. `get_latest_csv()` finds most recent CSV by filename
3. `upload_to_dashboard()` reads CSV and POSTs to external API
4. Response logged, errors raised

**State Management:**
- No persistent state between runs
- Each run produces independent timestamped output file
- File-based handoff between scraper.py and upload_results.py
- Environment variables provide runtime configuration

## Key Abstractions

**Lead DataFrame Schema:**
- Purpose: Standardized structure for sales leads
- Columns: `company`, `domain`, `job_title`, `location`, `posting_url`, `linkedin_managers`, `linkedin_hiring`, `linkedin_role`, `google_enduser`, `date_scraped`
- Pattern: Pandas DataFrame with consistent column ordering

**Filter Tiers:**
- Purpose: Multi-level qualification system for identifying relevant job postings
- Location: `scraper.py` lines 153-220 in `description_matches()`
- Pattern: Cascading if-return statements with early exclusion, tiered inclusion
- Tiers:
  - Tier 1: Solar-specific tools (helioscope, aurora solar, pvsyst)
  - Tier 2: Strong technical signals + design role
  - Tier 3: General CAD tools + design role + solar project type
  - Tier 4: Explicit solar design job title
  - Tier 5: CAD tool + design role (with solar context from earlier check)
  - Tier 6: Design role titles with implicit solar context

**LinkedIn Search URL Generators:**
- Purpose: Create actionable research links for sales team
- Location: `scraper.py` lines 15-48
- Examples: `generate_linkedin_search_url()`, `generate_linkedin_hiring_search_url()`, `generate_linkedin_enduser_search_url()`
- Pattern: URL-encoded Google site search queries targeting linkedin.com/in/

## Entry Points

**CLI Execution - Scraper:**
- Location: `scraper.py` line 408: `if __name__ == "__main__": main()`
- Triggers: Manual execution (`python scraper.py`) or GitHub Actions
- Responsibilities: Execute full scrape pipeline, save CSV output

**CLI Execution - Uploader:**
- Location: `upload_results.py` line 60: `if __name__ == "__main__": main()`
- Triggers: GitHub Actions after scraper completes
- Responsibilities: Find latest CSV, upload to dashboard API

**GitHub Actions Entry:**
- Location: `.github/workflows/scrape-leads.yml`
- Triggers: Daily cron (4am CT / 10:00 UTC) or manual workflow_dispatch
- Responsibilities: Set up environment, run scraper.py, run upload_results.py, archive artifacts

## Error Handling

**Strategy:** Fail-fast with printed diagnostics

**Patterns:**
- Try-except around individual search term scrapes (continues on failure)
- Early return with print message when no jobs found
- Exception raised on upload failure (fails workflow)
- No retry logic implemented
- No structured logging (uses print statements)

## Cross-Cutting Concerns

**Logging:** Print statements to stdout; no structured logging framework
**Validation:** Implicit via pandas operations and type checks
**Authentication:** Environment variables (`DASHBOARD_URL`, `DASHBOARD_API_KEY`) for upload API auth
**Rate Limiting:** None explicitly implemented; relies on python-jobspy library behavior

---

*Architecture analysis: 2026-01-18*
