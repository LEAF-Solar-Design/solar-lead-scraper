---
phase: "03"
plan: "01"
subsystem: "filtering"
tags: ["configuration", "json", "externalization", "architecture"]

dependency_graph:
  requires:
    - "02-data-driven-rules"
  provides:
    - "Externalized filter configuration"
    - "Runtime config loading"
    - "JSON-based term management"
  affects:
    - "03-02: confidence-levels"
    - "03-03: title-signal-detection"

tech_stack:
  added:
    - "json module (stdlib)"
  patterns:
    - "Lazy config loading with module-level caching"
    - "Pathlib for cross-platform paths"
    - "External JSON configuration"

key_files:
  created:
    - "config/filter-config.json"
  modified:
    - "scraper.py"

decisions:
  - decision: "Use JSON for configuration over YAML"
    rationale: "Zero dependencies, sufficient for term lists, universal support"
  - decision: "Lazy loading with module-level cache"
    rationale: "Load config once per process, avoid repeated file I/O"
  - decision: "Keep COMPANY_BLOCKLIST constant as documentation"
    rationale: "Helps developers understand blocklist purpose, config is authoritative"

metrics:
  duration: "4 min"
  completed: "2026-01-18"
---

# Phase 03 Plan 01: Externalize Filter Configuration Summary

**One-liner:** Extracted all hardcoded filter terms from scraper.py to config/filter-config.json with lazy-loading runtime configuration.

## What Changed

### Created Files

**config/filter-config.json** (94 lines)
- All company blocklist entries (28 companies)
- All exclusion patterns organized by category (8 categories)
- All positive signal tiers with weights (6 tiers)
- Design role indicators list
- Version field and threshold for future scoring

### Modified Files

**scraper.py**
- Added `json` import
- Added `load_filter_config()` function for JSON loading
- Added `get_config()` with lazy loading and module-level caching
- Refactored `description_matches()` to read all terms from config
- Reduced function from ~150 lines of hardcoded lists to ~90 lines of config lookups
- Maintained backward compatibility (same function signature)

## Verification Results

| Metric | Before | After | Status |
|--------|--------|-------|--------|
| Precision | 100.00% | 100.00% | PASS |
| Recall | 75.00% | 75.00% | PASS |
| F1 Score | 85.71% | 85.71% | PASS |
| True Positives | 12 | 12 | PASS |
| False Positives | 0 | 0 | PASS |
| False Negatives | 4 | 4 | PASS |
| True Negatives | 25 | 25 | PASS |

ARCH-01 verified: Added and removed test term from JSON config - filter behavior changed without any Python code modifications.

## Decisions Made

1. **JSON over YAML:** No new dependencies required. JSON is sufficient for term lists and widely supported.

2. **Lazy loading pattern:** Config loaded once on first use, cached at module level. Avoids file I/O on every call while keeping startup fast.

3. **Keep original constant:** `COMPANY_BLOCKLIST` constant kept in code as documentation. Config file is authoritative source of truth.

4. **Flat file structure:** Single `config/filter-config.json` file rather than multiple files. Project is small, single file is easier to manage.

## Deviations from Plan

None - plan executed exactly as written.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create JSON configuration file | ac6ac9e | config/filter-config.json |
| 2 | Add config loading to scraper.py | d234ed5 | scraper.py |
| 3 | Verify config changes work without code changes | N/A (verification only) | - |

## Next Phase Readiness

Ready for Plan 03-02 (confidence levels). This plan provides:
- Externalized configuration that can be extended with weights
- `get_config()` function for accessing configuration
- Weight fields already present in positive_signals (tier1_tools: 100, tier2_strong: 60, etc.)

Potential blockers: None identified.
