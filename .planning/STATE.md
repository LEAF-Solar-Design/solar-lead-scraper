# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-18)

**Core value:** Surface high-quality leads by finding companies actively hiring for solar design roles
**Current focus:** Phase 3 - Architecture Refactoring (in progress)

## Current Position

Phase: 3 of 4 (Architecture Refactoring)
Plan: 2 of 3 in current phase
Status: In progress
Last activity: 2026-01-18 - Completed 03-02-PLAN.md

Progress: [██████░░░░] 60%

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: 3.6 min
- Total execution time: 25 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Metrics Foundation | 2/2 | 6 min | 3 min |
| 2. Data-Driven Rules | 3/3 | 11 min | 3.67 min |
| 3. Architecture | 2/3 | 8 min | 4 min |
| 4. Quality | 0/2 | - | - |

**Recent Trend:**
- Last 5 plans: 02-02 (4 min), 02-03 (4 min), 03-01 (4 min), 03-02 (4 min)
- Trend: Consistent (~4 min per plan)

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
- Phase 2 focused on precision defense, recall improvement deferred (02-03)
- All exclusions verified with targeted test cases (02-03)
- JSON for configuration over YAML - zero dependencies (03-01)
- Lazy config loading with module-level caching (03-01)
- ScoringResult dataclass over dict/tuple for type safety (03-02)
- Score -100 for hard disqualifications vs 0 for neutral (03-02)
- Backward-compatible wrapper maintains API stability (03-02)

### Pending Todos

None yet.

### Blockers/Concerns

- Class imbalance: Only 16 qualified vs 514 rejected examples
- Golden test set now 41 items (was 33) - still relatively small
- 4 false negatives in tier4/tier5 remain (title signal detection issue)

## Session Continuity

Last session: 2026-01-18
Stopped at: Completed 03-02-PLAN.md
Resume file: None

## Completed Phases

### Phase 1: Metrics Foundation (complete)

**Deliverables:**
- `evaluate.py` - Evaluation infrastructure with precision/recall metrics (295 lines)
- `data/golden/golden-test-set.json` - 41-item curated regression test set
- `.planning/phases/01-metrics-foundation/01-BASELINE.md` - Baseline metrics documentation

**Baseline Results:** 100% precision, 75% recall, F1 85.71%
**Verified:** 2026-01-18

### Phase 2: Data-Driven Rule Refinement (complete)

**Summary:** Added company blocklist, installer/utility exclusions, EDA tool exclusions. Expanded golden test set to 41 items. Maintained 100% precision throughout.

**Deliverables:**
- `COMPANY_BLOCKLIST` with 28 aerospace/semiconductor companies
- 5 installer role exclusions (stringer, roofer, foreman, crew lead, panel installer)
- 4 utility engineering exclusions (interconnection, grid, protection, metering)
- 22 EDA tool exclusions (Cadence, Synopsys, Mentor Graphics, etc.)
- Golden test set expanded: 33 -> 41 items
- `.planning/phases/02-data-driven-rules/02-METRICS.md` - Phase 2 metrics

**Final Metrics:** 100% precision, 75% recall, F1 85.71%
**Test Coverage:** 16 positive, 25 negative examples (all pass)
**Completed:** 2026-01-18
**Verified:** 2026-01-18 (7/7 must-haves confirmed)

#### Plan 02-01: Company Blocklist (complete)

**Deliverables:**
- `COMPANY_BLOCKLIST` constant with 28 aerospace/semiconductor companies
- `description_matches()` updated to accept `company_name` parameter
- Company blocklist check runs before description analysis
- 2 new regression tests for blocked companies

**Results:** 100% precision, 75% recall maintained (no regressions)
**Completed:** 2026-01-18

#### Plan 02-02: Add Missing Exclusion Terms (complete)

**Deliverables:**
- 5 new installer exclusions: stringer, roofer, foreman, crew lead, panel installer
- 4 new utility engineering exclusions: interconnection, grid, protection, metering engineers
- New `eda_tools` exclusion block with 22 EDA vendors and tools (Cadence, Synopsys, etc.)

**Results:** 100% precision, 75% recall maintained (no regressions)
**Commits:** 5ffa0b2, 1f078a3, f99b19c
**Completed:** 2026-01-18

#### Plan 02-03: Validate Rules and Document Metrics (complete)

**Deliverables:**
- Golden test set expanded from 33 to 41 items
- 6 new test cases (2 EDA, 2 installer, 2 utility)
- `.planning/phases/02-data-driven-rules/02-METRICS.md` with before/after comparison
- All 4 requirements (RULE-01 through RULE-04) documented as satisfied

**Results:** 100% precision, 75% recall maintained (no regressions)
**Commits:** 32d8be5, a3277b9
**Completed:** 2026-01-18

### Phase 3: Architecture Refactoring (in progress)

#### Plan 03-01: Externalize Filter Configuration (complete)

**Deliverables:**
- `config/filter-config.json` - External filter configuration (94 lines)
- `load_filter_config()` and `get_config()` functions in scraper.py
- `description_matches()` refactored to read terms from config

**Results:** 100% precision, 75% recall maintained (no regressions)
**ARCH-01 satisfied:** Filter terms editable via JSON without code changes
**Commits:** ac6ac9e, d234ed5
**Completed:** 2026-01-18

#### Plan 03-02: Weighted Scoring System (complete)

**Deliverables:**
- `ScoringResult` dataclass with score, qualified, reasons, threshold fields
- `score_job()` function implementing weighted scoring (134 lines)
- `description_matches()` refactored to thin wrapper (87 lines -> 2 lines)

**Results:** 100% precision, 75% recall maintained (no regressions)
**ARCH-02 satisfied:** Tiered boolean filter converted to weighted scoring
**ARCH-04 satisfied:** Filter returns score + reasons (via ScoringResult)
**Commits:** 95bfa70, be5faf4, 63bdf55
**Completed:** 2026-01-18

## Next Steps

**Remaining Phase 3 Plans:**
- 03-03: Improve title signal detection

**Outstanding Issues:**
- 4 false negatives need title signal improvements
- Can now debug with score_job() reasons to understand scoring gaps
- Consider expanding title detection area beyond first 200 chars
