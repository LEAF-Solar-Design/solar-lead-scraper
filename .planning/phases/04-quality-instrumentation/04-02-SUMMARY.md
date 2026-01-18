---
phase: 04-quality-instrumentation
plan: 02
subsystem: data-export
tags: [rejected-leads, confidence-score, labeling-workflow, continuous-improvement]

dependency_graph:
  requires: [04-01]
  provides: [rejected-lead-export, confidence-scores]
  affects: [labeling-workflow, lead-prioritization]

tech_stack:
  added: []
  patterns:
    - labeled-data-schema-reuse
    - configurable-export-limits
    - confidence-score-capping

file_changes:
  created: []
  modified:
    - scraper.py

decisions:
  - id: "confidence-cap-100"
    choice: "Cap confidence at 100 (score directly maps to percentage)"
    rationale: "Score 50=threshold (50%), score 100+=100%. Clean mental model."
  - id: "rejected-leads-schema"
    choice: "Match golden-test-set.json schema for rejected exports"
    rationale: "Enables direct import into labeling workflow after review."
  - id: "max-export-default"
    choice: "Default max_export=100 to avoid huge files"
    rationale: "Balance between having enough data and manageable file size."

metrics:
  duration: "3 min"
  completed: "2026-01-18"
---

# Phase 4 Plan 02: Rejected Lead Export and Confidence Scores Summary

**One-liner:** Rejected leads exported as JSON for labeling review; qualified leads include confidence_score column.

## What Was Built

### export_rejected_leads Function

New function that exports rejected leads in the same schema as golden-test-set.json:

```python
def export_rejected_leads(
    rejected_leads: list[dict],
    output_dir: Path,
    run_id: str,
    max_export: int = 100
) -> Path
```

**Output format:**
```json
{
  "metadata": {
    "created": "2026-01-18T...",
    "purpose": "labeling_review",
    "run_id": "20260118_123456",
    "count": 100,
    "total_rejected": 523,
    "notes": "Review and change label to true for any false negatives"
  },
  "items": [
    {
      "id": "rejected_001_TestCo",
      "description": "Job description text...",
      "label": false,
      "company": "TestCo",
      "title": "Designer",
      "notes": "Rejected: no_solar_context (score: 0)"
    }
  ]
}
```

### Rejected Lead Collection in scrape_solar_jobs

Updated return signature to include rejected leads and scoring results:

```python
def scrape_solar_jobs() -> tuple[pd.DataFrame, FilterStats, list[dict], dict]:
```

**Returns:**
1. DataFrame of qualified jobs
2. FilterStats with run statistics
3. list of rejected lead dicts for labeling export
4. dict mapping row indices to ScoringResult for confidence calculation

### Confidence Score in process_jobs

Updated process_jobs to calculate confidence scores:

```python
def process_jobs(df: pd.DataFrame, scoring_results: dict = None) -> pd.DataFrame
```

**Confidence calculation:**
- Score 50 (threshold) = 50% confidence
- Score 100+ = 100% confidence (capped)
- None if no scoring result available

### Updated main() Flow

1. Receive all four returns from scrape_solar_jobs()
2. Pass scoring_results to process_jobs()
3. Export rejected leads JSON before saving CSV
4. Save CSV with confidence_score column

## Commits

| Commit | Description | Files |
|--------|-------------|-------|
| eecab7d | Add export_rejected_leads function | scraper.py |
| 8c5fd76 | Collect rejected leads and scoring results | scraper.py |
| 33a6df7 | Add confidence_score and wire main | scraper.py |

## Verification Results

**Evaluation (unchanged from baseline):**
- Precision: 100%
- Recall: 75%
- F1: 85.71%

**Success criteria verified:**
- export_rejected_leads() function exists with correct signature
- Rejected leads JSON matches labeled data schema (id, description, label, company, title, notes)
- Rejected leads limited to configurable max (default 100)
- scrape_solar_jobs() returns tuple with rejected_leads list
- process_jobs() accepts scoring_results parameter
- CSV output includes confidence_score column
- Confidence ranges 0-100 (score capped at 100)
- main() exports rejected leads to output/rejected_leads_*.json

## Requirements Satisfied

- **QUAL-02:** Rejected leads can be exported for labeling
- **QUAL-03:** Qualified leads include confidence score

## Deviations from Plan

None - plan executed exactly as written.

## Files Modified

### scraper.py

**Lines added:** ~112

**New functions:**
- `export_rejected_leads()` - Export rejected leads for labeling review (53 lines)

**Modified functions:**
- `scrape_solar_jobs()` - Now collects rejected_leads and scoring_results, returns 4-tuple
- `process_jobs()` - Now accepts scoring_results, adds confidence_score column
- `main()` - Wired to handle all returns and export rejected leads

## Next Phase Readiness

Phase 4 complete. All QUAL requirements satisfied:

| Requirement | Status | Plan |
|-------------|--------|------|
| QUAL-01: Each run logs filter statistics | DONE | 04-01 |
| QUAL-02: Rejected leads can be exported for labeling | DONE | 04-02 |
| QUAL-03: Qualified leads include confidence score | DONE | 04-02 |

**Continuous improvement workflow now enabled:**
1. Run scraper -> produces solar_leads_*.csv and rejected_leads_*.json
2. Human reviews rejected_leads_*.json for false negatives
3. Update label to true for any misclassified leads
4. Import corrected file into labeled data for training/tuning
5. Repeat to improve recall over time

**Remaining work for future:**
- 4 false negatives in tier4/tier5 remain (title signal detection issue)
- Consider expanding title detection area beyond first 200 chars
- Monitor confidence scores to calibrate threshold
