# Solar Lead Scraper — Ecosystem & Cross-Repo Relationships

## Architecture

```
ops-dashboard (Hub) <-- Neon DB (source of truth)
     ^
     |
     |--- scraper (THIS REPO) --> sends leads, stats, errors via API
     |--- leaf_website --> sends signups/subscriptions
     |--- linkedin-hubspot-extension --> sends CRM activity
     |--- cable-sizing plugin --> sends usage telemetry via BigQuery
     |--- Branch2025 --> legacy plugin version
```

This scraper pushes ONLY to ops-dashboard. It never writes directly to HubSpot, Neon, or BigQuery.

## How Other Repos Relate to This One

### ops-dashboard (DIRECT — receives our data)

**Relationship:** Primary consumer. Receives all scraper output via 4 API endpoints.

- `POST /api/jobs/ingest` — CSV of qualified leads -> stored in Neon `solar_leads` table
- `POST /api/scraper/errors` — JSON error reports for monitoring
- `POST /api/scraper/stats` — JSON run statistics for analytics
- `POST /api/scraper/analytics` — JSON deep diagnostics (optional)

**Auth:** Bearer token. This repo uses `DASHBOARD_API_KEY`, ops-dashboard expects `LEADS_API_KEY`.

**Filter suggestions feedback loop:** ops-dashboard analyzes lead feedback, generates filter config changes, and creates PRs against this repo's `config/filter-config.json` via GitHub API. When PRs auto-merge, the next scraper run uses updated filters.

**Coordinate when changing:** CSV column names/types, new fields, API payload format, error/stats JSON shape.

**Self-description:** `../ops-dashboard/.claude/docs/SELF.md`

### leaf_website (INDIRECT — no direct connection)

**Relationship:** No direct data exchange. Shares customers indirectly through ops-dashboard. Leads we find may become customers who sign up on the website.

**Self-description:** `../leaf_website/.claude/docs/SELF.md`

### linkedin-hubspot-extension (INDIRECT — no direct connection)

**Relationship:** No direct data exchange. The extension may contact leads we discovered (via HubSpot contacts that ops-dashboard creates from our leads).

**Self-description:** `../linkedin-hubspot-extension/.claude/docs/SELF.md`

### cable-sizing plugin (INDIRECT — no direct connection)

**Relationship:** No direct data exchange. End users of the product. Leads we find -> become customers -> use the plugin. Plugin telemetry flows to ops-dashboard via BigQuery.

**Self-description:** `../cable-sizing/beta-v1/beta-v1/.claude/docs/SELF.md`

### Branch2025 (INDIRECT — no direct connection)

**Relationship:** Legacy/alternate version of the plugin. Same indirect relationship as cable-sizing.

**Self-description:** `../Branch2025/.claude/docs/SELF.md`

## When to Coordinate with Other Repos

Check coordination docs BEFORE making these changes:

| Change | Affects | Action |
|--------|---------|--------|
| CSV column names or types | ops-dashboard `/api/jobs/ingest` | Deploy ops-dashboard changes first |
| New fields being captured | ops-dashboard ingest endpoint | Coordinate schema update |
| Error/stats JSON format | ops-dashboard error/stats endpoints | Deploy ops-dashboard changes first |
| filter-config.json structure | ops-dashboard filter suggestions | Coordinate config format changes |

## Coordination Documents (in ops-dashboard)

For cross-repo changes, read these docs in ops-dashboard:

| Doc | Purpose |
|-----|---------|
| `../ops-dashboard/CROSS_REPO_COORDINATION.md` | Change propagation matrix, shared schemas, step-by-step scenarios |
| `../ops-dashboard/DATA_ARCHITECTURE_PLAN.md` | Master data flows, Neon schema, all integration points |
| `../ops-dashboard/MASTER_WISHLIST.md` | Cross-repo prioritized wishlist with owners and dependencies |

## API Contract Details

### Authentication

All ops-dashboard endpoints use Bearer token auth:
```
Authorization: Bearer <DASHBOARD_API_KEY>
```
On ops-dashboard side, this maps to the `LEADS_API_KEY` environment variable.

### Deployment Order for Breaking Changes

1. Deploy ops-dashboard changes first (new/modified endpoints)
2. Verify endpoints are live
3. Deploy scraper changes (new/modified output format)
4. Verify next scraper run succeeds
