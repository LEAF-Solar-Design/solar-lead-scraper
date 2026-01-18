---
phase: "03"
plan: "02"
subsystem: "filtering"
tags: ["scoring", "weighted", "dataclass", "architecture", "confidence"]

dependency_graph:
  requires:
    - "03-01: externalize-filter-config"
  provides:
    - "ScoringResult dataclass"
    - "score_job() weighted scoring function"
    - "Numeric confidence levels"
    - "Scoring reasons for debugging"
  affects:
    - "03-03: title-signal-detection"
    - "04-quality-gates"

tech_stack:
  added:
    - "dataclasses module (stdlib)"
  patterns:
    - "Result objects over primitive returns"
    - "Weighted scoring with configurable threshold"
    - "Backward-compatible wrappers for API stability"

key_files:
  created: []
  modified:
    - "scraper.py"

decisions:
  - decision: "ScoringResult as dataclass over dict/tuple"
    rationale: "Type safety, clear field names, IDE autocomplete, immutable by convention"
  - decision: "Score -100 for hard disqualifications"
    rationale: "Clear separation from 0 (no signals) vs actively excluded"
  - decision: "Reasons list tracks all scoring decisions"
    rationale: "Enables debugging why a job qualified/rejected without re-running"
  - decision: "description_matches kept as thin wrapper"
    rationale: "Zero breaking changes to evaluate.py and existing callers"

metrics:
  duration: "4 min"
  completed: "2026-01-18"
---

# Phase 03 Plan 02: Weighted Scoring System Summary

**Converted boolean tier filter to weighted scoring with ScoringResult dataclass returning score + reasons for each job posting.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-18
- **Completed:** 2026-01-18
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- ScoringResult dataclass with score, qualified, reasons, threshold fields
- score_job() function implementing full weighted scoring logic
- Backward-compatible description_matches() wrapper (87 lines reduced to 2)
- Scoring reasons explain every qualification decision

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ScoringResult dataclass** - `95bfa70` (feat)
2. **Task 2: Implement score_job() function** - `be5faf4` (feat)
3. **Task 3: Update description_matches() as wrapper** - `63bdf55` (refactor)

## Files Created/Modified

- `scraper.py` - Added ScoringResult dataclass, score_job() function, refactored description_matches()

## Verification Results

| Metric | Before | After | Status |
|--------|--------|-------|--------|
| Precision | 100.00% | 100.00% | PASS |
| Recall | 75.00% | 75.00% | PASS |
| F1 Score | 85.71% | 85.71% | PASS |

All 5 verification criteria passed:
1. evaluate.py shows 100% precision, 75% recall (no regression)
2. score_job() returns ScoringResult with score, qualified, reasons
3. description_matches() calls score_job() and returns qualified boolean
4. Weights come from config file (tier1=100, tier2=60, etc.)
5. Threshold is configurable (changing threshold changes qualified status)

## Scoring System Details

**Score Ranges:**
- `score = -100`: Hard disqualification (blocklist, exclusion match)
- `score = 0`: No positive signals or missing required context
- `score >= threshold (50)`: Qualified

**Tier Weights (from config):**
| Tier | Weight | Description |
|------|--------|-------------|
| 1 | 100 | Solar-specific tools (auto-qualify) |
| 2 | 60 | Strong technical signals + design role |
| 3 | 40 | CAD + project type + design role |
| 4 | 80 | Explicit solar design job titles |
| 5 | 30 | CAD + design role (simpler) |
| 6 | 20 | Design role titles with solar context |

**Example Output:**
```
Score: 270.0, Qualified: True
Reasons:
  +0: Has solar/PV context (required)
  +100: Solar-specific design tools - auto-qualify (helioscope)
  +60: Strong technical signals requiring design role (permit set)
  +80: Explicit solar design job titles (solar designer)
  +30: CAD tool + design role (with solar context)
  +0: Has design role indicator
```

## Decisions Made

1. **ScoringResult as dataclass:** Type safety, clear field names, IDE support. Dataclass with `field(default_factory=list)` for mutable default.

2. **Score -100 for disqualifications:** Distinguishes actively excluded (-100) from neutral (0). Makes threshold logic cleaner.

3. **Comprehensive reasons tracking:** Every scoring decision logged. Enables debugging without re-running filter.

4. **Thin wrapper for backward compatibility:** description_matches() reduced to 2-line wrapper. Zero breaking changes to existing callers.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 03-03 (title signal detection). This plan provides:
- Numeric scores that can be analyzed for threshold tuning
- Reasons list that can identify which tiers are/aren't matching
- Architecture that supports adding new scoring tiers

The 4 false negatives (tier4 title signals, tier5 CAD design roles) can now be debugged by examining their score_job() reasons to understand why they're not reaching threshold.

Potential blockers: None identified.

---
*Phase: 03-architecture-refactoring*
*Completed: 2026-01-18*
