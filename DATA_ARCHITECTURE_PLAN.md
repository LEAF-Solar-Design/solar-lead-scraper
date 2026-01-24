# Data Architecture Plan: Solar Lead Scraper

> **Cross-Repo Coordination:** When making changes that affect other repos, see
> [ops-dashboard/CROSS_REPO_COORDINATION.md](../ops-dashboard/CROSS_REPO_COORDINATION.md)

## Role in Ecosystem

```
                              ┌─────────────────────────────────────┐
                              │         OPS-DASHBOARD (Hub)         │
                              │         Neon = Source of Truth      │
                              └─────────────────────────────────────┘
                                              ▲
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    │                                                   │
              ┌─────┴─────┐                                      ┌──────┴──────┐
              │  SCRAPER  │                                      │   HubSpot   │
              │  (this)   │                                      │   (mirror)  │
              └───────────┘                                      └─────────────┘
                    │                                                   ▲
                    │  POST /api/jobs/ingest                           │
                    │  POST /api/scraper/errors                         │
                    │  POST /api/scraper/stats                          │
                    │  POST /api/scraper/analytics (optional)           │
                    └───────────────────────────────────────────────────┘
                                    ops-dashboard syncs leads to HubSpot
```

**This Scraper's Role:**
- Stateless ETL pipeline (runs daily via GitHub Actions)
- Scrapes job boards (Indeed, LinkedIn, ZipRecruiter, Glassdoor)
- Filters and qualifies solar design leads
- **Pushes ONLY to ops-dashboard** - never directly to HubSpot or Neon
- ops-dashboard owns the lead data and decides what to sync

---

## Current Integrations Inventory

| Service | Purpose | Data Direction |
|---------|---------|----------------|
| **Indeed** | Job board scraping | Inbound (scrape) |
| **LinkedIn** | Job board scraping | Inbound (scrape) |
| **ZipRecruiter** | Job board scraping (Cloudflare bypass) | Inbound (scrape) |
| **Glassdoor** | Job board scraping (Cloudflare bypass) | Inbound (scrape) |
| **ops-dashboard API** | Lead ingestion | Outbound (POST) |
| **GitHub Artifacts** | Backup storage | Outbound (30-day retention) |

---

## Data Registry (Human-Readable)

