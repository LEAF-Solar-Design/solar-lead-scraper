# Phase 4: Quality Instrumentation - Research

**Researched:** 2026-01-18
**Domain:** Python logging, statistics tracking, data export for ML labeling
**Confidence:** HIGH

## Summary

This phase adds observability to the solar lead scraper's filtering system. The goal is to understand filter behavior through statistics (QUAL-01), enable labeling workflow through rejected lead export (QUAL-02), and surface confidence in output (QUAL-03). This builds on Phase 3's `ScoringResult` dataclass which already captures `score`, `qualified`, `reasons`, `company_score`, and `role_score`.

The research confirms this can be achieved using Python standard library only (no new dependencies). The approach uses:
1. `collections.Counter` for per-rule statistics aggregation
2. `dataclasses.asdict()` for JSON export of rejected leads
3. Existing `ScoringResult.score` as the confidence signal (score relative to threshold)

**Primary recommendation:** Add a `FilterStats` dataclass to track per-rule counts during scoring runs, use Counter for efficient aggregation, export rejected leads as JSON (matching existing labeled data schema), and add confidence_score column to CSV output calculated from the existing score.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `collections.Counter` | stdlib | Aggregate rule hit counts | O(n) counting, dict subclass, arithmetic operations |
| `dataclasses.asdict` | stdlib | Convert ScoringResult to dict for JSON | Already using dataclasses, recursive dict conversion |
| `json` | stdlib | Export rejected leads | Already used for config loading |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typing` | stdlib | Type hints for stats dict | Already in use |
| `datetime` | stdlib | Timestamp exports | Already imported in scraper.py |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Counter | dict with manual counting | Counter is cleaner, supports arithmetic ops, returns 0 for missing keys |
| asdict | manual dict construction | asdict handles nested dataclasses automatically |
| print() for stats | logging module | logging adds complexity, print() matches existing codebase patterns |
| JSON for rejected | CSV | JSON matches labeled data schema, easier to merge for labeling |

**Installation:**
```bash
# No new dependencies required - all stdlib
```

## Architecture Patterns

### Recommended Approach: Extend Existing Structure

Given the flat file structure and Phase 3's additions to scraper.py, the recommended approach is to:

1. Add `FilterStats` dataclass to scraper.py (near `ScoringResult`)
2. Modify scoring functions to return stats alongside results
3. Add stats aggregation in `scrape_solar_jobs()`
4. Add rejected export function
5. Add confidence to CSV output in `process_jobs()`

```
solar-lead-scraper/
├── scraper.py           # Add FilterStats, stats collection, confidence
├── evaluate.py          # No changes needed
├── config/
│   └── filter-config.json  # No changes needed
└── output/
    ├── solar_leads_*.csv           # Add confidence_score column
    └── rejected_leads_*.json       # NEW: Exported for labeling
```

### Pattern 1: Statistics Collection with Counter

**What:** Track how many leads match each rule during a scoring run.

**When to use:** Per-run statistics logging (QUAL-01).

**Example:**
```python
# Source: Python stdlib collections.Counter
from collections import Counter
from dataclasses import dataclass, field

@dataclass
class FilterStats:
    """Statistics collected during a filter run.

    Attributes:
        total_processed: Total leads processed
        total_qualified: Leads that passed filter
        total_rejected: Leads that failed filter
        rejection_reasons: Counter of rejection reasons
        qualification_tiers: Counter of highest tier matched for qualifications
        company_blocked: Count of company blocklist rejections
    """
    total_processed: int = 0
    total_qualified: int = 0
    total_rejected: int = 0
    rejection_reasons: Counter = field(default_factory=Counter)
    qualification_tiers: Counter = field(default_factory=Counter)
    company_blocked: int = 0

def collect_stats(results: list[ScoringResult]) -> FilterStats:
    """Aggregate statistics from scoring results."""
    stats = FilterStats()

    for result in results:
        stats.total_processed += 1
        if result.qualified:
            stats.total_qualified += 1
            # Track highest tier from reasons
            for reason in result.reasons:
                if reason.startswith("+"):
                    tier = extract_tier_from_reason(reason)
                    stats.qualification_tiers[tier] += 1
                    break  # Count only highest
        else:
            stats.total_rejected += 1
            # Track rejection reason
            if result.reasons:
                stats.rejection_reasons[result.reasons[0]] += 1
            if result.company_score < 0:
                stats.company_blocked += 1

    return stats
