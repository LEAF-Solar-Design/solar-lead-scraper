---
phase: 02-data-driven-rules
plan: 02
subsystem: filtering
tags: [exclusions, false-positives, installer, utility, eda-tools, precision]

# Dependency graph
requires:
  - phase: 02-01
    provides: Company blocklist and updated description_matches() signature
  - phase: 01-02
    provides: Golden test set for regression testing
provides:
  - Installer false positive exclusions (stringer, roofer, foreman, crew lead, panel installer)
  - Utility/grid engineering exclusions (interconnection, grid, protection, metering engineers)
  - EDA tool exclusions for semiconductor CAD (22 tools/vendors)
affects: [02-03, phase-3]

# Tech tracking
tech-stack:
  added: []
  patterns: [targeted-exclusion-terms, eda-tool-blocklist]

key-files:
  created: []
  modified:
    - scraper.py

key-decisions:
  - "Add 5 installer terms to catch field crew false positives"
  - "Add 4 utility engineering terms to exclude grid-focused roles"
  - "Create new eda_tools exclusion block with 22 EDA vendors and tools"

patterns-established:
  - "Phase 2 comment markers in exclusion lists for traceability"
  - "EDA tool exclusion as separate block from semiconductor terms"

# Metrics
duration: 4min
completed: 2026-01-18
---

# Phase 02 Plan 02: Add Missing Exclusion Terms Summary

**Expanded exclusion lists with 5 installer terms, 4 utility engineering terms, and 22 EDA tools to reduce false positives while maintaining 100% precision and 75% recall**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-18
- **Completed:** 2026-01-18
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- Added 5 installer false positive exclusions: stringer, roofer, foreman, crew lead, panel installer
- Added 4 utility/grid engineering exclusions: interconnection engineer, grid engineer, protection engineer, metering engineer
- Created new eda_tools exclusion block with 22 EDA vendors and specific tools
- Validated all new exclusions work correctly
- Confirmed no regressions on golden test set (100% precision, 75% recall maintained)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add missing installer/field role exclusions** - `5ffa0b2` (feat)
2. **Task 2: Add missing engineering role exclusions** - `1f078a3` (feat)
3. **Task 3: Add EDA tool exclusions for semiconductor CAD** - `f99b19c` (feat)

## Files Modified

- `scraper.py` - Updated installer_terms, other_eng_terms, and added new eda_tools block

### Changes Detail

**installer_terms additions (line 137-142):**
```python
# Added in Phase 2 - installer false positives
'stringer',           # Tennis/racquet AND solar stringing labor
'roofer',             # Roofing labor, not design
'foreman',            # Construction supervision
'crew lead',          # Installation crew supervision
'panel installer',    # Explicit installer role
```

**other_eng_terms additions (line 178-182):**
```python
# Added in Phase 2 - utility/grid engineering false positives
'interconnection engineer',  # Utility interface role
'grid engineer',             # Grid/utility focus
'protection engineer',       # Utility protection systems
'metering engineer',         # Utility metering
```

**New eda_tools block (lines 130-140):**
```python
# Exclude EDA/chip design tools (semiconductor CAD, not solar CAD)
# Added in Phase 2 - these are chip design tools, not solar design tools
eda_tools = [
    'cadence', 'synopsys', 'mentor graphics', 'siemens eda',
    'virtuoso', 'spectre', 'innovus', 'genus', 'conformal',
    'calibre', 'questa', 'modelsim', 'vcs', 'verdi',
    'primetime', 'icc2', 'design compiler', 'dc shell',
    'spyglass', 'formality', 'encounter', 'ic compiler'
]
if any(tool in desc_lower for tool in eda_tools):
    return False
```

## Decisions Made

1. **Add stringer to installer_terms** - Catches both tennis racquet stringers and solar panel stringers (installation labor)
2. **Add foreman and crew lead** - Construction supervision roles, not design roles
3. **Add interconnection/grid/protection/metering engineers** - Utility-focused roles that mention solar but focus on grid interface
4. **Separate EDA tools from semiconductor_terms** - EDA tools are specific tool names (Cadence, Synopsys), while semiconductor_terms are domain keywords (ASIC, FPGA)
5. **22 EDA tools/vendors included** - Comprehensive coverage of major EDA ecosystem

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Note:** Plan 02-01 (Company Blocklist) was executed prior to this plan but no SUMMARY.md was created. The COMPANY_BLOCKLIST and updated description_matches() signature are already in scraper.py, indicating 02-01 was completed but not formally documented. This plan (02-02) built upon that work successfully.

## User Setup Required

None - no external service configuration required.

## Verification Results

All verification tests passed:

| Test | Result |
|------|--------|
| stringer excluded | True |
| roofer excluded | True |
| foreman excluded | True |
| interconnection engineer excluded | True |
| cadence excluded | True |
| synopsys excluded | True |
| virtuoso excluded | True |
| primetime excluded | True |
| Golden test precision | 100% |
| Golden test recall | 75% |
| Helioscope designer accepted | True |
| AutoCAD drafter accepted | True |

## Next Phase Readiness

**Ready for Plan 02-03 (Recall Improvement):**
- Precision improvements complete (false positives addressed)
- Golden test baseline maintained (no regressions)
- Ready to focus on recall improvement (4 false negatives from baseline)

**Blockers:** None

**Concerns:**
- The 4 false negatives identified in baseline (tier4/tier5) are not addressed by this plan
- Plan 02-03 should focus on recall improvement patterns

---
*Phase: 02-data-driven-rules*
*Completed: 2026-01-18*
