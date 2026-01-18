# Phase 2: Data-Driven Rule Refinement - Research

**Researched:** 2026-01-18
**Domain:** Text pattern extraction / rule-based classification improvement
**Confidence:** HIGH

## Summary

Phase 2 focuses on improving filter precision by adding rules derived from analysis of labeled/rejected data. The approach is straightforward: analyze what false positives currently slip through, identify patterns (company names, role terms, tool names), and add targeted blocklists and exclusions.

The core deliverables are:
1. **Pattern analysis** of rejected leads to extract false positive categories
2. **Company blocklist** for known aerospace/semiconductor false positive companies (Boeing, Northrop Grumman, SpaceX, Lockheed, Raytheon)
3. **Missing exclusion terms** for roles (stringer, roofer, foreman, interconnection engineer) and EDA tools (Cadence, Synopsys)

**Primary recommendation:** Keep the rule-based approach simple. This phase is about adding targeted exclusions based on evidence, not architectural changes. The blocklist should be a simple Python list or JSON file in the filter function. Each new exclusion should be validated against the golden test set to ensure no regressions.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.x | List/set operations for blocklists | No dependencies needed |
| json | stdlib | Store blocklist as external config (optional) | Human-readable, easy to edit |
| re | stdlib | Pattern matching for term extraction | Already used in scraper.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandas | existing | DataFrame operations for labeled data analysis | Already in project |
| collections.Counter | stdlib | Term frequency counting | Built-in, efficient |
| scikit-learn TfidfVectorizer | 1.5+ | TF-IDF for term importance (optional) | If automated pattern extraction desired |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hardcoded Python lists | External JSON config | JSON = easier editing by non-developers, but adds complexity |
| Simple substring matching | Regex patterns | Regex = more flexible but harder to maintain |
| Manual analysis | TF-IDF automated extraction | Manual = more precise for small datasets like this |

**Installation:**
```bash
# No new dependencies required - all stdlib or already installed
```

## Architecture Patterns

### Recommended Project Structure
```
solar-lead-scraper/
  scraper.py                # description_matches() with new exclusions
  data/
    labeled/                # Labeled data for analysis
      *.json                # Rejected/qualified lead files
    golden/
      golden-test-set.json  # Regression test set
  evaluate.py               # Evaluation script to validate changes
```

### Pattern 1: Company Blocklist Implementation
**What:** A list of company names/patterns to auto-reject
**When to use:** When false positives share a company-level pattern (aerospace, semiconductor)

```python
# Source: Best practice from blocklist-aggregator patterns
# In scraper.py description_matches() function

# Company blocklist - known false positive companies
COMPANY_BLOCKLIST = {
    # Aerospace/Defense
    'boeing', 'northrop grumman', 'lockheed', 'lockheed martin',
    'raytheon', 'spacex', 'blue origin', 'general dynamics',
    'bae systems', 'l3harris', 'leidos',
    # Semiconductor
    'intel', 'nvidia', 'amd', 'qualcomm', 'broadcom',
    'texas instruments', 'micron', 'applied materials',
}

def is_blocked_company(company_name: str) -> bool:
    """Check if company is on blocklist."""
    if not company_name:
        return False
    company_lower = company_name.lower()
    return any(blocked in company_lower for blocked in COMPANY_BLOCKLIST)
```

**Key considerations:**
- Use lowercase comparison for case-insensitivity
- Use substring matching (e.g., "Northrop Grumman Corporation" matches "northrop grumman")
- Keep blocklist as a set for O(1) lookup performance
- Log blocked companies for audit/review

### Pattern 2: Role Exclusion Term Addition
**What:** Adding missing exclusion terms to existing exclusion blocks
**When to use:** When specific terms are identified as causing false positives

```python
# Source: Existing pattern in scraper.py
# Add to installer_terms list:
installer_terms = [
    # ... existing terms ...
    'stringer',           # Tennis/racquet false positives
    'roofer',             # Installation labor
    'foreman',            # Construction supervision
    'crew lead',          # Installation supervision
]

# Add to other_eng_terms list:
other_eng_terms = [
    # ... existing terms ...
    'interconnection engineer',  # Utility interface role
    'grid engineer',             # Utility focus
]
```

### Pattern 3: EDA Tool Exclusions
**What:** Exclusion terms for semiconductor/chip design tools
**When to use:** When CAD search terms match chip design roles

```python
# Source: Industry knowledge - EDA = Electronic Design Automation
# Add new exclusion block in description_matches():

# Exclude EDA/chip design tools (different kind of "CAD")
eda_tools = [
    'cadence', 'synopsys', 'mentor graphics', 'siemens eda',
    'virtuoso', 'spectre', 'innovus', 'genus', 'conformal',
    'calibre', 'questa', 'modelsim', 'vcs', 'verdi',
    'primetime', 'icc2', 'dc_shell', 'design compiler'
]
if any(tool in desc_lower for tool in eda_tools):
    return False
```

