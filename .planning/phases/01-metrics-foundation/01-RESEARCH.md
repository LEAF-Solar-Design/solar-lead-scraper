# Phase 1: Metrics Foundation - Research

**Researched:** 2026-01-18
**Domain:** Binary classification evaluation / precision-recall metrics
**Confidence:** HIGH

## Summary

Phase 1 establishes measurement infrastructure to track precision and recall before making any filter changes. This is a well-understood domain with established patterns in Python/scikit-learn.

The core deliverables are:
1. An **evaluation script** that loads labeled JSON files and computes precision/recall against the current `description_matches()` filter
2. A **golden test set** with known good/bad examples for regression testing
3. **Baseline documentation** capturing current filter performance (~3% precision expected)

**Primary recommendation:** Use scikit-learn's `precision_score`, `recall_score`, and `classification_report` functions. Keep the evaluation script simple and focused - no need for complex infrastructure. Store labeled data as JSON files with `{description, label, metadata}` structure.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | 1.5+ | Precision/recall/F1 metrics | Industry standard, already used in ML ecosystem |
| json | stdlib | Load labeled data files | Simple, human-readable, no dependencies |
| pandas | existing | Optional: DataFrame operations | Already in project, useful for analysis |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.0+ | Test runner for golden set | If integrating with CI/CD |
| tabulate | 0.9+ | Pretty-print metrics tables | Optional, for CLI output formatting |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| scikit-learn | Manual calculation | Reinventing the wheel, error-prone |
| JSON | CSV | JSON preserves structure better for multi-field records |
| JSON | SQLite | Overkill for <1000 records, adds complexity |

**Installation:**
```bash
pip install scikit-learn
# pandas already installed
# json is stdlib
```

## Architecture Patterns

### Recommended Project Structure
```
solar-lead-scraper/
  data/
    labeled/
      qualified-leads-2026-01-18.json    # Positive examples
      rejected-leads-2026-01-16.json     # Negative examples (used for analysis)
      rejected-leads-2026-01-17.json     # Negative examples (used for analysis)
    golden/
      golden-test-set.json               # Curated regression test set
  evaluate.py                            # Main evaluation script
  scraper.py                             # Existing (contains description_matches)
```

### Pattern 1: Labeled Data Schema
**What:** Consistent JSON structure for all labeled data
**When to use:** Always - standardize early to avoid migration pain

```json
{
  "metadata": {
    "created": "2026-01-18",
    "source": "manual_labeling",
    "labeler": "user",
    "criteria_version": "1.0"
  },
  "items": [
    {
      "id": "job_123",
      "description": "Solar Designer using Helioscope...",
      "label": true,
      "company": "SunPower",
      "title": "Solar Designer",
      "notes": "Clear solar design role with specific tools"
    }
  ]
}
```

**Key fields:**
- `label`: boolean (true = qualified, false = rejected)
- `description`: the text passed to `description_matches()`
- `id`: unique identifier for traceability
- Metadata enables auditing and criteria evolution tracking

### Pattern 2: Evaluation Script Structure
**What:** Standalone script that loads data, runs filter, computes metrics
**When to use:** Phase 1 - keep it simple

```python
# evaluate.py
"""
Evaluate filter precision/recall against labeled data.

Usage:
    python evaluate.py                    # Evaluate against all labeled data
    python evaluate.py --golden           # Evaluate against golden test set only
    python evaluate.py --file data.json   # Evaluate against specific file
"""

import json
import argparse
from pathlib import Path
from sklearn.metrics import precision_score, recall_score, f1_score, classification_report

from scraper import description_matches  # Import existing filter


def load_labeled_data(filepath: Path) -> list[dict]:
    """Load labeled items from JSON file."""
    with open(filepath) as f:
        data = json.load(f)
    return data.get("items", data)  # Handle both wrapped and raw formats


def evaluate(items: list[dict]) -> dict:
    """Run filter against labeled items, return metrics."""
    y_true = []
    y_pred = []

    for item in items:
        y_true.append(item["label"])
        y_pred.append(description_matches(item["description"]))

    return {
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "total": len(items),
        "positives": sum(y_true),
        "negatives": len(y_true) - sum(y_true),
        "true_positives": sum(1 for t, p in zip(y_true, y_pred) if t and p),
        "false_positives": sum(1 for t, p in zip(y_true, y_pred) if not t and p),
        "false_negatives": sum(1 for t, p in zip(y_true, y_pred) if t and not p),
        "true_negatives": sum(1 for t, p in zip(y_true, y_pred) if not t and not p),
    }
```

