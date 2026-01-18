# Requirements: Solar Lead Scraper

**Defined:** 2026-01-18
**Core Value:** Surface high-quality leads by finding companies actively hiring for solar design roles that would use solar design automation software.

## v1 Requirements

Requirements for improving lead qualification precision from ~3% to >20%.

### Metrics & Baseline

- [x] **METR-01**: System tracks precision (qualified / total passed) per run
- [x] **METR-02**: System tracks recall (qualified found / qualified in source) via golden test set
- [x] **METR-03**: Labeled data files can be loaded for evaluation
- [x] **METR-04**: Evaluation script compares filter output against labeled data

### Data-Driven Rules

- [ ] **RULE-01**: Company blocklist excludes known false positive companies (Boeing, Northrop, SpaceX, etc.)
- [ ] **RULE-02**: Missing role exclusions added (stringer, roofer, foreman, interconnection engineer)
- [ ] **RULE-03**: EDA tool exclusions added (Cadence, Synopsys for chip design false positives)
- [ ] **RULE-04**: Filter terms extracted from analysis of labeled rejected leads

### Architecture Refactoring

- [ ] **ARCH-01**: Filter configuration externalized to JSON/YAML (not hardcoded in scraper.py)
- [ ] **ARCH-02**: Tiered boolean filter converted to weighted scoring system
- [ ] **ARCH-03**: Company classification separated from role classification
- [ ] **ARCH-04**: Filter function returns score + reasons, not just boolean

### Output Quality

- [ ] **QUAL-01**: Each run logs filter statistics (passed/rejected per tier/rule)
- [ ] **QUAL-02**: Rejected leads can be exported for labeling exercises
- [ ] **QUAL-03**: Qualified leads include confidence score

## v2 Requirements

Deferred until 50+ qualified examples available.

### Machine Learning

- **ML-01**: TF-IDF vectorizer trained on labeled descriptions
- **ML-02**: Classifier (Naive Bayes or LogisticRegression) with class_weight='balanced'
- **ML-03**: ML score combined with rule-based score for final decision
- **ML-04**: Model retrained when new labeled data added

### Advanced Features

- **ADV-01**: Company name lookup against known solar company database
- **ADV-02**: Title-based pre-filter before description analysis
- **ADV-03**: Historical lead deduplication across runs

## Out of Scope

| Feature | Reason |
|---------|--------|
| LLM-based classification | Cost, latency, overkill for current data volume |
| Deep learning models | Not enough training data (<50 positives) |
| Real-time scraping | Batch runs sufficient for sales use case |
| CRM integration | CSV export is the interface |
| Web UI | CLI tool is sufficient |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| METR-01 | Phase 1 | Complete |
| METR-02 | Phase 1 | Complete |
| METR-03 | Phase 1 | Complete |
| METR-04 | Phase 1 | Complete |
| RULE-01 | Phase 2 | Pending |
| RULE-02 | Phase 2 | Pending |
| RULE-03 | Phase 2 | Pending |
| RULE-04 | Phase 2 | Pending |
| ARCH-01 | Phase 3 | Pending |
| ARCH-02 | Phase 3 | Pending |
| ARCH-03 | Phase 3 | Pending |
| ARCH-04 | Phase 3 | Pending |
| QUAL-01 | Phase 4 | Pending |
| QUAL-02 | Phase 4 | Pending |
| QUAL-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-01-18*
*Last updated: 2026-01-18 after Phase 1 completion*
