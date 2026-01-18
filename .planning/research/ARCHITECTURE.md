# Architecture Research: Job Listing Classification Pipeline

**Domain:** Text classification/filtering for lead qualification
**Researched:** 2026-01-18
**Confidence:** MEDIUM (based on established patterns in text classification; no external sources available for verification)

## Executive Summary

The current architecture is a monolithic scrape-filter-output pipeline in a single 400-line file. For improved filtering with potential ML integration, recommend evolving to a **staged pipeline architecture** with clear separation between: data acquisition, preprocessing, classification (rules + optional ML scoring), and output formatting. This allows incremental improvement without rewriting, maintains testability, and provides a clear path to add ML scoring later without disrupting the rule-based system that works today.

## Recommended Architecture

### High-Level Design: Staged Pipeline with Pluggable Classifiers

```
[Job Boards] --> [Scraper] --> [Preprocessor] --> [Classifier Pipeline] --> [Output Formatter] --> [CSV/Dashboard]
                                                         |
                                                    +---------+
                                                    |         |
                                              [Rule Engine] [ML Scorer]
                                                    |         |
                                                    +---------+
                                                         |
                                                    [Combiner]
```

**Why this design:**
1. **Separation of concerns** - Each stage has one job, testable independently
2. **Incremental evolution** - Can improve one stage without touching others
3. **ML-optional** - Rules work alone; ML scoring is additive, not required
4. **Debuggable** - Can inspect data at each stage to diagnose issues
5. **Maintains simplicity** - No external services, still runs as single Python process

### Architecture Principles

| Principle | Application |
|-----------|-------------|
| Single Responsibility | Each component does one thing |
| Open-Closed | Add new filters/scorers without modifying existing |
| Dependency Inversion | Components depend on interfaces, not implementations |
| Fail-Fast | Bad data caught early, not at output |
| Observable | Each stage can log/report its decisions |

## Component Breakdown

### 1. Data Acquisition Layer (Scraper)

**Responsibility:** Fetch raw job listings from external sources

**Current:** `scrape_solar_jobs()` function in `scraper.py`

**Recommended Structure:**
```
scraper/
  __init__.py
  jobspy_adapter.py    # Wraps python-jobspy library
  models.py            # RawJobListing dataclass
```

**Interface:**
```python
@dataclass
class RawJobListing:
    id: str                    # Unique identifier (job_url hash)
    title: str
    company: str
    location: str
    description: str
    job_url: str
    source: str                # indeed/glassdoor/ziprecruiter
    scraped_at: datetime

def scrape(search_terms: list[str], results_per_term: int = 100) -> list[RawJobListing]:
    """Fetch raw listings. No filtering here."""
```

**Key Design Decisions:**
- Scraper does NOT filter - that's classification's job
- Returns structured data, not DataFrames (easier to test)
- Wraps jobspy so it can be mocked in tests
- Handles retries and rate limiting internally

### 2. Preprocessing Layer

**Responsibility:** Normalize and enrich raw data before classification

**Current:** Implicit in `description_matches()` (lowercase conversion)

**Recommended Structure:**
```
preprocessing/
  __init__.py
  normalizer.py        # Text normalization (lowercase, clean unicode)
  enricher.py          # Add derived fields (company_name_clean, etc.)
  models.py            # ProcessedJobListing dataclass
```

**Interface:**
```python
@dataclass
class ProcessedJobListing:
    raw: RawJobListing
    description_normalized: str   # Lowercased, cleaned
    title_normalized: str
    company_clean: str            # Suffix removed
    domain_guess: str
    # Extracted features for classification
    features: dict[str, any]      # e.g., {"has_solar_mention": True}

def preprocess(listings: list[RawJobListing]) -> list[ProcessedJobListing]:
    """Normalize and enrich. No filtering here."""
```

**Why separate preprocessing:**
- Normalization logic is reusable across rules and ML
- Feature extraction happens once, used by multiple classifiers
- Easy to add new features without touching classification logic

### 3. Classification Layer (Core Innovation)

**Responsibility:** Decide which listings are qualified leads

**Current:** Monolithic `description_matches()` with 6 tiers

**Recommended Structure:**
```
classification/
  __init__.py
  pipeline.py          # Orchestrates classification stages
  rules/
    __init__.py
    base.py            # BaseRule abstract class
    exclusion_rules.py # Reject tennis, aerospace, etc.
    inclusion_rules.py # Accept solar-specific tools, etc.
    tier_rules.py      # Tiered qualification (current 6-tier logic)
  scoring/
    __init__.py
    base.py            # BaseScorer abstract class
    keyword_scorer.py  # Weighted keyword scoring
    ml_scorer.py       # Optional ML model integration
  combiner.py          # Combines rule verdicts + scores into final decision
  models.py            # ClassificationResult dataclass
```

