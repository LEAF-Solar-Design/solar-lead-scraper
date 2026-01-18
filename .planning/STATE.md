# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-18)

**Core value:** Surface high-quality leads by finding companies actively hiring for solar design roles
**Current focus:** Phase 2 - Data-Driven Rules (Plan 2 complete)

## Current Position

Phase: 2 of 4 (Data-Driven Rule Refinement)
Plan: 2 of 3 in current phase
Status: In progress
Last activity: 2026-01-18 - Completed 02-02-PLAN.md (Add Missing Exclusion Terms)

Progress: [████░░░░░░] 40%

## Performance Metrics

**Velocity:**
- Total plans completed: 4
- Average duration: 3.25 min
- Total execution time: 13 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Metrics Foundation | 2/2 | 6 min | 3 min |
| 2. Data-Driven Rules | 2/3 | 7 min | 3.5 min |
| 3. Architecture | 0/3 | - | - |
| 4. Quality | 0/2 | - | - |

**Recent Trend:**
- Last 5 plans: 01-01 (3 min), 01-02 (3 min), 02-01 (3 min), 02-02 (4 min)
- Trend: Consistent

## Accumulated Context

### Decisions

Decisions logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Data-driven before ML: Start with rule refinement, add ML when 50+ positives
- Scoring over boolean: Convert tier system to weighted scoring
- JSON format flexibility: evaluate.py supports both wrapped and raw array formats
- Labeled data schema: {id, description, label, company?, title?, notes?}
- Golden test set covers all 6 tiers and 8 false positive categories
- Baseline: 100% precision, 75% recall - focus improvement on recall
- 4 false negatives identified: tier4 title signals and tier5 CAD design roles
- Company blocklist check runs before description analysis (02-01)
- Blocklist uses substring matching for company name variants (02-01)
- EDA tools separated from semiconductor terms as distinct exclusion block (02-02)
- Stringer added to installer_terms (catches tennis and solar stringing labor) (02-02)

### Pending Todos

None yet.

### Blockers/Concerns

- Class imbalance: Only 16 qualified vs 514 rejected examples
- Golden test set is small (35 items) - metrics have variance
- 4 false negatives in tier4/tier5 need investigation in Plan 02-03

## Session Continuity

Last session: 2026-01-18
Stopped at: Completed 02-02-PLAN.md (Add Missing Exclusion Terms)
Resume file: None

## Completed Phases

### Phase 1: Metrics Foundation (complete)

**Deliverables:**
- `evaluate.py` - Evaluation infrastructure with precision/recall metrics (295 lines)
- `data/golden/golden-test-set.json` - 35-item curated regression test set
- `.planning/phases/01-metrics-foundation/01-BASELINE.md` - Baseline metrics documentation

**Baseline Results:** 100% precision, 75% recall, F1 85.71%
**Verified:** 2026-01-18

## Phase 2 Progress

### Plan 02-01: Company Blocklist (complete)

**Deliverables:**
- `COMPANY_BLOCKLIST` constant with 28 aerospace/semiconductor companies
- `description_matches()` updated to accept `company_name` parameter
- Company blocklist check runs before description analysis
- 2 new regression tests for blocked companies

**Results:** 100% precision, 75% recall maintained (no regressions)
**Completed:** 2026-01-18

### Plan 02-02: Add Missing Exclusion Terms (complete)

**Deliverables:**
- 5 new installer exclusions: stringer, roofer, foreman, crew lead, panel installer
- 4 new utility engineering exclusions: interconnection, grid, protection, metering engineers
- New `eda_tools` exclusion block with 22 EDA vendors and tools (Cadence, Synopsys, etc.)

**Results:** 100% precision, 75% recall maintained (no regressions)
**Commits:** 5ffa0b2, 1f078a3, f99b19c
**Completed:** 2026-01-18