```python
"""
SCRAPER DATA REGISTRY

Documents all data flowing in/out of the scraper.
Coordinates with ops-dashboard's master data registry.
"""

DATA_REGISTRY = {

    # ═══════════════════════════════════════════════════════════
    # INBOUND: Data we SCRAPE from job boards
    # ═══════════════════════════════════════════════════════════

    "inbound": {
        "job_boards": {
            "source": "Indeed, LinkedIn, ZipRecruiter, Glassdoor",
            "method": "Web scraping via python-jobspy + Camoufox",
            "fields": {
                "job_title":       "Job title from posting",
                "company":         "Company name",
                "location":        "Job location (city, state)",
                "job_description": "Full job description text",
                "posting_url":     "Direct URL to job posting",
                "date_posted":     "When the job was posted",
                "source_site":     "indeed | linkedin | zip_recruiter | glassdoor",
            },
            "volume": "~47,000 raw jobs per daily run",
            "filter_rate": "~8% pass rate (3,500-4,000 qualified leads)",
        },
    },

    # ═══════════════════════════════════════════════════════════
    # OUTBOUND: Data we SEND to ops-dashboard
    # ═══════════════════════════════════════════════════════════

    "outbound": {
        "leads": {
            "destination": "ops-dashboard: POST /api/jobs/ingest",
            "format": "CSV (text/csv)",
            "auth": "Bearer token (DASHBOARD_API_KEY)",
            "fields": {
                "company":           "Company name from job posting",
                "domain":            "Guessed company domain (best-effort)",
                "job_title":         "Job title",
                "location":          "Job location (city, state, country)",
                "confidence_score":  "Qualification score (50.0-100.0)",
                "posting_url":       "Direct link to job posting",
                "linkedin_managers": "Google search URL for company managers",
                "linkedin_hiring":   "Google search URL for recruiters",
                "linkedin_role":     "Google search URL for specific role",
                "google_enduser":    "Google search URL for CAD/design staff",
                "date_scraped":      "Date the job was scraped (YYYY-MM-DD)",
            },
            "stored_in": "ops-dashboard Neon: solar_leads table",
        },

        "errors": {
            "destination": "ops-dashboard: POST /api/scraper/errors",
            "format": "JSON",
            "auth": "Bearer token",
            "fields": {
                "search_term":    "What search term failed",
                "site":           "Which job board",
                "error_type":     "rate_limit | blocked | timeout | connection | unknown",
                "error_message":  "Error description",
                "timestamp":      "When the error occurred",
            },
            "purpose": "Debugging and monitoring scraper health",
        },

        "stats": {
            "destination": "ops-dashboard: POST /api/scraper/stats",
            "format": "JSON",
            "auth": "Bearer token",
            "fields": {
                "run_id":                 "Unique run identifier (timestamp-based)",
                "total_searches":         "Number of search terms attempted",
                "successful_searches":    "Searches that returned results",
                "total_jobs_raw":         "Total jobs scraped before filtering",
                "total_jobs_filtered":    "Jobs that passed qualification",
                "unique_companies":       "Deduplicated company count",
                "filter_rate":            "Percentage rejected by filter",
                "site_breakdown":         "Per-site success/fail counts",
                "qualification_tiers":    "How many leads per tier",
                "rejection_reasons":      "Why leads were rejected",
                "run_duration_seconds":   "Total scrape time",
            },
            "purpose": "Analytics on scraper performance",
        },

        "deep_analytics": {
            "destination": "ops-dashboard: POST /api/scraper/analytics",
            "format": "JSON",
            "auth": "Bearer token",
            "fields": {
                "run_id":                "Unique run identifier",
                "search_attempts":       "Per-search-term diagnostics with timing and errors",
                "cloudflare_stats":      "Challenge encounter and solve rates",
                "selector_performance":  "Browser scraping selector success rates",
                "session_diagnostics":   "Browser session health metrics",
            },
            "purpose": "Deep debugging for browser scraping issues (optional endpoint)",
        },

        "github_artifacts": {
            "destination": "GitHub Actions Artifacts",
            "retention": "30 days",
            "files": [
                "solar_leads_{timestamp}.csv",
                "run_stats_{timestamp}.json",
                "search_errors_{timestamp}.json",
                "deep_analytics_{timestamp}.json",
            ],
            "purpose": "Backup and audit trail",
        },
    },

    # ═══════════════════════════════════════════════════════════
    # LOCAL: Configuration files
    # ═══════════════════════════════════════════════════════════

    "local": {
        "filter_config": {
            "file": "config/filter-config.json",
            "fields": {
                "threshold":         "Minimum score to qualify (default: 50)",
                "company_blocklist": "Companies to always reject (Boeing, SpaceX, Intel, etc.)",
                "required_context":  "Must match solar/PV/Helioscope/PVSyst terms",
                "exclusions":        "Patterns that instantly reject (installer, aerospace, etc.)",
                "positive_signals":  "6-tier scoring system with weights",
            },
        },
    },
}
```

---

## Lead Data Schema (Sent to ops-dashboard)

This is the CSV format sent to `POST /api/jobs/ingest`:

| Column | Type | Example | Description |
|--------|------|---------|-------------|
| company | string | "Inty Power LLC" | Company name from job posting |
| domain | string | "intypower.com" | Guessed domain (best-effort) |
| job_title | string | "Design Manager - Solar Installation" | Job title |
| location | string | "Tempe, AZ, US" | Job location |
| confidence_score | float | 100.0 | Qualification score (50.0-100.0) |
| posting_url | string | "https://indeed.com/viewjob?jk=..." | Direct job link |
| linkedin_managers | string | "https://google.com/search?q=..." | Google search for managers |
| linkedin_hiring | string | "https://google.com/search?q=..." | Google search for recruiters |
| linkedin_role | string | "https://google.com/search?q=..." | Google search for role |
| google_enduser | string | "https://google.com/search?q=..." | Google search for CAD staff |
| date_scraped | string | "2026-01-19" | Scrape date |

