---
phase: 02-data-driven-rules
plan: 01
subsystem: filter
tags: [company-blocklist, aerospace, semiconductor, false-positives]

dependency_graph:
  requires: [01-01, 01-02]
  provides: [company-blocklist-filter, company-aware-evaluation]
  affects: [02-02, 02-03]

tech_stack:
  added: []
  patterns: [company-level-filtering, blocklist-matching]

key_files:
  created: []
  modified:
    - scraper.py
    - evaluate.py
    - data/golden/golden-test-set.json

decisions:
  - Company blocklist check runs before description analysis
  - Blocklist uses substring matching for flexible company name variants

metrics:
  duration: 3 min
  completed: 2026-01-18
---

# Phase 2 Plan 1: Company Blocklist Summary

Company-level blocklist filtering for aerospace/defense and semiconductor false positives.

## What Was Done

Added COMPANY_BLOCKLIST constant with 28 aerospace/defense and semiconductor companies that frequently post jobs mentioning "solar" (spacecraft solar panels) or "CAD" (chip design) that are false positives for our solar design lead filter.

### Task 1: Add company blocklist and update function signature (49cfee9)

- Added `COMPANY_BLOCKLIST` set constant with 28 companies:
  - Aerospace/Defense: Boeing, Northrop Grumman, Lockheed Martin, Raytheon, SpaceX, Blue Origin, General Dynamics, BAE Systems, L3Harris, Leidos, Huntington Ingalls, RTX, Sierra Nevada Corporation
  - Semiconductor: Intel, Nvidia, AMD, Qualcomm, Broadcom, Texas Instruments, Micron, Applied Materials, Lam Research, KLA, ASML, Marvell, Microchip
- Updated `description_matches()` to accept optional `company_name` parameter
- Added company blocklist check at the START of function (before description analysis)
- Updated `scrape_solar_jobs()` call site to pass company name via lambda

### Task 2: Update evaluate.py to pass company name (f4a183a)

- Updated `evaluate()` function to pass `item.get("company")` to `description_matches()`
- Backward compatible: items without company field still work correctly
- Golden test set maintains baseline metrics

### Task 3: Add regression test items for blocked companies (dffd2cb)

- Added 2 new test cases to golden test set:
  - `golden_neg_blocked_company_01`: Boeing aerospace test case
  - `golden_neg_blocked_company_02`: Intel semiconductor test case
- Both correctly rejected by company blocklist
- Golden set expanded from 33 to 35 items

## Metrics After Changes

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Precision | 100% | 100% | No change |
| Recall | 75% | 75% | No change |
| F1 Score | 85.71% | 85.71% | No change |
| True Negatives | 17 | 19 | +2 (blocked companies) |
| Total Items | 33 | 35 | +2 |

## Key Design Decisions

1. **Blocklist check runs first**: Company blocklist check happens before any description analysis. This is more efficient (early exit) and ensures blocked companies are filtered regardless of description content.

2. **Substring matching**: Using `blocked in company_lower` allows flexible matching of company name variants (e.g., "Boeing Company", "Boeing Inc", "The Boeing Company" all match "boeing").

3. **Backward compatible**: `company_name` parameter defaults to `None`, so existing code without company information continues to work.

## Files Modified

| File | Changes |
|------|---------|
| `scraper.py` | +25 lines (COMPANY_BLOCKLIST constant, function signature update, blocklist check logic, call site update) |
| `evaluate.py` | +1 line (pass company to description_matches) |
| `data/golden/golden-test-set.json` | +16 lines (2 new blocked company test cases) |

## Verification Results

All verification checks passed:
- 28 companies in blocklist (exceeds 26+ requirement)
- Golden test: 100% precision, 75% recall (no regressions)
- Boeing correctly rejected
- SunPower correctly accepted

## Deviations from Plan

None - plan executed exactly as written.

## Next Steps

- 02-02: Title signal enhancement (address 4 false negatives in tier4/tier5)
- 02-03: Scoring system implementation
