# Pitfalls Research: Job Classification / Lead Qualification

**Domain:** Job listing classification for B2B lead qualification
**Researched:** 2026-01-18
**Confidence:** MEDIUM (domain expertise + codebase analysis; no WebSearch verification)

## Executive Summary

Job classification and lead qualification systems fail in predictable ways. With your ~3% precision rate (16/514), the current system exhibits classic symptoms of several pitfalls. This document catalogs common mistakes, their warning signs, and prevention strategies specific to improving your solar lead scraper.

---

## Critical Pitfalls

Mistakes that cause fundamental system failure or require architectural rewrites.

### Pitfall 1: Blacklist/Exclusion Whack-a-Mole

**What goes wrong:**
Teams add exclusion terms reactively as false positives appear. Each new exclusion potentially creates false negatives. The exclusion list grows unbounded while precision stays flat because new false positive categories keep appearing.

**Your current state:**
The `description_matches()` function has 8 separate exclusion blocks (tennis, space, semiconductor, installer, sales, management, other_eng) totaling 60+ exclusion terms. Each commit shows new terms being added.

**Why it happens:**
- Exclusions are easy to add (single line change)
- No systematic analysis of why false positives share characteristics
- No measurement of false negatives introduced

**Consequences:**
- Exclusion lists become unmaintainable
- False negatives silently increase (qualified leads excluded)
- Diminishing returns on each new exclusion

**Prevention:**
1. Track both precision AND recall when adding exclusions
2. Group exclusions by root cause, not symptom
3. Use scoring/weighting instead of hard exclusions
4. Require evidence of pattern (3+ examples) before adding exclusion

**Detection (Warning Signs):**
- Exclusion list grows faster than precision improves
- New false positive categories keep appearing
- No one knows what false negatives exist

**Phase to address:** Phase 1 - Requires measurement infrastructure before any filter changes

---

### Pitfall 2: Word Matching Without Semantic Context

**What goes wrong:**
Simple string matching catches unintended uses of terms. "Solar" matches tennis racquet stringing, aerospace solar panels, and solar energy equally. "PV" matches protective vest, Palo Verde nuclear plant, and photovoltaic.

**Your current state:**
All filtering uses substring matching (`term in desc_lower`). The tennis exclusion was added after "stringing" matched racquet stringing. This is reactive patching.

**Why it happens:**
- Substring matching is simple and fast
- Works for obvious cases, fails for edge cases
- Ambiguous terms are common in job descriptions

**Consequences:**
- False positives from homonyms/context mismatches
- Exclusion rules needed for each ambiguous term
- Cannot distinguish "solar company" from "company that mentions solar"

**Prevention:**
1. Use phrase-level matching ("solar energy" vs "solar" alone)
2. Require co-occurrence patterns (solar + design + CAD together)
3. Consider embeddings or ML for semantic similarity
4. Weight matches by proximity to role-relevant terms

**Detection (Warning Signs):**
- Same root term appears in both inclusions and exclusions
- Exclusions target industries rather than job characteristics
- "Stringing" matches tennis, "lineman" matches utility, "solar" matches aerospace

**Phase to address:** Phase 2 - After measurement, before ML approaches

---

### Pitfall 3: Training on Imbalanced Data Without Adjustment

**What goes wrong:**
With 3% positive rate, a classifier that predicts "not qualified" 100% of the time achieves 97% accuracy. Standard accuracy metrics are meaningless. Models learn to predict the majority class.

**Your current state:**
16 qualified vs 514 total = 3.1% positive rate. Any ML approach will face severe class imbalance.

**Why it happens:**
- Default metrics reward majority class prediction
- Training algorithms optimize for overall accuracy
- Positive examples too few to learn patterns

**Consequences:**
- Model appears accurate but finds no leads
- Precision/recall tradeoff invisible
- Tuning makes no measurable difference

**Prevention:**
1. Use precision/recall/F1 instead of accuracy
2. Apply class weights (e.g., 30:1 for positives)
3. Use SMOTE or similar oversampling for training
4. Set threshold based on business requirement (high recall vs high precision)
5. Measure precision@k for ranked results

