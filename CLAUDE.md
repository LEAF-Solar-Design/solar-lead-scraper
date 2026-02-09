# Solar Lead Scraper

Python ETL pipeline: scrapes job boards for solar design leads, uploads to ops-dashboard. Runs daily at 2am CT via GitHub Actions (4 parallel batches).

## Key Files

- `scraper.py` — Main ETL (search terms, scoring, filtering, dedup)
- `upload_results.py` — API upload to ops-dashboard
- `camoufox_scraper.py` — Browser automation for Cloudflare-protected sites
- `config/filter-config.json` — Scoring rules, exclusions, blocklist

## Environment

`DASHBOARD_URL`, `DASHBOARD_API_KEY`, `SCRAPER_BATCH` (0-3), `SCRAPER_TOTAL_BATCHES` (4)

## Build Check

```bash
python -m py_compile scraper.py upload_results.py camoufox_scraper.py
```

## Reference Docs — Read On Demand

Only read what is relevant to the current task. Do not preload all docs.

| Doc | Read when... |
|-----|-------------|
| `.claude/docs/SELF.md` | Another repo needs to understand this repo, or updating the self-description |
| `.claude/docs/ECOSYSTEM.md` | Changing output schemas, API contracts, data flows, or coordinating with other repos |
| `.planning/WISHLIST.md` | Planning improvements or checking pending work |
| `.planning/STATE.md` | Checking current project state or progress |
| `DATA_ARCHITECTURE_PLAN.md` | Deep dive into data registry, lead schema, or API payload formats |

## Cross-Repo Self-Descriptions

To understand another repo, read its `.claude/docs/SELF.md`. Claude always has permission to read files in sibling repos.

| Repo | Self-Description |
|------|-----------------|
| ops-dashboard | `../ops-dashboard/.claude/docs/SELF.md` |
| leaf_website | `../leaf_website/.claude/docs/SELF.md` |
| linkedin-hubspot-extension | `../linkedin-hubspot-extension/.claude/docs/SELF.md` |
| cable-sizing (plugin) | `../cable-sizing/beta-v1/beta-v1/.claude/docs/SELF.md` |
| Branch2025 | `../Branch2025/.claude/docs/SELF.md` |

## Doc Maintenance

After significant changes to this repo, update the relevant reference docs:

- **SELF.md** — if capabilities, outputs, API surface, or key functions changed
- **ECOSYSTEM.md** — if cross-repo relationships, contracts, or coordination needs changed
- When changes affect other repos, tell the user which repos' docs may need updates