```

### Pattern 2: Rejected Lead Export for Labeling

**What:** Export rejected leads in the same format as labeled data for human review.

**When to use:** Creating labeling exercises (QUAL-02).

**Example:**
```python
# Source: Matches existing data/golden/golden-test-set.json schema
from dataclasses import asdict
import json

@dataclass
class RejectedLead:
    """A rejected lead exported for labeling review.

    Schema matches labeled data format for easy import after review.
    """
    id: str
    description: str
    label: bool = False  # Presumed false, reviewer confirms
    company: str = None
    title: str = None
    rejection_reason: str = None
    score: float = 0.0

def export_rejected_leads(
    rejected: list[RejectedLead],
    output_path: Path,
    run_id: str
) -> None:
    """Export rejected leads for labeling review.

    Args:
        rejected: List of RejectedLead instances
        output_path: Directory to write JSON file
        run_id: Timestamp or identifier for this run
    """
    export_data = {
        "metadata": {
            "created": datetime.now().isoformat(),
            "purpose": "labeling_review",
            "run_id": run_id,
            "count": len(rejected)
        },
        "items": [asdict(lead) for lead in rejected]
    }

    filepath = output_path / f"rejected_leads_{run_id}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2)
```

### Pattern 3: Confidence Score Calculation

**What:** Convert numeric score to confidence metric for qualified leads.

**When to use:** Adding confidence to output (QUAL-03).

**Example:**
```python
# Source: Standard confidence score pattern
def calculate_confidence(result: ScoringResult) -> float:
    """Calculate confidence score from ScoringResult.

    Returns 0-100 scale where:
    - 100 = maximum possible score (tier 1 tool match = 100+)
    - 50 = threshold (minimum qualifying)
    - 0 = no positive signals matched

    For qualified leads, confidence represents score relative to threshold.
    """
    if not result.qualified:
        return 0.0

    # Score is already meaningful - scale to percentage
    # Tier 1 tools give 100 points, threshold is 50
    # A perfect tier 1 match = 100+ score, so 100 confidence
    # Threshold match (50) = 50 confidence
    confidence = min(100.0, result.score)
    return round(confidence, 1)
```

### Pattern 4: Statistics Logging

**What:** Print human-readable statistics summary at end of run.

**When to use:** Per-run logging (QUAL-01).

**Example:**
```python
# Source: Matches existing print() pattern in scraper.py
def print_filter_stats(stats: FilterStats) -> None:
    """Print human-readable filter statistics."""
    print()
    print("=" * 50)
    print("FILTER STATISTICS")
    print("=" * 50)
    print(f"Total processed:  {stats.total_processed}")
    print(f"Qualified:        {stats.total_qualified} ({stats.total_qualified/stats.total_processed*100:.1f}%)")
    print(f"Rejected:         {stats.total_rejected} ({stats.total_rejected/stats.total_processed*100:.1f}%)")

    if stats.company_blocked > 0:
        print(f"\nCompany blocklist: {stats.company_blocked}")

    if stats.rejection_reasons:
        print("\nTop rejection reasons:")
        for reason, count in stats.rejection_reasons.most_common(5):
            # Truncate long reasons
            display = reason[:60] + "..." if len(reason) > 60 else reason
            print(f"  {count:4d} | {display}")

    if stats.qualification_tiers:
        print("\nQualification by tier:")
        for tier, count in sorted(stats.qualification_tiers.items()):
            print(f"  {tier}: {count}")
    print("=" * 50)