**Detection (Warning Signs):**
- Model achieves 95%+ accuracy but business hates results
- Changing threshold has no effect
- Model predicts majority class for almost all inputs

**Phase to address:** Phase 1 - Must establish correct metrics before any optimization

---

### Pitfall 4: No Ground Truth / Subjective Labeling

**What goes wrong:**
Without clear labeling criteria, the same job gets labeled differently by different people or at different times. Filter improvements cannot be measured. A/B tests are inconclusive.

**Your current state:**
Labeled data exists (rejected/qualified JSON files) but labeling criteria not documented. Unclear what distinguishes a "qualified" lead.

**Why it happens:**
- "I know it when I see it" approach
- Edge cases not discussed upfront
- Multiple implicit criteria (company type + job type + seniority)

**Consequences:**
- Cannot measure true precision/recall
- Filter changes appear random in effect
- Cannot compare approaches objectively

**Prevention:**
1. Document explicit qualification criteria BEFORE labeling
2. Label edge cases collaboratively and document decisions
3. Use inter-rater reliability metrics
4. Create "gold standard" test set with agreed labels

**Detection (Warning Signs):**
- Disagreement on whether specific lead is qualified
- Labeling criteria changed mid-labeling
- No documented rationale for labels

**Phase to address:** Phase 1 - Foundation for all subsequent work

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, or suboptimal results.

### Pitfall 5: Optimizing Search Terms Instead of Filters

**What goes wrong:**
Teams iterate on search terms trying to find "better" queries, when the real issue is post-retrieval filtering. Search term changes have unpredictable effects on result composition.

**Your current state:**
37 search terms, frequently modified (see commit history). Wide net approach intentional, but search term changes may be mixing signals.

**Why it happens:**
- Search terms are visible, filters are hidden
- Easy to blame search for bad results
- Adding search terms feels productive

**Consequences:**
- Inconsistent result composition across runs
- Hard to measure filter effectiveness
- Search term bloat with diminishing returns

**Prevention:**
1. Fix search terms, iterate only on filters
2. Measure filter performance independently of search
3. A/B test filter changes, not search term changes
4. Track result composition (how many from each search term)

**Detection (Warning Signs):**
- Search terms modified and filter modified in same commit
- Different runs have wildly different results
- Cannot explain why precision changed

**Phase to address:** Phase 2 - Stabilize search, focus on filter

---

### Pitfall 6: Tier/Priority System Without Score Aggregation

**What goes wrong:**
Tiered systems (Tier 1, Tier 2, ...) become complex IF-ELSE chains that are order-dependent and hard to reason about. Adding a new signal requires restructuring the entire flow.

**Your current state:**
6 tiers with early returns. Order matters. Cannot easily combine weak signals (e.g., "mentioned solar + mentioned CAD + title looks right" should be stronger than any one signal).

**Why it happens:**
- Tiers are intuitive to design initially
- Binary include/exclude decisions are simple
- Scoring systems require more infrastructure

**Consequences:**
- Order-dependent bugs (tier 5 masks tier 6)
- Cannot tune signal strengths
- All-or-nothing decisions lose information

**Prevention:**
1. Convert to scoring: each signal adds/subtracts points
2. Final decision is threshold on score
3. Log scores for analysis (understand why rejected)
4. Tune weights based on labeled data

**Detection (Warning Signs):**
- Changing tier order changes results unpredictably
- Cannot explain why specific lead was rejected
- Similar-looking jobs get different outcomes

**Phase to address:** Phase 2 - Refactor filter architecture

---

### Pitfall 7: Company vs Job Role Confusion

**What goes wrong:**
Qualifying based on company characteristics (solar company) vs job characteristics (design role) requires different signals. Mixing them causes systematic errors.

**Your current state:**
Filter checks both (solar context at top, role exclusions throughout). But a CAD job at a solar company is qualified even if the specific role is unrelated to solar.

**Why it happens:**
- Both matter, but differently
- Company info often missing or ambiguous
- Easier to check job description than research company