**Classification Pipeline Design:**

```
[ProcessedListing] --> [Exclusion Rules] --> [Inclusion Rules] --> [Scorers] --> [Combiner] --> [Result]
                              |                     |                  |
                        REJECT early          ACCEPT early        Add confidence
                        (tennis, etc)         (helioscope, etc)   score to result
```

**Interface:**
```python
@dataclass
class ClassificationResult:
    listing: ProcessedJobListing
    decision: str                 # "QUALIFIED" | "REJECTED" | "REVIEW"
    confidence: float             # 0.0 to 1.0
    reasons: list[str]            # Why this decision
    rule_verdicts: dict[str, str] # Which rules fired
    scores: dict[str, float]      # Scores from each scorer

class ClassificationPipeline:
    def __init__(self,
                 exclusion_rules: list[BaseRule],
                 inclusion_rules: list[BaseRule],
                 scorers: list[BaseScorer],
                 combiner: Combiner):
        ...

    def classify(self, listing: ProcessedJobListing) -> ClassificationResult:
        # 1. Run exclusion rules (any REJECT = final REJECT)
        # 2. Run inclusion rules (any ACCEPT = qualified, continue for confidence)
        # 3. Run scorers (add confidence scores)
        # 4. Combine into final decision
```

**Rule Interface:**
```python
class BaseRule(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def evaluate(self, listing: ProcessedJobListing) -> RuleResult:
        """Returns ACCEPT, REJECT, or NEUTRAL"""
```

**Scorer Interface:**
```python
class BaseScorer(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def score(self, listing: ProcessedJobListing) -> float:
        """Returns 0.0 to 1.0 confidence score"""
```

### 4. Output Layer

**Responsibility:** Format results for consumption (CSV, dashboard)

**Current:** DataFrame manipulation in `process_jobs()`, CSV writing in `main()`

**Recommended Structure:**
```
output/
  __init__.py
  formatter.py         # Convert results to output format
  csv_writer.py        # Write to CSV
  dashboard_client.py  # Upload to dashboard API
  linkedin_urls.py     # Generate LinkedIn search URLs
```

**Interface:**
```python
@dataclass
class Lead:
    company: str
    domain: str
    job_title: str
    location: str
    posting_url: str
    linkedin_managers: str
    linkedin_hiring: str
    linkedin_role: str
    google_enduser: str
    date_scraped: str
    confidence: float          # NEW: from classification
    qualification_reasons: str # NEW: from classification

def format_leads(results: list[ClassificationResult]) -> list[Lead]:
    """Filter to qualified, dedupe by company, format output"""

def write_csv(leads: list[Lead], output_path: Path) -> None: ...
def upload_to_dashboard(leads: list[Lead], api_url: str, api_key: str) -> None: ...
```

### 5. Configuration Layer

**Responsibility:** Externalize settings currently hardcoded

**Recommended Structure:**
```
config/
  __init__.py
  settings.py          # Configuration dataclasses
  loader.py            # Load from YAML/JSON/env
  search_terms.yaml    # Search terms (currently hardcoded list)
  filter_terms.yaml    # Exclusion/inclusion term lists
```

**Why externalize configuration:**
- Change filter terms without code changes
- A/B test different filter configurations
- Version control filter iterations separately from code
- Enable per-environment configuration

## Data Flow

### Primary Pipeline Flow

```
1. ACQUIRE
   Input:  Search configuration (terms, results_per_term)
   Action: Call jobspy for each term
   Output: list[RawJobListing]

2. PREPROCESS
   Input:  list[RawJobListing]
   Action: Normalize text, extract features, enrich
   Output: list[ProcessedJobListing]

3. CLASSIFY
   Input:  list[ProcessedJobListing]
   Action: Run through exclusion rules, inclusion rules, scorers
   Output: list[ClassificationResult]

4. FORMAT
   Input:  list[ClassificationResult]
   Action: Filter qualified, dedupe, generate URLs
   Output: list[Lead]

5. OUTPUT
   Input:  list[Lead]
   Action: Write CSV, upload to dashboard
   Output: Files/API calls
```

### Classification Sub-Flow (Detail)

```
For each ProcessedJobListing:

1. EXCLUSION PHASE
   - Run all exclusion rules in parallel
   - If ANY returns REJECT:
     - Result = REJECTED
     - Stop processing, return early
   - Else: Continue to inclusion

2. INCLUSION PHASE
   - Run all inclusion rules in sequence (by tier)
   - If ANY returns ACCEPT:
     - Mark as QUALIFIED
     - Continue to scoring for confidence
   - If none accept and all NEUTRAL:
     - Mark as tentative REVIEW

3. SCORING PHASE
   - Run all scorers
   - Aggregate scores (weighted average or max)
   - Attach confidence score to result

4. COMBINATION PHASE
   - If QUALIFIED: final decision = QUALIFIED
   - If REVIEW + high confidence: decision = QUALIFIED
   - If REVIEW + low confidence: decision = REVIEW
   - Return ClassificationResult with full audit trail
```