### Pattern 3: Golden Test Set Design
**What:** Curated subset of labeled data for regression testing
**When to use:** Before any filter changes

**Golden set characteristics:**
- **Size:** 50-100 items (per industry best practices)
- **Balance:** Include both positives AND negatives
- **Coverage:** Include edge cases and known tricky examples
- **Stability:** Rarely changed, version controlled
- **Documentation:** Each item has notes explaining why it's included

```json
{
  "metadata": {
    "created": "2026-01-18",
    "purpose": "regression_testing",
    "criteria_version": "1.0"
  },
  "items": [
    {
      "id": "golden_pos_01",
      "description": "Solar Designer using Helioscope and Aurora Solar...",
      "label": true,
      "category": "tier1_tool_match",
      "notes": "Clear positive - mentions solar-specific design tools"
    },
    {
      "id": "golden_neg_01",
      "description": "Tennis racquet stringing technician...",
      "label": false,
      "category": "false_positive_tennis",
      "notes": "Known false positive pattern - stringing term in non-solar context"
    }
  ]
}
```

### Anti-Patterns to Avoid
- **Over-engineering:** Don't build a database, web UI, or complex infrastructure for <1000 records
- **Mixing labeled data formats:** Standardize JSON schema from day one
- **Evaluating without baseline:** Document current performance BEFORE making changes
- **Golden set drift:** Don't continuously modify the golden set; refresh periodically with new version
- **Accuracy as primary metric:** Use precision/recall for imbalanced data (3% positive rate)

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Precision/recall calculation | Manual TP/FP counting | `sklearn.metrics.precision_score` | Edge cases (zero division), tested, standard |
| Classification report | Custom formatting | `sklearn.metrics.classification_report` | Comprehensive output, industry standard |
| F1 score | `2*p*r/(p+r)` manually | `sklearn.metrics.f1_score` | Handles edge cases, consistent with sklearn |
| JSON loading | Custom parser | `json.load()` | Standard library, battle-tested |
| Metric aggregation | Custom dict building | `precision_recall_fscore_support` | All metrics in one call |

**Key insight:** scikit-learn's metrics module is mature and handles edge cases (zero division, empty arrays, class imbalance) that manual implementations miss.

## Common Pitfalls

### Pitfall 1: Using Accuracy Instead of Precision/Recall
**What goes wrong:** With 3% positive rate, accuracy of 97% is achieved by predicting "not qualified" for everything
**Why it happens:** Accuracy is the default metric people reach for
**How to avoid:** Always report precision AND recall; use F1 for single-number summary
**Warning signs:** High accuracy (>90%) but no qualified leads found

### Pitfall 2: Evaluating Without Documented Labeling Criteria
**What goes wrong:** Labels are inconsistent, metrics are meaningless
**Why it happens:** "I know a good lead when I see it" approach
**How to avoid:** Document explicit criteria BEFORE labeling; include in metadata
**Warning signs:** Disagreement on edge cases, changing labels over time

### Pitfall 3: Golden Set Contamination
**What goes wrong:** Golden set overlaps with data used for filter tuning
**Why it happens:** Convenience - using same data for development and testing
**How to avoid:** Separate golden set from development labeled data; never tune on golden set
**Warning signs:** Perfect golden set performance, poor production performance

### Pitfall 4: Forgetting to Track Recall
**What goes wrong:** Adding exclusions improves precision but kills recall (good leads filtered out)
**Why it happens:** False positives are visible; false negatives are invisible
**How to avoid:** Always measure BOTH metrics; require recall check before adding exclusions
**Warning signs:** Precision improving but lead volume dropping significantly

### Pitfall 5: Inconsistent Test Data Format
**What goes wrong:** Different JSON structures across files, breaking evaluation script
**Why it happens:** Schema not defined upfront, organic growth
**How to avoid:** Define schema in Phase 1, validate all loaded files
**Warning signs:** KeyError exceptions, missing fields

## Code Examples

Verified patterns from official sources:

### Computing Precision and Recall
```python
# Source: sklearn documentation
from sklearn.metrics import precision_score, recall_score, f1_score

y_true = [True, False, True, True, False, False, True, False]
y_pred = [True, False, False, True, False, True, True, False]

precision = precision_score(y_true, y_pred)  # 0.75
recall = recall_score(y_true, y_pred)        # 0.75
f1 = f1_score(y_true, y_pred)                # 0.75
```