**Consequences:**
- Qualified: CAD job at solar company doing HVAC design
- Rejected: Solar design job at diversified engineering firm
- False positives from solar company non-design roles
- False negatives from non-solar-branded companies

**Prevention:**
1. Separate company qualification from role qualification
2. Both must pass for lead to qualify
3. Use company name lookup/enrichment where possible
4. Different confidence levels for each dimension

**Detection (Warning Signs):**
- False positives share company type not role type
- False negatives are at diversified companies
- "Solar company" assumed from any solar mention

**Phase to address:** Phase 2 - Requires filter architecture change

---

### Pitfall 8: Hardcoded Terms in Code vs Configuration

**What goes wrong:**
Filter terms hardcoded in Python require code changes, deployments, and code review for any filter adjustment. Iteration is slow and risky.

**Your current state:**
All 60+ exclusion terms and 50+ inclusion terms are in `scraper.py`. Every filter change requires git commit.

**Why it happens:**
- Started simple, grew organically
- Configuration management is overhead upfront
- "Just one more term" accumulates

**Consequences:**
- Filter iteration requires developer
- Cannot A/B test configurations easily
- Version control noise (filter commits mixed with feature commits)

**Prevention:**
1. Extract filter terms to JSON/YAML configuration
2. Version config separately from code
3. Enable runtime config loading
4. Build admin interface for non-developers

**Detection (Warning Signs):**
- Most recent commits are filter term changes
- Non-developers cannot adjust filters
- Filter changes require full deployment

**Phase to address:** Phase 1 or Phase 2 - Infrastructure improvement

---

## Minor Pitfalls

Mistakes that cause annoyance but are recoverable.

### Pitfall 9: Case Sensitivity Bugs

**What goes wrong:**
Inconsistent casing causes terms to miss. "AutoCAD" vs "autocad" vs "AUTOCAD" all appear in job descriptions.

**Your current state:**
Good - using `.lower()` consistently. But watch for edge cases like "PV" (could be "pv", "PV", "Pv").

**Prevention:**
1. Always normalize case before matching
2. Test with real data variations
3. Consider regex with `re.IGNORECASE` for complex patterns

**Phase to address:** Ongoing - part of testing discipline

---

### Pitfall 10: Substring vs Word Boundary Matching

**What goes wrong:**
"cad" matches "facade", "cadence", "academy". Substring matching without word boundaries causes false matches.

**Your current state:**
Uses substring matching. The term 'cad ' (with trailing space) attempts boundary matching but misses "cad," or "cad." or "CAD/CAM".

**Prevention:**
1. Use word boundary regex: `\bcad\b`
2. Or token-based matching after splitting on whitespace/punctuation
3. Test against real description corpus for unintended matches

**Detection (Warning Signs):**
- Short terms (2-3 letters) cause false positives
- Trailing spaces used inconsistently
- Terms match unrelated words

**Phase to address:** Phase 2 - Part of filter refactoring

---

### Pitfall 11: No Negative Feedback Loop

**What goes wrong:**
Rejected leads are not analyzed. Same false positive categories reappear. No learning from mistakes.

**Your current state:**
Rejected leads JSON files exist but no automated analysis. Manual review identified tennis/linemen/aerospace categories.

**Prevention:**
1. Cluster rejected leads to find patterns
2. Track rejection reasons (which exclusion triggered)
3. Regular review of rejection categories
4. Feed back into filter development

**Phase to address:** Phase 1 - Part of measurement infrastructure

---

### Pitfall 12: Overlapping/Conflicting Signals

**What goes wrong:**
The same term appears in both include and exclude logic, or signals contradict each other. Results become unpredictable.

**Your current state:**
"stringing" is a strong positive signal (solar panel stringing) but also indicates tennis (racquet stringing). Handled by order (exclude tennis first), but fragile.

**Prevention:**
1. Audit for terms appearing in multiple lists
2. Use context-dependent signals, not standalone terms
3. Document why each signal is included/excluded

**Phase to address:** Phase 2 - Part of filter audit

---

## Domain-Specific Pitfalls for Solar Lead Qualification