## Build Order (Dependency Graph)

Dependencies determine the order components must be built. Build leaf nodes first.

```
                    [main.py]
                       |
              +--------+--------+
              |                 |
        [Pipeline]         [Config Loader]
              |
    +---------+---------+
    |         |         |
[Scraper] [Classifier] [Output]
              |
    +---------+---------+
    |         |         |
[Rules]   [Scorers]  [Combiner]
    |         |
    |    [ML Scorer] (optional, later)
    |
[Preprocessor]
```

### Recommended Build Sequence

**Phase 1: Foundation (Extract and Modularize)**
1. `models.py` - Define dataclasses (RawJobListing, ProcessedJobListing, ClassificationResult, Lead)
2. `config/` - Extract hardcoded values to configuration files
3. `preprocessing/` - Extract normalization logic from current filter function

**Phase 2: Rule Engine (Refactor Current Logic)**
4. `classification/rules/base.py` - Define BaseRule interface
5. `classification/rules/exclusion_rules.py` - Port current exclusion logic (tennis, aerospace, etc.)
6. `classification/rules/inclusion_rules.py` - Port tier 1-6 logic as separate rules
7. `classification/pipeline.py` - Wire rules together

**Phase 3: Output (Extract and Enhance)**
8. `output/formatter.py` - Extract lead formatting logic
9. `output/csv_writer.py` - Extract CSV writing
10. `output/linkedin_urls.py` - Extract URL generation functions

**Phase 4: Integration**
11. `scraper/` - Wrap jobspy with clean interface
12. `main.py` - Wire everything together

**Phase 5: ML Enhancement (Optional, Later)**
13. `classification/scoring/keyword_scorer.py` - Add confidence scoring
14. `classification/scoring/ml_scorer.py` - Add ML model scoring
15. `classification/combiner.py` - Combine rules + scores

### Why This Order

| Phase | Rationale |
|-------|-----------|
| 1. Foundation | Models and config are dependencies for everything else |
| 2. Rules | Core business logic; most value, most risk - get it right first |
| 3. Output | Low risk, easy to extract, builds on classification results |
| 4. Integration | Only integrate after pieces are tested individually |
| 5. ML | Optional enhancement; rules must work standalone first |

## ML Integration Strategy

### Approach: Rules-First, ML-Augmented

**Why not ML-only:**
- Only 16 qualified examples (insufficient for training)
- Rule-based system is working (just needs tuning)
- Rules are interpretable and auditable
- ML is a black box; hard to debug false positives

**Why not ignore ML:**
- Training data exists (can learn from rejected patterns)
- ML can catch edge cases rules miss
- Confidence scoring valuable even without full ML classification

### ML Integration Points

```
Option A: ML as Tie-Breaker (Recommended)
  - Rules make primary decision
  - ML provides confidence score
  - Low-confidence QUALIFIED items get flagged for REVIEW

Option B: ML as Pre-Filter
  - ML scores all listings first
  - Only high-confidence items go through rules
  - Risk: ML errors propagate

Option C: Ensemble
  - Rules and ML both classify independently
  - Combiner reconciles disagreements
  - Most complex, needs more training data
```

### Recommended ML Architecture (for later phase)

```python
# Simple keyword-weight scoring (no external ML library needed)
class KeywordScorer(BaseScorer):
    """Scores based on weighted keyword presence"""

    def __init__(self, positive_weights: dict, negative_weights: dict):
        self.positive = positive_weights  # {"helioscope": 0.9, "pv system": 0.7, ...}
        self.negative = negative_weights  # {"tennis": -1.0, "spacecraft": -0.8, ...}

    def score(self, listing: ProcessedJobListing) -> float:
        text = listing.description_normalized
        score = 0.5  # Neutral baseline
        for keyword, weight in self.positive.items():
            if keyword in text:
                score += weight * (1 - score)  # Diminishing returns
        for keyword, weight in self.negative.items():
            if keyword in text:
                score += weight * score  # Reduce score
        return max(0.0, min(1.0, score))
```

**If more sophisticated ML needed later:**
- scikit-learn TF-IDF + LogisticRegression (lightweight, fast)
- No deep learning until 1000+ training examples
- Keep model file small (<10MB) to fit in GitHub repo

## File Structure (Target State)

