# Research Summary

**Project:** Solar Lead Scraper - Improved Filtering
**Domain:** Text classification / lead qualification
**Researched:** 2026-01-18
**Confidence:** MEDIUM

## Key Recommendations

1. **Start with data-driven rule refinement, not ML** - With only 16 qualified examples vs 500+ rejected, analyze labeled data to extract discriminative terms before attempting machine learning.

2. **Convert tiered filtering to weighted scoring** - Replace the 6-tier IF-ELSE chain with a scoring system where signals add/subtract points, enabling fine-tuning without order-dependent bugs.

3. **Add company-level classification** - Most false positives (aerospace, semiconductor) are company-level issues, not role-level. Implement blocklist for Boeing, Northrop Grumman, SpaceX, etc.

4. **Extract filter configuration from code** - Move 60+ exclusion terms and 50+ inclusion terms to YAML/JSON files to enable iteration without code deployments.

5. **Establish ground truth metrics before optimization** - Document labeling criteria, create golden test set, measure precision AND recall to avoid exclusion whack-a-mole.

## Stack

Use the existing stack (pandas, re, json) for Phase 1 data-driven rule refinement. Add scikit-learn (TF-IDF + Naive Bayes/LogisticRegression with class_weight='balanced') only when you have 50+ qualified examples. Avoid deep learning, LLM APIs, and heavy NLP libraries - they require far more training data than available and add infrastructure overhead inappropriate for a GitHub Actions workflow.

## Features

**High-signal inclusion features:**
- Solar-specific tools (Helioscope, Aurora Solar, PVsyst) - auto-qualify
- Solar-specific deliverables (stringing diagrams, permit sets, array layouts)
- Explicit role titles (solar designer, pv drafter, solar design engineer)
- Company name signals ("solar", "pv" in company name)

**Critical exclusion features to add:**
- Company blocklist: Boeing, Northrop Grumman, SpaceX, Lockheed, Raytheon
- Missing role exclusions: stringer, roofer, foreman, interconnection engineer
- EDA tool exclusions: Cadence, Synopsys (chip design false positives)

**Feature engineering priority:**
- Compound boolean logic (stringing AND solar context AND NOT tennis)
- Scoring model replacing binary tiers
- Company classification as separate dimension from role classification

## Architecture

Evolve from monolithic 400-line scraper.py to a **staged pipeline architecture** with clear separation:

1. **Scraper Layer** - Fetch raw listings, no filtering
2. **Preprocessing Layer** - Normalize text, extract features
3. **Classification Layer** - Rules (exclusion -> inclusion) + optional ML scoring
4. **Output Layer** - Format leads, dedupe, generate LinkedIn URLs

The classification layer should use pluggable rules with a consistent interface (BaseRule.evaluate() returns ACCEPT/REJECT/NEUTRAL) and a combiner that aggregates rule verdicts and scorer confidence into final decisions.

**Build order:** Models/config first, then rule engine, then output extraction, then integration, then optional ML scoring.

## Pitfalls to Avoid

1. **Exclusion whack-a-mole** - Track both precision AND recall when adding exclusions; require 3+ examples of a pattern before adding new exclusion terms.

2. **Word matching without semantic context** - "Solar" matches tennis stringing, aerospace panels, and solar energy equally. Use compound features (solar AND design AND CAD) not individual terms.

3. **Imbalanced data without adjustment** - With 3% positive rate, accuracy is meaningless. Use precision/recall/F1 metrics and class_weight='balanced' for any ML approaches.

---

*Research completed: 2026-01-18*
*Ready for roadmap: yes*