### Pitfall DS-1: Solar Industry Vertical Confusion

**Industries that mention "solar" but are not solar design:**
- Aerospace/satellite (solar panels on spacecraft)
- Consumer electronics (solar-powered gadgets)
- Water heating (solar thermal, not PV)
- Real estate (south-facing windows, solar exposure)
- Agriculture (greenhouse, solar radiation)
- Gaming/entertainment ("Solar Studios", fictional names)

**Prevention:**
1. Require multiple solar + design signals, not just "solar"
2. Explicitly exclude known confounding industries
3. Check for PV-specific terminology (string sizing, inverter, module layout)

---

### Pitfall DS-2: Role Title Inflation/Deflation

**Job titles are unreliable:**
- "Solar Designer" could be graphic designer at solar marketing company
- "CAD Technician" at solar company could be facilities/HVAC
- "Engineer" is overloaded (software, electrical, civil, process)

**Prevention:**
1. Require description content, not just title match
2. Look for specific tools (Helioscope, Aurora, PVsyst)
3. Look for specific deliverables (permit sets, plan sets, single-line diagrams)

---

### Pitfall DS-3: Adjacent Roles That Are NOT Leads

**Roles at solar companies but not qualified leads:**
- Sales/business development (they buy, not use, design tools)
- Project managers (oversee, don't use CAD)
- Installers/field techs (install, don't design)
- O&M technicians (maintenance, not design)
- Estimators/preconstruction (cost, not CAD)
- Structural/civil engineers (foundations, not electrical)

**Prevention:**
1. Explicit exclusions for these role types
2. Require design/drafting role indicators
3. Separate "solar company employee" from "solar design role"

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Measurement setup | Ground truth subjectivity (P4) | Document labeling criteria FIRST |
| Filter refactoring | Tier ordering bugs (P6) | Convert to scoring system |
| ML exploration | Imbalanced data (P3) | Use precision/recall, class weights |
| Configuration extraction | Scope creep (P8) | Fixed config schema, not dynamic |
| Company enrichment | Over-reliance on name (DS-1) | Multiple signals required |

---

## Prevention Strategy Summary

### Immediate (Before Any Filter Changes)

1. **Document labeling criteria** - What exactly makes a lead "qualified"?
2. **Establish metrics** - Precision, recall, F1 on holdout set
3. **Create test set** - Golden labeled examples for regression testing

### Short-term (Phase 1-2)

1. **Convert to scoring** - Replace tier system with weighted scores
2. **Extract configuration** - Filter terms in JSON, not Python
3. **Add rejection logging** - Track which rule rejected each lead

### Medium-term (Phase 2-3)

1. **Semantic matching** - Context-aware signals, not substring matching
2. **Company enrichment** - Separate company qualification from role qualification
3. **Automated analysis** - Cluster rejected leads, surface patterns

### Ongoing

1. **Review rejection categories** - Weekly analysis of false positives
2. **Track false negatives** - Spot-check rejected leads for missed qualifications
3. **Version control discipline** - Separate filter config from code changes

---

## Warning Signs Checklist

Run this checklist after any filter change:

- [ ] Did precision improve without measuring recall?
- [ ] Did exclusion list grow? By how much?
- [ ] Are there terms in both include and exclude lists?
- [ ] Can you explain why any specific lead was rejected?
- [ ] Did you test on the golden test set?
- [ ] Is the change in config or code?

---

## Sources

**Primary:**
- Codebase analysis: `c:\Users\ehaug\OneDrive\Documents\GitHub\solar-lead-scraper\scraper.py`
- Git history: Filter evolution over 14 commits
- Project context: `.planning/PROJECT.md`, `.planning/codebase/CONCERNS.md`

**Domain expertise:**
- Text classification patterns (training data)
- Imbalanced learning best practices (training data)
- Lead qualification system patterns (training data)

**Confidence note:**
These pitfalls are derived from domain expertise and codebase analysis. WebSearch was unavailable for external validation. Recommend validating ML-specific recommendations against current best practices documentation when implementing those phases.

---

*Pitfalls research: 2026-01-18*