```
solar-lead-scraper/
  scraper/
    __init__.py
    jobspy_adapter.py
    models.py
  preprocessing/
    __init__.py
    normalizer.py
    enricher.py
    models.py
  classification/
    __init__.py
    pipeline.py
    combiner.py
    models.py
    rules/
      __init__.py
      base.py
      exclusion_rules.py
      inclusion_rules.py
    scoring/
      __init__.py
      base.py
      keyword_scorer.py
  output/
    __init__.py
    formatter.py
    csv_writer.py
    dashboard_client.py
    linkedin_urls.py
  config/
    __init__.py
    settings.py
    loader.py
  data/
    search_terms.yaml
    filter_config.yaml
    keyword_weights.json    # For scorer
  tests/
    __init__.py
    test_rules.py
    test_preprocessing.py
    test_pipeline.py
    fixtures/
      sample_listings.json
  main.py                   # Entry point
  requirements.txt
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Premature ML Integration
**What:** Adding ML before rules are solid
**Why bad:** ML masks rule bugs; harder to debug
**Instead:** Get rules to 80%+ precision first, then add ML for the remaining edge cases

### Anti-Pattern 2: Monolithic Classifier
**What:** Single function with all classification logic
**Why bad:** Current state - untestable, hard to modify
**Instead:** Separate rules into independent, testable units

### Anti-Pattern 3: Implicit Dependencies
**What:** Functions that silently depend on pandas DataFrame structure
**Why bad:** Column renames break everything; no compile-time safety
**Instead:** Use explicit dataclasses with typed fields

### Anti-Pattern 4: Configuration in Code
**What:** Hardcoded term lists in function bodies
**Why bad:** Every filter change requires code deployment
**Instead:** External configuration files that can be updated independently

### Anti-Pattern 5: All-or-Nothing Classification
**What:** Binary QUALIFIED/REJECTED with no middle ground
**Why bad:** Misses opportunity to surface uncertain cases for human review
**Instead:** Add REVIEW category for low-confidence decisions

## Testing Strategy

### Unit Tests by Component

| Component | Test Focus |
|-----------|------------|
| Exclusion Rules | Each rule correctly rejects its target patterns |
| Inclusion Rules | Each tier accepts expected patterns, rejects non-matches |
| Preprocessor | Normalization is consistent, features extracted correctly |
| Combiner | Decision logic handles edge cases (all reject, mixed, etc.) |
| Output Formatter | Deduplication works, URL generation correct |

### Integration Tests

| Test | Purpose |
|------|---------|
| End-to-end pipeline | Mock scraper -> real classification -> output matches expected |
| Configuration loading | YAML/JSON config loads and applies correctly |
| Regression suite | Known good/bad listings produce expected decisions |

### Test Data Management

```
tests/fixtures/
  qualified_samples.json    # Known good leads
  rejected_samples.json     # Known bad leads
  edge_cases.json           # Tricky cases for regression
```

## Migration Path from Current State

### Step 1: Add Tests for Current Logic (No Refactoring)
- Write tests against `description_matches()` as-is
- Capture current behavior to prevent regression
- Use rejected/qualified training data as test cases

### Step 2: Extract Configuration (Minimal Code Change)
- Move term lists to YAML files
- Import terms in `description_matches()`
- Behavior unchanged, just externalized

### Step 3: Create Rule Classes (Parallel Implementation)
- Build new rule classes alongside existing function
- New rules must match old function behavior
- Delete old function only when new matches exactly

### Step 4: Wire New Pipeline
- Replace `scrape_solar_jobs()` filter call with new pipeline
- Verify output matches

### Step 5: Add Scoring (Enhancement)
- Add confidence scores to output
- No classification change, just additional data

### Step 6: ML Integration (Optional)
- Add ML scorer alongside keyword scorer
- Use combiner to incorporate scores into decisions

## Confidence Assessment

| Area | Confidence | Rationale |
|------|------------|-----------|
| Pipeline structure | HIGH | Standard ETL pattern, proven in many systems |
| Rule engine design | HIGH | Common pattern for business rule systems |
| Build order | HIGH | Based on clear dependency analysis |
| ML integration approach | MEDIUM | Depends on training data quality, untested |
| Performance characteristics | LOW | No profiling data; assumed fast enough for current scale |

## Open Questions

1. **Training data format** - PROJECT.md mentions JSON files but they're not in repo. Where is this data?
2. **Performance requirements** - Is the current runtime acceptable? Parallelization adds complexity.
3. **Human review workflow** - If we add REVIEW category, what's the process for handling those?
4. **Model persistence** - If ML scorer added, where to store trained models?

---

*Architecture research: 2026-01-18*
*Applies to: lead qualification/filtering pipeline restructuring*