### Classification Report
```python
# Source: sklearn documentation
from sklearn.metrics import classification_report

y_true = [True, False, True, True, False, False, True, False]
y_pred = [True, False, False, True, False, True, True, False]

print(classification_report(
    y_true,
    y_pred,
    target_names=["rejected", "qualified"]
))

# Output:
#               precision    recall  f1-score   support
#     rejected       0.80      0.80      0.80         5
#    qualified       0.75      0.75      0.75         4
#     accuracy                           0.78         9
#    macro avg       0.77      0.77      0.77         9
# weighted avg       0.78      0.78      0.78         9
```

### Getting All Metrics at Once
```python
# Source: sklearn documentation
from sklearn.metrics import precision_recall_fscore_support

precision, recall, f1, support = precision_recall_fscore_support(
    y_true, y_pred, average='binary', pos_label=True
)
```

### Loading and Validating Labeled Data
```python
# Pattern for consistent data loading
import json
from pathlib import Path

def load_labeled_data(filepath: Path) -> list[dict]:
    """Load and validate labeled data from JSON."""
    with open(filepath) as f:
        data = json.load(f)

    items = data.get("items", data)  # Handle wrapped or raw format

    # Validate required fields
    for i, item in enumerate(items):
        if "description" not in item:
            raise ValueError(f"Item {i} missing 'description' field")
        if "label" not in item:
            raise ValueError(f"Item {i} missing 'label' field")
        if not isinstance(item["label"], bool):
            raise ValueError(f"Item {i} 'label' must be boolean, got {type(item['label'])}")

    return items
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual TP/FP counting | sklearn metrics functions | Stable since sklearn 0.x | Standardized, handles edge cases |
| Accuracy for imbalanced | Precision/recall/F1 | Best practice for 10+ years | Meaningful metrics for imbalanced data |
| Ad-hoc test data | Golden test sets | ML ops maturation ~2020 | Reproducible evaluation, regression detection |

**Deprecated/outdated:**
- Using accuracy alone for imbalanced classification (misleading)
- Hardcoded expected values instead of systematic evaluation (brittle)

## Open Questions

Things that couldn't be fully resolved:

1. **Existing labeled data format**
   - What we know: Files mentioned in PROJECT.md (`rejected-leads-2026-01-16.json`, etc.)
   - What's unclear: Exact schema of these files, whether they include description text
   - Recommendation: Check if files exist and their format; may need to recreate or transform

2. **Recall baseline calculation**
   - What we know: Need qualified examples to measure recall
   - What's unclear: With only 16 qualified examples, is that enough for meaningful recall?
   - Recommendation: Use what we have; note sample size limitation in baseline doc

3. **Labeling criteria documentation**
   - What we know: Implicit criteria exist (design roles at solar companies)
   - What's unclear: Exact boundaries (is a CAD job at a diversified company qualified?)
   - Recommendation: Document criteria as part of Phase 1 before further labeling

## Sources

### Primary (HIGH confidence)
- [scikit-learn metrics documentation](https://scikit-learn.org/stable/modules/model_evaluation.html) - precision_score, recall_score, f1_score, classification_report APIs
- [scikit-learn Precision-Recall tutorial](https://scikit-learn.org/stable/auto_examples/model_selection/plot_precision_recall.html) - best practices for imbalanced classification
- [Google ML Crash Course: Classification metrics](https://developers.google.com/machine-learning/crash-course/classification/accuracy-precision-recall) - when to use precision vs recall

### Secondary (MEDIUM confidence)
- [Golden Datasets: Foundation of Reliable AI Evaluation](https://medium.com/@federicomoreno613/golden-datasets-the-foundation-of-reliable-ai-evaluation-486ce97ce89d) - golden test set design principles
- [Evaluating models with golden sets](https://www.sachith.co.uk/evaluating-models-with-golden-sets-performance-tuning-guide-practical-guide-dec-6-2025/) - practical guide for golden set construction
- [Building a Golden Dataset for AI Evaluation](https://www.getmaxim.ai/articles/building-a-golden-dataset-for-ai-evaluation-a-step-by-step-guide/) - step-by-step methodology

### Tertiary (LOW confidence)
- Training data knowledge on Python evaluation script patterns (needs validation against current best practices)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - scikit-learn is undisputed standard for this use case
- Architecture: HIGH - JSON + Python script is well-established pattern
- Pitfalls: HIGH - documented extensively in ML evaluation literature

**Research date:** 2026-01-18
**Valid until:** 6 months (stable domain, unlikely to change)

---

*Research completed: 2026-01-18*
*Ready for planning: yes*