### Pattern 4: False Positive Pattern Analysis Workflow
**What:** Manual analysis workflow for extracting patterns from rejected data
**When to use:** Before adding new rules, to identify what patterns exist

```python
# Analysis script pattern for extracting false positive patterns
# This is for one-time analysis, not production code

import json
from collections import Counter
from pathlib import Path

def analyze_rejected_leads(filepath: Path) -> dict:
    """Extract patterns from rejected leads."""
    with open(filepath) as f:
        data = json.load(f)

    items = data.get("items", data)

    # Count company names
    companies = Counter()
    for item in items:
        company = item.get("company", "").lower()
        if company:
            companies[company] += 1

    # Extract terms that appear frequently
    all_descriptions = " ".join(item.get("description", "") for item in items)
    words = all_descriptions.lower().split()
    word_freq = Counter(words)

    return {
        "top_companies": companies.most_common(20),
        "top_terms": word_freq.most_common(50),
        "total_items": len(items)
    }
```

### Anti-Patterns to Avoid
- **Adding exclusions without validation:** Every new exclusion must be tested against golden set
- **Overly specific patterns:** "Boeing Corporation" instead of "boeing" misses variations
- **Blocking entire industries instead of companies:** "aerospace" in description is fine; company-level blocking is better
- **Forgetting to track recall:** New exclusions can create false negatives

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Term frequency analysis | Custom tokenizer | `collections.Counter` + split() | Built-in, handles edge cases |
| TF-IDF calculation | Manual math | `sklearn.TfidfVectorizer` | Battle-tested, handles edge cases |
| Regex for patterns | Complex regex | Simple substring matching | Substring is faster, easier to debug |
| Company name normalization | Custom cleanup | Lowercase + substring matching | Good enough for blocklist |
| Metric calculation | Manual counts | `sklearn.metrics` | Already using it |

**Key insight:** For a blocklist of ~50-100 companies, simple Python data structures (sets, lists) are sufficient. Don't over-engineer with databases or external services.

## Common Pitfalls

### Pitfall 1: Blocklist Whack-a-Mole
**What goes wrong:** Adding companies one-by-one reactively without grouping by pattern
**Why it happens:** Each false positive is addressed individually without root cause analysis
**How to avoid:** Group companies by industry/category, add entire category at once
**Warning signs:** Blocklist grows faster than precision improves

### Pitfall 2: Over-Exclusion Creating False Negatives
**What goes wrong:** Broad exclusion terms reject valid leads
**Why it happens:** Terms like "engineer" or "manager" are too generic
**How to avoid:** Use compound matching (exclusion AND NOT design role), validate against golden set
**Warning signs:** Recall drops while precision improves, lead volume decreases sharply

### Pitfall 3: Excluding Based on Description When Company Is the Issue
**What goes wrong:** Adding description-level exclusions for company-level problems
**Why it happens:** Description is what's being analyzed; company name is separate
**How to avoid:** Implement company blocklist first, then add term-level exclusions for remaining issues
**Warning signs:** Aerospace/semiconductor exclusion terms grow while Boeing still appears in output

### Pitfall 4: Not Validating Against Golden Test Set
**What goes wrong:** New rules break existing correct classifications
**Why it happens:** Testing only the specific case that triggered the change
**How to avoid:** Run `python evaluate.py --golden` after every rule change
**Warning signs:** "Fixed" a false positive but broke another case

### Pitfall 5: Ambiguous Term Exclusions
**What goes wrong:** Excluding "solar" in certain contexts is impossible without semantic analysis
**Why it happens:** The same word means different things in different contexts
**How to avoid:** Use compound matching, consider context (company, job title), not just description
**Warning signs:** Exclusion for one context creates false negatives in target context

## Code Examples

Verified patterns for this phase:

### Adding Company Blocklist to description_matches()
```python
# Location: scraper.py, at the top of description_matches()
# Source: Standard blocklist pattern

# Company blocklist for known false positive industries
COMPANY_BLOCKLIST = {
    # Aerospace/Defense - "solar" in these companies = spacecraft solar panels
    'boeing', 'northrop grumman', 'lockheed', 'lockheed martin',
    'raytheon', 'spacex', 'blue origin', 'general dynamics',
    'bae systems', 'l3harris', 'leidos', 'huntington ingalls',
    # Semiconductor - "CAD" in these companies = chip design
    'intel', 'nvidia', 'amd', 'qualcomm', 'broadcom',
    'texas instruments', 'micron', 'applied materials',
    'lam research', 'kla', 'asml',
}

def description_matches(description: str, company_name: str = None) -> bool:
    """Check if job description matches our criteria for solar design roles."""
    # Company blocklist check FIRST (before description analysis)
    if company_name:
        company_lower = company_name.lower()
        for blocked in COMPANY_BLOCKLIST:
            if blocked in company_lower:
                return False

    # ... rest of existing logic ...
```

