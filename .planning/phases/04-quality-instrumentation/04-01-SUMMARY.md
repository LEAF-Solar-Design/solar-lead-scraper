---
phase: 04-quality-instrumentation
plan: 01
subsystem: statistics
tags: [statistics, logging, dataclass, counter]

dependency-graph:
  requires: [03-03]
  provides: [FilterStats, print_filter_stats, stats collection]
  affects: [04-02]

tech-stack:
  added: []
  patterns: [dataclass with Counter aggregation, statistics collection during iteration]

key-files:
  created: []
  modified: [scraper.py]

decisions:
  - id: STATS-01
    decision: "Use Counter from collections for aggregation"
    reason: "Built-in, efficient, provides most_common() for top N"
  - id: STATS-02
    decision: "Extract tier from reasons string parsing"
    reason: "ScoringResult already contains tier info in reason text"
  - id: STATS-03
    decision: "Categorize rejections to config section names"
    reason: "Enables correlation between stats and config tuning"

metrics:
  duration: 3 min
  completed: 2026-01-18
---

# Phase 04 Plan 01: Filter Statistics Summary

FilterStats dataclass tracks leads processed/qualified/rejected with Counter aggregation for rejection categories and qualification tiers.

## What Was Built

### FilterStats Dataclass (scraper.py)
- `total_processed`, `total_qualified`, `total_rejected` counters
- `rejection_categories: Counter` maps reason -> count
- `qualification_tiers: Counter` maps tier -> count
- `company_blocked` separate counter for blocklist rejections
- `add_qualified(tier)` and `add_rejected(category, is_blocked)` methods
- `pass_rate` property calculates percentage

### Statistics Collection (scraper.py)
- `categorize_rejection(result)` maps reasons to config section names
- `extract_tier_from_reasons(reasons)` parses tier from scoring reasons
- `scrape_solar_jobs()` now returns `tuple[pd.DataFrame, FilterStats]`
- Stats collected during filtering loop (replaced lambda filter)

### Output Display (scraper.py)
- `print_filter_stats(stats)` displays human-readable statistics
- Shows: total processed, pass rate, top 5 rejection reasons, tier distribution
- `main()` wires stats display after each run

## Verification Results

### Must-Haves Verified
- [x] FilterStats dataclass with add_qualified(), add_rejected(), pass_rate
- [x] scrape_solar_jobs() returns (DataFrame, FilterStats) tuple
- [x] Stats collection in filtering loop
- [x] Rejection categorization to config section names
- [x] print_filter_stats() displays formatted output
- [x] main() calls print_filter_stats() after scraping

### Regression Test
```
Precision: 100.00%
Recall:    75.00%
F1 Score:  85.71%
```
No regressions from Phase 3 baseline.

### Example Output
```
==================================================
FILTER STATISTICS
==================================================
Total processed:  4
Qualified:        2 (50.0%)
Rejected:         2 (50.0%)

Company blocklist: 1

Top rejection reasons:
     1 | no_solar_context
     1 | company_blocklist

Qualification by tier:
  tier1: 1
  tier2: 1
==================================================
```

## Commits

| Commit | Description |
|--------|-------------|
| 5919165 | feat(04-01): add FilterStats dataclass for filter statistics |
| 23d5cc8 | feat(04-01): collect stats in scrape_solar_jobs during filtering |
| c46af01 | feat(04-01): add print_filter_stats and wire to main |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added extract_tier_from_reasons helper**
- **Found during:** Task 2
- **Issue:** Plan showed tier extraction inline in loop; extracted to reusable function
- **Fix:** Created `extract_tier_from_reasons(reasons)` function
- **Files modified:** scraper.py
- **Commit:** 23d5cc8

## QUAL-01 Requirement

**QUAL-01: Each run logs filter statistics**

Status: SATISFIED

Evidence:
- FilterStats collects statistics during filtering
- print_filter_stats() displays at end of each run
- main() wires the display automatically
- User sees: total processed, pass rate, rejection reasons, tier distribution

## Next Phase Readiness

Ready for 04-02:
- Statistics infrastructure in place
- Can extend FilterStats for additional metrics
- print_filter_stats() can be enhanced with more detail
