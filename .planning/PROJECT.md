# Solar Lead Scraper

## What This Is

A Python scraper that finds job listings for solar CAD/design roles, which indicate companies with demonstrated demand for solar design work. These companies are ideal sales prospects for solar design automation software (stringing, wire schedules, plan sets). The scraper also generates LinkedIn search URLs to find decision-makers and end-users at those companies.

## Core Value

Surface high-quality leads by finding companies actively hiring for the exact roles that would use solar design software - drafters, CAD technicians, and PV designers doing permit sets and stringing layouts.

## Requirements

### Validated

- Scrape job listings from Indeed, ZipRecruiter, Glassdoor via jobspy
- Filter results based on job description content
- Generate LinkedIn search URLs for managers/directors
- Generate LinkedIn search URLs for specific role matches
- Output to CSV with company, job title, location, posting URL
- Tier-based filtering system (solar-specific tools > strong signals > general CAD)

### Active

- [ ] Improve precision - reduce false positives (514 rejected vs 16 qualified in recent runs)
- [ ] Add pattern learning from rejected leads data
- [ ] Add pattern learning from qualified leads data
- [ ] Reduce noise from non-solar industries (tennis, utility linemen, aerospace, semiconductor)
- [ ] Better company-level filtering (solar companies vs generic)

### Out of Scope

- Real-time scraping/monitoring - batch runs are sufficient
- CRM integration - CSV export is the interface
- Automated outreach - this is lead generation only
- Web UI - CLI tool is sufficient

## Context

**Current state:**
- Scraper works but has low precision (~3% qualified rate based on recent labeling)
- Filter is already sophisticated with 6 tiers but still passes too many false positives
- Main false positive categories from rejected leads:
  1. Tennis/racquet sports (from "stringing" term)
  2. Utility linemen/lineworkers
  3. General electrical engineers at non-solar companies (Tesla, SpaceX, Boeing)
  4. BESS/battery/microgrid engineers
  5. Solar sales/installer/field tech roles
  6. Civil/structural engineers adjacent to solar projects

**Qualified lead patterns:**
- Companies: Sundog Solar, Soltage, EDP Renewables, Kimley-Horn (solar practice), Shoals Technologies
- Titles: "Solar Design Engineer", "CAD Designer", "AutoCAD Drafter", "PV Electrical Engineer", "Electrical Designer - Power & Energy"
- Common thread: Design/drafting roles at solar-focused companies

**Training data available:**
- `rejected-leads-2026-01-16.json` - 253 rejected leads
- `rejected-leads-2026-01-17.json` - 261 rejected leads
- `qualified-leads-2026-01-18.json` - 16 qualified leads

## Constraints

- **Tech stack**: Python, jobspy library, pandas - keep simple
- **Data source**: Indeed/ZipRecruiter/Glassdoor via jobspy - no API changes
- **Output format**: CSV compatible with existing workflow

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use description filtering vs title filtering | Titles are inconsistent, descriptions have more signal | -- Pending (need to evaluate adding more title-based filters) |
| Wide search + strict filter approach | Cast broad net, let filter narrow | -- Pending (may be causing too much noise) |

---
*Last updated: 2026-01-18 after initialization*
