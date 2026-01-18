# Phase 1: Baseline Metrics

**Measured:** 2026-01-18
**Golden Test Set:** data/golden/golden-test-set.json (33 items)

## Current Filter Performance

| Metric | Value |
|--------|-------|
| Precision | 100.00% |
| Recall | 75.00% |
| F1 Score | 85.71% |

## Confusion Matrix

|                | Predicted Positive | Predicted Negative |
|----------------|-------------------|-------------------|
| Actual Positive | 12 | 4 |
| Actual Negative | 0 | 17 |

## Analysis

### What's Working

The filter has **perfect precision** (100%) - every lead it approves is actually qualified:

- **Tier 1 (Solar-specific tools):** All 3 items correctly identified (Helioscope, Aurora Solar, PVsyst)
- **Tier 2 (Strong signals):** 2 of 3 items correctly identified (stringing diagrams, single line diagrams)
- **Tier 3 (CAD + solar project):** All 2 items correctly identified
- **Tier 6 (Design role titles):** All 4 items correctly identified (electrical drafter, CAD technician, BIM modeler, permit designer)

All exclusion rules are working correctly:
- Tennis/racquet false positives blocked (1/1)
- Aerospace/space context blocked (3/3)
- Semiconductor/chip design blocked (2/2)
- Installer/field technician blocked (3/3)
- Sales roles blocked (2/2)
- Management roles blocked (2/2)
- Other engineering (civil, structural) blocked (2/2)
- Utility/transmission roles blocked (2/2)

### False Positives (Predicted True, Actually False)

**None.** The filter has perfect precision - it correctly rejects all 17 negative examples.

### False Negatives (Predicted False, Actually True)

The filter missed 4 qualified leads (25% of positives):

1. **golden_pos_tier2_02** - CAD Designer creating permit packages and plan sets
   - Category: tier2_strong_signals
   - Issue: "SolarCity Design Services" not triggering despite having wiring schedules, conduit schedules
   - Pattern: Exclusion rule may be blocking (need to investigate)

2. **golden_pos_tier4_01** - Solar Designer at Kimley-Horn doing PV system design
   - Category: tier4_title_signals
   - Issue: "Solar Designer" in title but not in first 200 chars of description
   - Pattern: Title signal check too narrow

3. **golden_pos_tier4_02** - PV Design Engineer at Shoals Technologies
   - Category: tier4_title_signals
   - Issue: "PV Design Engineer" in title but not detected
   - Pattern: Same as above - title signal check issue

4. **golden_pos_tier5_01** - AutoCAD Designer at solar company working on array layouts
   - Category: tier5_cad_design_role
   - Issue: Has CAD + design role + solar mentioned but not qualifying
   - Pattern: May be hitting an exclusion rule or missing a design role indicator

## Baseline for Comparison

All future filter changes should be measured against this baseline:

| Metric | Baseline | Goal |
|--------|----------|------|
| Precision | 100.00% | Maintain (>90%) |
| Recall | 75.00% | Improve (>85%) |
| F1 Score | 85.71% | Improve (>90%) |

**Primary focus for improvement:** Increase recall without sacrificing precision. The filter is conservative - it's missing good leads rather than accepting bad ones.

## Comparison with Production Data

**Expected vs Actual:**
- PROJECT.md noted ~3% precision based on production data (16 qualified vs 514 rejected)
- Golden test set shows 100% precision

**Why the difference:**
1. Golden test set is curated with clear-cut examples designed to test specific tiers
2. Production data has more ambiguous edge cases
3. Golden set negative examples are from documented false positive categories
4. Production data may have different distribution of job types

**Implication:** Golden test set measures filter logic correctness, not production distribution. Both metrics are valuable:
- Golden test: "Is the filter logic working as designed?"
- Production data: "Is the filter effective on real-world data?"

## Notes

- Golden set size: 33 items (16 positive, 17 negative)
- Sample size limitation: With only 33 items, metrics have some variance
- Criteria version: 1.0
- All negative examples correctly rejected (17/17)
- 4 positive examples missed (4/16) - indicates room for recall improvement

## Next Steps

Based on this baseline, Phase 2 should focus on:
1. Investigating why tier4 and tier5 positive examples are being missed
2. Expanding title signal detection area
3. Adding more nuanced pattern matching for qualified roles
4. Consider adding more golden test items as edge cases are discovered

---
*Baseline measured: 2026-01-18*
