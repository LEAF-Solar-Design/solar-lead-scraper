# Roadmap: Solar Lead Scraper

## Overview

Improve lead qualification precision from ~3% to >20% through a data-driven approach: first establish measurement infrastructure to track progress, then refine rules based on labeled data analysis, then refactor the filter architecture for maintainability and scoring, and finally add quality instrumentation for ongoing optimization.

## Phases

- [x] **Phase 1: Metrics Foundation** - Establish baseline measurements and evaluation infrastructure
- [x] **Phase 2: Data-Driven Rule Refinement** - Add exclusions and inclusions derived from labeled data
- [ ] **Phase 3: Architecture Refactoring** - Convert to scoring system with externalized config
- [ ] **Phase 4: Quality Instrumentation** - Add logging, confidence scores, and export tools

## Phase Details

### Phase 1: Metrics Foundation
**Goal**: Establish measurement infrastructure to track precision/recall before making filter changes
**Depends on**: Nothing (first phase)
**Requirements**: METR-01, METR-02, METR-03, METR-04
**Success Criteria** (what must be TRUE):
  1. Running evaluate.py against labeled JSON files produces precision/recall metrics
  2. Golden test set created with known good/bad examples
  3. Current filter baseline precision is documented (expected ~3%)
**Plans**: 2 plans (Wave 1: 01-01, Wave 2: 01-02)

Plans:
- [x] 01-01-PLAN.md - Create evaluation infrastructure (evaluate.py, data directories, scikit-learn)
- [x] 01-02-PLAN.md - Create golden test set and document baseline metrics

### Phase 2: Data-Driven Rule Refinement
**Goal**: Improve filter precision by adding rules derived from analysis of rejected/qualified leads
**Depends on**: Phase 1
**Requirements**: RULE-01, RULE-02, RULE-03, RULE-04
**Success Criteria** (what must be TRUE):
  1. Company blocklist blocks aerospace/semiconductor false positives
  2. New role exclusions block installer/field tech false positives
  3. Precision improves measurably (>5%) on golden test set
**Plans**: 3 plans (Wave 1: 02-01, 02-02 parallel; Wave 2: 02-03)

Plans:
- [x] 02-01-PLAN.md - Add company blocklist for aerospace/semiconductor companies (RULE-01)
- [x] 02-02-PLAN.md - Add missing role and EDA tool exclusions (RULE-02, RULE-03)
- [x] 02-03-PLAN.md - Validate rules and document Phase 2 metrics (RULE-04)

### Phase 3: Architecture Refactoring
**Goal**: Refactor filter from boolean tiers to weighted scoring with external configuration
**Depends on**: Phase 2
**Requirements**: ARCH-01, ARCH-02, ARCH-03, ARCH-04
**Success Criteria** (what must be TRUE):
  1. Filter configuration lives in JSON/YAML file, not hardcoded
  2. Filter returns numeric score, not boolean
  3. Company signals scored separately from role signals
  4. Threshold for "qualified" is configurable
**Plans**: 3 plans

Plans:
- [ ] 03-01: Extract filter terms to configuration file
- [ ] 03-02: Implement weighted scoring engine
- [ ] 03-03: Separate company and role classification

### Phase 4: Quality Instrumentation
**Goal**: Add observability to understand filter behavior and enable continuous improvement
**Depends on**: Phase 3
**Requirements**: QUAL-01, QUAL-02, QUAL-03
**Success Criteria** (what must be TRUE):
  1. Each run logs how many leads passed/rejected per rule
  2. Rejected leads can be exported for labeling review
  3. Qualified leads include confidence score in output
**Plans**: 2 plans

Plans:
- [ ] 04-01: Add per-rule statistics logging
- [ ] 04-02: Add rejected lead export and confidence scores

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Metrics Foundation | 2/2 | ✓ Complete | 2026-01-18 |
| 2. Data-Driven Rule Refinement | 3/3 | ✓ Complete | 2026-01-18 |
| 3. Architecture Refactoring | 0/3 | Not started | - |
| 4. Quality Instrumentation | 0/2 | Not started | - |

---
*Roadmap created: 2026-01-18*
*Last updated: 2026-01-18 after Phase 2 execution*