### How ops-dashboard Stores This

In Neon `solar_leads` table:
```sql
CREATE TABLE solar_leads (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid(),
  company TEXT NOT NULL,
  domain TEXT,
  job_title TEXT,
  location TEXT,
  confidence_score DECIMAL(5,2),
  posting_url TEXT,
  linkedin_managers TEXT,
  linkedin_hiring TEXT,
  linkedin_role TEXT,
  google_enduser TEXT,
  date_scraped DATE,

  -- Tracking
  status TEXT DEFAULT 'new',  -- new | contacted | qualified | disqualified
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  -- Association (set by ops-dashboard when lead becomes customer)
  customer_email TEXT,
  associated_at TIMESTAMP,

  UNIQUE(company, job_title, date_scraped)  -- Prevent duplicates
);
```

---

## Coordination with ops-dashboard

### Current State
```
Scraper → ops-dashboard API → Neon (solar_leads table)
                            ↓
                         HubSpot (synced as contacts/companies)
```

### Data Flow

1. **Daily Scrape (2am CT)**
   - GitHub Actions triggers 4 parallel batch jobs
   - Each batch scrapes ~16 search terms across 4 sites
   - Results filtered and deduplicated

2. **Upload to ops-dashboard**
   - `POST /api/jobs/ingest` with CSV payload
   - ops-dashboard upserts into `solar_leads` table
   - Returns count of imported leads

3. **ops-dashboard Processing**
   - Deduplicates by (company, job_title, date_scraped)
   - Optionally syncs new leads to HubSpot as contacts/companies
   - Associates leads with customers by domain matching

---

## Qualification Tiers

The scraper uses a 6-tier scoring system:

| Tier | Score | Criteria | Example Match |
|------|-------|----------|---------------|
| Tier 1 | 100 | Solar-specific tools | "Helioscope", "Aurora Solar", "PVSyst" |
| Tier 2 | 60 | Strong signals + design | "stringing diagram", "module layout" |
| Tier 3 | 40 | CAD + project + design | Generic CAD + solar project context |
| Tier 4 | 80 | Explicit solar titles | "solar designer", "PV engineer" |
| Tier 5 | 30 | CAD + design role | Generic CAD/design without solar |
| Tier 6 | 20 | Design titles | General design titles |

**Threshold:** Score ≥ 50 to qualify

### Exclusions (Instant Reject)

- Tennis/racquet sports (false positives from "stringing")
- Aerospace/spacecraft (false positives from "solar panels")
- Semiconductor/chip design (false positives from CAD)
- Installation field roles (not our target)
- Sales/marketing roles (not our target)
- Management roles (not our target)

### Company Blocklist

- Boeing, SpaceX, Northrop Grumman, Lockheed Martin (aerospace)
- Intel, Nvidia, AMD, TSMC (semiconductor)
- Tesla (complex - has solar but also automotive)

---

## Environment Variables

```bash
# === REQUIRED ===
DASHBOARD_URL=https://ops-dashboard.example.com
DASHBOARD_API_KEY=sk_xxx

# === BATCH PROCESSING ===
SCRAPER_BATCH=0            # 0-3 (which batch to run)
SCRAPER_TOTAL_BATCHES=4    # Total parallel batches

# === OPTIONAL ===
SCRAPER_PROXIES=user:pass@proxy.com:8080,proxy2.com:3128
ENABLE_BROWSER_SCRAPING=1  # Enable Camoufox for ZipRecruiter/Glassdoor
CAMOUFOX_DEBUG=1           # Save debug screenshots
```

---

## ops-dashboard API Endpoints (Expected)

### POST /api/jobs/ingest

**Request:**
```http
POST /api/jobs/ingest
Authorization: Bearer sk_xxx
Content-Type: text/csv

company,domain,job_title,location,confidence_score,posting_url,linkedin_managers,linkedin_hiring,linkedin_role,google_enduser,date_scraped
"Inty Power LLC","intypower.com","Design Manager","Tempe, AZ",100.0,"https://indeed.com/...","https://google.com/...","https://google.com/...","https://google.com/...","https://google.com/...","2026-01-19"
```

