---
phase: 03-architecture-refactoring
plan: 03
subsystem: scoring
tags: [scoring, classification, separation-of-concerns, dataclass]

# Dependency graph
requires:
  - phase: 03-02
    provides: ScoringResult dataclass and score_job() function
provides:
  - score_company() function for company-level classification
  - score_role() function for role/description classification
  - ScoringResult with company_score and role_score fields
affects: [phase-4-quality, future-tuning, debugging]

# Tech tracking
tech-stack:
  added: []
  patterns: [separation-of-concerns, composed-scoring]

key-files:
  created: []
  modified: [scraper.py]

key-decisions:
  - "Company and role scoring as separate functions for independent tuning"
  - "ScoringResult tracks both scores for debugging visibility"
  - "score_job() is thin orchestrator delegating to specialized functions"

patterns-established:
  - "Composed scoring: score_job() calls score_company() then score_role()"
  - "Short-circuit on negative: return immediately if company or role is disqualified"

# Metrics
duration: 4min
completed: 2026-01-18
---

# Phase 3 Plan 3: Separate Company and Role Classification Summary

**Extracted company classification into score_company() and role classification into score_role() for independent tuning and debugging**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-18
- **Completed:** 2026-01-18
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- ScoringResult dataclass extended with company_score and role_score fields
- score_company() handles blocklist checks (returns -100 for blocked companies)
- score_role() handles all description-based signals (tiers 1-6, exclusions)
- score_job() refactored to thin orchestrator delegating to specialized functions
- ARCH-03 satisfied: Company classification separated from role classification

## Task Commits

All three tasks committed atomically as one refactoring:

1. **Task 1-3: Separate company and role classification** - `993073a` (refactor)

**Plan metadata:** (included in task commit)

## Files Created/Modified

- `scraper.py` - Added score_company(), score_role() functions; updated ScoringResult dataclass; refactored score_job()

## Decisions Made

- **Composed scoring pattern:** score_job() calls score_company() first, then score_role() if company passes
- **Short-circuit on negative:** If company_score < 0 or role_score < 0, return immediately without further processing
- **Additive ScoringResult fields:** company_score and role_score default to 0.0 for backward compatibility

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 complete: All architecture refactoring objectives achieved
- ARCH-01 (externalized config), ARCH-02 (weighted scoring), ARCH-03 (separated classification), ARCH-04 (score+reasons) all satisfied
- Ready for Phase 4: Quality improvements with recall focus
- Debugging now easier: can inspect company_score vs role_score to understand classification

---
*Phase: 03-architecture-refactoring*
*Completed: 2026-01-18*