```

### Anti-Patterns to Avoid

- **Logging every lead:** Will flood output - aggregate to counts instead
- **Storing full descriptions in stats:** Memory inefficient - store reason strings only
- **Modifying ScoringResult:** Keep it immutable, create new FilterStats
- **Complex confidence formulas:** Score is already meaningful, keep calculation simple
- **New file format for rejects:** Match existing labeled data schema for compatibility

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Counting rule hits | Dict with manual increment | `collections.Counter` | Returns 0 for missing keys, supports `.most_common()` |
| Dataclass to dict | Loop over fields | `dataclasses.asdict()` | Handles nested structures recursively |
| Sorting counts | Manual sorted() | `Counter.most_common(n)` | Built-in, returns top n tuples |
| JSON serialization | String formatting | `json.dump()` | Handles escaping, encoding |
| File path handling | String concatenation | `pathlib.Path` | Already used in project |

**Key insight:** Phase 3 established ScoringResult with reasons tracking. Statistics collection extends this naturally - the data is already being captured, we just need to aggregate it.

## Common Pitfalls

### Pitfall 1: Memory Bloat from Full Lead Storage

**What goes wrong:** Storing full job descriptions for all rejected leads causes memory issues.

**Why it happens:** Rejected leads may be 90%+ of input, descriptions are large strings.

**How to avoid:**
- Limit rejected export to configurable sample size (e.g., 100 per run)
- Store only metadata (id, company, title) plus first N chars of description
- Or export to file incrementally during processing

**Warning signs:** Memory usage grows linearly with job count, process killed.

### Pitfall 2: Statistics Lost on Early Exit

**What goes wrong:** If scraper fails mid-run, no statistics are logged.

**Why it happens:** Stats printed only at end of main().

**How to avoid:**
- Log intermediate stats periodically (every 100 jobs)
- Or accept this limitation for v1 (small data volumes)

**Warning signs:** Runs that error produce no useful diagnostics.

### Pitfall 3: Confidence Score Misinterpretation

**What goes wrong:** Users interpret confidence as probability, expect 0-1 range.

**Why it happens:** "Confidence" implies statistical meaning.

**How to avoid:**
- Document that confidence is score-based, not probabilistic
- Use "score" column name instead of "confidence" if unclear
- Scale is 0-100 where 50 = threshold, 100 = strong match

**Warning signs:** User feedback asking about model, probability calibration.

### Pitfall 4: JSON Schema Drift from Labeled Data

**What goes wrong:** Rejected export format doesn't match labeled data schema.

**Why it happens:** Schema defined implicitly in golden-test-set.json.

**How to avoid:**
- Reference golden-test-set.json schema explicitly
- Required fields: id, description, label
- Optional fields: company, title, notes, category

**Warning signs:** import errors when loading rejected exports for labeling.

### Pitfall 5: Stats Counter Key Explosion

**What goes wrong:** Reason strings have variable formatting, creating many unique keys.

**Why it happens:** Pattern like `"Company 'Boeing Defense' in blocklist (boeing)"` - company name varies.

**How to avoid:**
- Use normalized reason categories, not full reason strings
- e.g., "company_blocklist" not the full message

**Warning signs:** Stats show hundreds of unique reasons, most with count=1.

## Code Examples

Verified patterns from official sources and project analysis:

### Counter Usage for Statistics
```python
# Source: Python stdlib collections documentation
from collections import Counter

# Efficient counting
c = Counter()
for item in items:
    c[item["category"]] += 1

# Top N most common
for category, count in c.most_common(5):
    print(f"{category}: {count}")

# Missing keys return 0 (no KeyError)
print(c["nonexistent"])  # 0

# Arithmetic operations
c1 = Counter(a=3, b=1)
c2 = Counter(a=1, b=2)
c1 + c2  # Counter({'a': 4, 'b': 3})
```

### Dataclass to JSON via asdict
```python
# Source: Python stdlib dataclasses documentation
from dataclasses import dataclass, field, asdict
import json

@dataclass
class Lead:
    id: str
    description: str
    label: bool = False
    company: str = None

# Convert to dict, then JSON
lead = Lead("lead_001", "Job description...", company="SolarCo")
lead_dict = asdict(lead)
json_str = json.dumps(lead_dict, indent=2)

# For list of dataclasses
leads = [lead1, lead2, lead3]
json.dump([asdict(l) for l in leads], file, indent=2)
```

### FilterStats Dataclass with Counter
```python
# Source: Combination of dataclasses and Counter patterns
from dataclasses import dataclass, field
from collections import Counter