**Response:**
```json
{
  "count": 157,
  "duplicates_skipped": 12,
  "errors": []
}
```

### POST /api/scraper/errors

**Request:**
```json
{
  "run_id": "20260119_020000",
  "errors": [
    {
      "search_term": "solar designer",
      "site": "linkedin",
      "error_type": "rate_limit",
      "error_message": "429 Too Many Requests",
      "timestamp": "2026-01-19T02:15:32Z"
    }
  ]
}
```

### POST /api/scraper/stats

**Request:**
```json
{
  "run_id": "20260119_020000",
  "total_searches": 65,
  "successful_searches": 63,
  "total_jobs_raw": 47776,
  "total_jobs_filtered": 3985,
  "unique_companies": 157,
  "filter_rate": 91.7,
  "run_duration_seconds": 5388,
  "site_breakdown": {
    "indeed": { "searches": 65, "jobs": 41172, "success_rate": 100 },
    "linkedin": { "searches": 65, "jobs": 6604, "success_rate": 100 }
  },
  "qualification_tiers": {
    "tier1_tools": 145,
    "tier4_title": 2145,
    "tier6_design_titles": 1840
  }
}
```

### POST /api/scraper/analytics (Optional)

Deep diagnostics for browser scraping debugging. Non-critical - failures are logged but don't stop the workflow.

**Request:**
```json
{
  "run_id": "20260119_020000",
  "search_attempts": [
    {
      "search_term": "solar designer",
      "site": "zip_recruiter",
      "attempts": [
        {
          "attempt_number": 1,
          "duration_seconds": 12.5,
          "success": false,
          "error": "Cloudflare challenge detected",
          "selectors_tried": ["div.job-card", "article.job"]
        }
      ]
    }
  ],
  "cloudflare_stats": {
    "challenges_encountered": 15,
    "challenges_solved": 12,
    "solve_rate": 80.0
  },
  "selector_performance": {
    "div.job-card": { "attempts": 50, "success": 45 },
    "article.job": { "attempts": 30, "success": 28 }
  }
}
```

---

## File Structure

```
solar-lead-scraper/
├── scraper.py                    # Main ETL script
├── upload_results.py             # Dashboard upload script
├── camoufox_scraper.py          # Browser scraping module
├── config/
│   └── filter-config.json       # Filter rules
├── output/                       # Local output directory
│   ├── solar_leads_*.csv
│   ├── run_stats_*.json
│   └── search_errors_*.json
├── .github/
│   └── workflows/
│       └── scrape-leads.yml     # GitHub Actions workflow
├── requirements.txt
└── DATA_ARCHITECTURE_PLAN.md    # This file
```

---

## Implementation Notes

### No Changes Needed for ops-dashboard Integration

The scraper already outputs in the correct format. ops-dashboard just needs:

1. **Endpoint to receive CSV** - `POST /api/jobs/ingest`
2. **Upsert logic** - Deduplicate by (company, job_title, date_scraped)
3. **Stats storage** - Store run stats for monitoring
4. **Error logging** - Store scraper errors for debugging

### Future Enhancements

1. **HubSpot sync** - ops-dashboard syncs new leads to HubSpot as contacts/companies
2. **Domain matching** - Associate leads with customers by email domain
3. **Lead status tracking** - Track contacted/qualified/disqualified status
4. **Duplicate detection** - Cross-reference with existing customers

---

## Verification Checklist

- [x] Scraper runs successfully via GitHub Actions
- [x] CSV uploads to ops-dashboard `/api/jobs/ingest`
- [x] Leads appear in Neon `solar_leads` table (ops-dashboard endpoints implemented)
- [x] Duplicate leads are deduplicated correctly (ops-dashboard endpoints implemented)
- [x] Error reports sent to `/api/scraper/errors`
- [x] Run stats sent to `/api/scraper/stats`
- [x] Deep analytics sent to `/api/scraper/analytics` (optional)
- [x] GitHub Artifacts retained for 30 days
