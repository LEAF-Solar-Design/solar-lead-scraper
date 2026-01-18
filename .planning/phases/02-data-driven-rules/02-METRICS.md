# Phase 2: Data-Driven Rules - Metrics

**Measured:** 2026-01-18
**Golden Test Set:** data/golden/golden-test-set.json

## Phase 2 Changes Summary

### Rules Added

1. **Company Blocklist** (02-01)
   - 26+ aerospace/defense companies (Boeing, Northrop Grumman, SpaceX, etc.)
   - 13+ semiconductor companies (Intel, Nvidia, AMD, etc.)
   - Company check runs before description analysis

2. **Installer Role Exclusions** (02-02)
   - Added: stringer, roofer, foreman, crew lead, panel installer

3. **Utility Engineering Exclusions** (02-02)
   - Added: interconnection engineer, grid engineer, protection engineer, metering engineer

4. **EDA Tool Exclusions** (02-02)
   - Added: Cadence, Synopsys, Mentor Graphics + 18 specific tool names
   - Separated from semiconductor terms as distinct exclusion block

## Metrics Comparison

### Before Phase 2 (Baseline from Phase 1)

| Metric | Value |
|--------|-------|
| Precision | 100.00% |
| Recall | 75.00% |
| F1 Score | 85.71% |
| Test Set Size | 33 items |

### After Phase 2

| Metric | Value |
|--------|-------|
| Precision | 100.00% |
| Recall | 75.00% |
| F1 Score | 85.71% |
| Test Set Size | 41 items |

### Change Analysis

**Precision:** Maintained at 100%. All new exclusion rules are working correctly - no false positives introduced.

**Recall:** Maintained at 75%. The Phase 2 changes focused on reducing false positives (adding exclusions), not improving recall. The 4 false negatives from Phase 1 baseline remain:
- golden_pos_tier2_02: CAD Designer at SolarCity Design Services
- golden_pos_tier4_01: Solar Designer at Kimley-Horn
- golden_pos_tier4_02: PV Design Engineer at Shoals Technologies
- golden_pos_tier5_01: AutoCAD Designer at solar company

**Test Coverage:** Expanded from 33 to 41 items (+8 items = +24% coverage increase).

## Test Coverage by Category

| Category | Count | All Pass? |
|----------|-------|-----------|
| tier1_tool_match | 3 | Yes |
| tier2_strong_signals | 3 | 2/3 (1 FN) |
| tier3_cad_with_context | 2 | Yes |
| tier4_title_signals | 2 | 0/2 (2 FN) |
| tier5_cad_design_role | 2 | 1/2 (1 FN) |
| tier6_solar_design_titles | 4 | Yes |
| false_positive_tennis | 1 | Yes |
| false_positive_aerospace | 3 | Yes |
| false_positive_semiconductor | 2 | Yes |
| false_positive_installer | 5 | Yes |
| false_positive_sales | 2 | Yes |
| false_positive_management | 2 | Yes |
| false_positive_other_engineering | 2 | Yes |
| false_positive_utility | 4 | Yes |
| false_positive_blocked_company | 2 | Yes |
| false_positive_eda_tools | 2 | Yes |

**Summary:** 16 positive items, 25 negative items. All 25 negatives correctly rejected (100%). 12 of 16 positives correctly identified (75%).

## Confusion Matrix

|                | Predicted Reject | Predicted Qualify |
|----------------|-----------------|-------------------|
| Actual Reject  | 25 (TN)         | 0 (FP)            |
| Actual Qualify | 4 (FN)          | 12 (TP)           |

## Requirements Satisfied

- [x] RULE-01: Company blocklist excludes known false positive companies (Boeing, Intel, etc.)
- [x] RULE-02: Missing role exclusions added (stringer, roofer, foreman, interconnection engineer)
- [x] RULE-03: EDA tool exclusions added (Cadence, Synopsys for chip design)
- [x] RULE-04: Filter terms extracted from analysis (documented in 02-RESEARCH.md)

## Phase 2 Impact Assessment

**Positive outcomes:**
- Defense against aerospace/semiconductor false positives via company blocklist
- Defense against EDA/chip design false positives via tool detection
- Defense against installer labor roles (stringer, foreman)
- Defense against utility engineering roles (interconnection, grid)
- All new exclusions verified with test cases

**No regressions:**
- Precision maintained at 100%
- Recall maintained at 75%
- No previously-passing tests now failing

**Outstanding issues (for Phase 3+):**
- 4 false negatives in tier2/tier4/tier5 need title signal improvements
- Consider expanding title detection area beyond first 200 chars
- May need pattern refinement for "Solar Designer" in varied title formats

## Notes

- Golden test set expanded from 33 to 41 items (+8 new exclusion test cases)
- Phase 2 focused on reducing false positives, not improving recall
- Recall improvement deferred to future phase focusing on title signal detection
- Company blocklist approach validated: substring matching handles company name variants

---
*Metrics measured: 2026-01-18*