@dataclass
class FilterStats:
    """Statistics collected during a filter run."""
    total_processed: int = 0
    total_qualified: int = 0
    total_rejected: int = 0
    rejection_categories: Counter = field(default_factory=Counter)
    qualification_tiers: Counter = field(default_factory=Counter)
    company_blocked: int = 0

    def add_qualified(self, tier: str) -> None:
        self.total_processed += 1
        self.total_qualified += 1
        self.qualification_tiers[tier] += 1

    def add_rejected(self, category: str, is_company_blocked: bool = False) -> None:
        self.total_processed += 1
        self.total_rejected += 1
        self.rejection_categories[category] += 1
        if is_company_blocked:
            self.company_blocked += 1

    @property
    def pass_rate(self) -> float:
        if self.total_processed == 0:
            return 0.0
        return self.total_qualified / self.total_processed
```

### Confidence Score in CSV Output
```python
# Source: pandas CSV output pattern (already in scraper.py)
def process_jobs(df: pd.DataFrame, scoring_results: dict) -> pd.DataFrame:
    """Process jobs with confidence scores."""
    # ... existing processing ...

    # Add confidence score for qualified leads
    def get_confidence(row):
        result = scoring_results.get(row.name)  # or by company/job_url
        if result and result.qualified:
            return min(100.0, result.score)
        return None

    df['confidence_score'] = df.apply(get_confidence, axis=1)

    # Reorder columns to include confidence
    final_columns = [
        'company', 'domain', 'job_title', 'location',
        'confidence_score', 'posting_url', ...
    ]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No statistics | Per-rule statistics with Counter | This phase | Understanding filter behavior |
| No rejected export | JSON export matching labeled schema | This phase | Enables labeling workflow |
| No confidence in output | Score-based confidence in CSV | This phase | Prioritization of leads |
| Print-only logging | Print + aggregated stats | This phase | Actionable diagnostics |

**Deprecated/outdated:**
- Complex logging frameworks (overkill for CLI tool)
- Probabilistic confidence (requires ML, not available yet)
- Database storage for stats (CSV/JSON sufficient for batch use case)

## Open Questions

Things that couldn't be fully resolved:

1. **Rejected sample size**
   - What we know: Exporting all rejected leads may be thousands
   - What's unclear: Optimal sample size for labeling review
   - Recommendation: Make configurable, default to 100 (covers diverse cases)

2. **Confidence scale communication**
   - What we know: Score is 0-100+ where 50 is threshold
   - What's unclear: Whether users expect 0-1 probability
   - Recommendation: Use "score" column name, document in output

3. **Stats persistence across runs**
   - What we know: Each run produces independent stats
   - What's unclear: Whether to track trends across runs
   - Recommendation: Log to console per-run; trend tracking is v2 feature

4. **Rejection category normalization**
   - What we know: Full reason strings create many unique keys
   - What's unclear: Optimal categorization scheme
   - Recommendation: Map to config section names (e.g., "exclusions.installer", "company_blocklist")

## Sources

### Primary (HIGH confidence)
- [Python dataclasses documentation](https://docs.python.org/3/library/dataclasses.html) - asdict(), field(), default_factory
- [Python collections.Counter documentation](https://docs.python.org/3/library/collections.html) - Counter class, most_common()
- Current codebase analysis - scraper.py ScoringResult, evaluate.py, golden-test-set.json schema

### Secondary (MEDIUM confidence)
- [Real Python Counter Guide](https://realpython.com/python-counter/) - Counter patterns and best practices
- [Python Logging Best Practices](https://betterstack.com/community/guides/logging/python/python-logging-best-practices/) - Logging patterns (confirmed print() acceptable for CLI)
- [CleanLab Data Labeling](https://towardsdatascience.com/automatically-detecting-label-errors-in-datasets-with-cleanlab-e0a3ea5fb345/) - Exported data for labeling review patterns

### Tertiary (LOW confidence)
- [dataclasses-json PyPI](https://pypi.org/project/dataclasses-json/) - Third-party library (not recommended, stdlib sufficient)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib, patterns verified in official docs
- Architecture: HIGH - Extends existing Phase 3 patterns naturally
- Pitfalls: HIGH - Based on actual codebase analysis and common Python issues

**Research date:** 2026-01-18
**Valid until:** 2026-03-18 (60 days - stable patterns, no fast-moving dependencies)