### Adding Missing Role Exclusions
```python
# Location: scraper.py, installer_terms list
# Source: Pattern extraction from rejected leads + FEATURES.md analysis

# Add to existing installer_terms list:
'stringer',              # Tennis/racquet false positives (not solar stringing)
'roofer',                # Installation labor, not design
'foreman',               # Construction supervision
'crew lead',             # Installation crew supervision
'panel installer',       # Explicit installer role

# Add to existing other_eng_terms list:
'interconnection engineer',  # Utility interface, not PV design
'grid engineer',             # Grid/utility focus
'power systems analyst',     # Analysis, not design
'protection engineer',       # Utility protection
```

### Adding EDA Tool Exclusions
```python
# Location: scraper.py, new exclusion block after semiconductor_terms
# Source: Industry knowledge of EDA tool ecosystem

# Exclude EDA/chip design tools (semiconductor CAD, not solar CAD)
eda_tools = [
    'cadence', 'synopsys', 'mentor graphics', 'siemens eda',
    'virtuoso', 'spectre', 'innovus', 'genus', 'conformal',
    'calibre', 'questa', 'modelsim', 'vcs', 'verdi',
    'primetime', 'icc2', 'design compiler', 'dc shell',
    'spyglass', 'formality', 'tetramax', 'encounter'
]
if any(tool in desc_lower for tool in eda_tools):
    return False
```

### Validation Workflow
```bash
# After every rule change:
python evaluate.py --golden

# Expected output:
# - Precision should stay at 100% (no new false positives)
# - Recall should stay at 75% or improve (no new false negatives)
# - If recall drops, investigate which positive was excluded
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Generic "aerospace" exclusion | Company-level blocklist | Current best practice | More precise targeting |
| Single-term matching | Compound feature matching | Established pattern | Reduces ambiguity |
| Hardcoded exclusion lists | External config (JSON/YAML) | Optional for Phase 3 | Easier maintenance |
| Binary pass/fail | Scoring with threshold | Phase 3 target | More nuanced decisions |

**Deprecated/outdated:**
- Blocking entire industries by keyword ("aerospace" in description) - too broad
- Adding exclusions without measuring recall impact - creates invisible false negatives

## Open Questions

Things that couldn't be fully resolved:

1. **Labeled data availability**
   - What we know: PROJECT.md mentions rejected-leads-*.json files but they don't exist in repo
   - What's unclear: Whether data was lost, never committed, or in different location
   - Recommendation: Plan 02-01 should create labeled data if not available, or document workflow for labeling

2. **Company name availability in filter**
   - What we know: `description_matches()` currently only takes description text
   - What's unclear: Whether company name is available at filter time
   - Recommendation: May need to modify function signature to accept company name, or implement company check separately

3. **BESS/Storage handling**
   - What we know: BESS appears in some titles with PV (e.g., "Substation / PV / BESS / Wind")
   - What's unclear: Should BESS-only roles be excluded? Hybrid roles seem valid
   - Recommendation: Keep BESS roles that also mention PV; defer pure BESS exclusion to separate analysis

4. **Design Manager edge case**
   - What we know: "Design Manager" at Voltage appears in output
   - What's unclear: Is this a false positive (manager doesn't use software) or valid (manages designers, influences purchases)
   - Recommendation: Keep for now; may be legitimate lead for enterprise sales

## Sources

### Primary (HIGH confidence)
- Existing codebase analysis: `scraper.py` filter implementation
- Phase 1 research: `.planning/phases/01-metrics-foundation/01-RESEARCH.md`
- Features research: `.planning/research/FEATURES.md` (comprehensive gap analysis)
- Baseline metrics: `.planning/phases/01-metrics-foundation/01-BASELINE.md`
- Golden test set: `data/golden/golden-test-set.json` (33 curated examples)

### Secondary (MEDIUM confidence)
- [scikit-learn TfidfVectorizer documentation](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html) - for optional automated extraction
- [Python Keyword Extraction Tutorial using TF-IDF](https://kavita-ganesan.com/python-keyword-extraction/) - pattern extraction methodology
- [Extract Rules from Decision Tree in 3 Ways with Scikit-Learn and Python](https://mljar.com/blog/extract-rules-decision-tree/) - rule extraction patterns
- [Best Practices for Working with Configuration in Python](https://tech.preferred.jp/en/blog/working-with-configuration-in-python/) - configuration management

### Tertiary (LOW confidence)
- WebSearch results on blocklist implementation patterns - general patterns, not specific to this use case
- Training data knowledge on rule-based filtering - needs validation against current codebase

## Metadata

**Confidence breakdown:**
- Company blocklist approach: HIGH - clear pattern, identified companies documented
- Role exclusion additions: HIGH - specific terms identified in FEATURES.md
- EDA tool exclusions: HIGH - standard semiconductor tools well-known
- Analysis workflow: MEDIUM - depends on labeled data availability
- Golden set validation: HIGH - infrastructure already in place from Phase 1

**Research date:** 2026-01-18
**Valid until:** 90 days (domain-specific blocklists may need periodic updates)

---

*Research completed: 2026-01-18*
*Ready for planning: yes*
