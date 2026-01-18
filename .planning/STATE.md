# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-18)

**Core value:** Surface high-quality leads by finding companies actively hiring for solar design roles
**Current focus:** Phase 4 - Quality Instrumentation (COMPLETE)

## Current Position

Phase: 4 of 4 (Quality Instrumentation)
Plan: 2 of 2 in current phase
Status: Milestone complete - all phases verified
Last activity: 2026-01-18 - Phase 4 verified and complete

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 10
- Average duration: 3.5 min
- Total execution time: 35 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Metrics Foundation | 2/2 | 6 min | 3 min |
| 2. Data-Driven Rules | 3/3 | 11 min | 3.67 min |
| 3. Architecture | 3/3 | 12 min | 4 min |
| 4. Quality | 2/2 | 6 min | 3 min |

**Recent Trend:**
- Last 5 plans: 03-02 (4 min), 03-03 (4 min), 04-01 (3 min), 04-02 (3 min)
- Trend: Consistent (~3-4 min per plan)

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
- Company and role scoring as separate functions for independent tuning (03-03)
- ScoringResult tracks company_score and role_score for debugging visibility (03-03)
- score_job() is thin orchestrator delegating to specialized functions (03-03)
- Counter from collections for stats aggregation (04-01)
- Categorize rejections to config section names for correlation (04-01)
- Confidence score capped at 100 (score 50=threshold, 100+=100%) (04-02)
- Rejected leads export matches golden-test-set.json schema (04-02)
- Default max_export=100 to avoid huge files (04-02)

### Pending Todos

None - all planned work complete.

### Blockers/Concerns

- Class imbalance: Only 16 qualified vs 514 rejected examples
- Golden test set now 41 items (was 33) - still relatively small
- 4 false negatives in tier4/tier5 remain (title signal detection issue)

## Session Continuity

Last session: 2026-01-18
Stopped at: Milestone complete - all phases verified
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

### Phase 3: Architecture Refactoring (complete)

**Summary:** Externalized filter configuration to JSON, converted boolean filter to weighted scoring system, separated company and role classification. All ARCH requirements satisfied.

**Deliverables:**
- `config/filter-config.json` - External filter configuration
- `ScoringResult` dataclass with score, qualified, reasons, company_score, role_score
- `score_job()`, `score_company()`, `score_role()` functions
- `description_matches()` as backward-compatible wrapper

**ARCH Requirements:**
- ARCH-01: Filter terms editable via JSON without code changes
- ARCH-02: Tiered boolean filter converted to weighted scoring
- ARCH-03: Company classification separated from role classification
- ARCH-04: Filter returns score + reasons (via ScoringResult)

**Final Metrics:** 100% precision, 75% recall, F1 85.71% (no regressions)
**Completed:** 2026-01-18

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

#### Plan 03-03: Separate Company and Role Classification (complete)

**Deliverables:**
- `ScoringResult` extended with `company_score` and `role_score` fields
- `score_company()` function for company-level classification (blocklist)
- `score_role()` function for role/description classification (tiers 1-6)
- `score_job()` refactored to thin orchestrator

**Results:** 100% precision, 75% recall maintained (no regressions)
**ARCH-03 satisfied:** Company classification separated from role classification
**Commits:** 993073a
**Completed:** 2026-01-18
**Verified:** 2026-01-18 (4/4 must-haves confirmed)

### Phase 4: Quality Instrumentation (complete)

**Summary:** Added per-rule statistics logging, rejected lead export for labeling, and confidence scores in output. All QUAL requirements satisfied.

**Deliverables:**
- `FilterStats` dataclass with Counter aggregation
- `categorize_rejection()` and `extract_tier_from_reasons()` helpers
- `export_rejected_leads()` function producing JSON for labeling workflow
- `scrape_solar_jobs()` returns (DataFrame, FilterStats, rejected_leads, scoring_results)
- `process_jobs()` adds confidence_score column
- `print_filter_stats()` displays human-readable statistics
- `main()` wires stats display and rejected lead export

**QUAL Requirements:**
- QUAL-01: Each run logs filter statistics
- QUAL-02: Rejected leads can be exported for labeling
- QUAL-03: Qualified leads include confidence score

**Final Metrics:** 100% precision, 75% recall, F1 85.71% (no regressions)
**Completed:** 2026-01-18

#### Plan 04-01: Filter Statistics (complete)

**Deliverables:**
- `FilterStats` dataclass with Counter aggregation
- `categorize_rejection()` and `extract_tier_from_reasons()` helpers
- `scrape_solar_jobs()` returns (DataFrame, FilterStats) tuple
- `print_filter_stats()` displays human-readable statistics
- `main()` wires stats display after each run

**Results:** 100% precision, 75% recall maintained (no regressions)
**QUAL-01 satisfied:** Each run logs filter statistics
**Commits:** 5919165, 23d5cc8, c46af01
**Completed:** 2026-01-18

#### Plan 04-02: Rejected Lead Export and Confidence Scores (complete)

**Deliverables:**
- `export_rejected_leads()` function exporting JSON matching golden-test-set.json schema
- `scrape_solar_jobs()` returns 4-tuple including rejected_leads and scoring_results
- `process_jobs()` accepts scoring_results and adds confidence_score column
- `main()` exports rejected leads and passes scoring to process_jobs

**Results:** 100% precision, 75% recall maintained (no regressions)
**QUAL-02 satisfied:** Rejected leads can be exported for labeling
**QUAL-03 satisfied:** Qualified leads include confidence score
**Commits:** eecab7d, 8c5fd76, 33a6df7
**Completed:** 2026-01-18

## Project Complete

All 4 phases complete. All requirements satisfied:

| Phase | Requirements | Status |
|-------|--------------|--------|
| 1. Metrics Foundation | METRIC-01, METRIC-02, METRIC-03 | DONE |
| 2. Data-Driven Rules | RULE-01, RULE-02, RULE-03, RULE-04 | DONE |
| 3. Architecture | ARCH-01, ARCH-02, ARCH-03, ARCH-04 | DONE |
| 4. Quality Instrumentation | QUAL-01, QUAL-02, QUAL-03 | DONE |

**Final Metrics:**
- Precision: 100%
- Recall: 75%
- F1 Score: 85.71%
- Golden test set: 41 items (16 positive, 25 negative)

**Outstanding Issues for Future Work:**
- 4 false negatives in tier4/tier5 remain (title signal detection issue)
- Consider expanding title detection area beyond first 200 chars
- Class imbalance: Only 16 qualified examples - need more positives for ML
