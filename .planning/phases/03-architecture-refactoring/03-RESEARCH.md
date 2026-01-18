# Phase 3: Architecture Refactoring - Research

**Researched:** 2026-01-18
**Domain:** Python configuration externalization, weighted scoring systems
**Confidence:** HIGH

## Summary

This phase refactors the current boolean-based tiered filter in `scraper.py` into a weighted scoring system with externalized configuration. The current `description_matches()` function is ~150 lines of hardcoded term lists and boolean logic that returns `True/False`. The goal is to:

1. Extract all filter terms and weights to a JSON configuration file
2. Convert the boolean tier system to numeric weighted scoring
3. Separate company classification from role/description classification
4. Return a score with reasons instead of just a boolean

The research confirms this can be achieved using Python standard library only (no new dependencies needed). The approach uses `dataclass` for the return type (score + reasons), standard `json` module for configuration loading, and a simple weighted scoring algorithm that assigns points for positive signals and penalties for negative signals.

**Primary recommendation:** Use JSON for configuration (universal support, no YAML dependencies), Python dataclasses for result types (score, reasons), and a simple additive scoring model where each matched signal adds/subtracts points from a base score.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `json` | stdlib | Load JSON config files | Universal, zero dependencies, sufficient for this use case |
| `dataclasses` | stdlib | Return type for score+reasons | Python 3.7+ built-in, no validation overhead needed |
| `pathlib` | stdlib | Config file path handling | Already used in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typing` | stdlib | Type hints for config schema | Define expected structure |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSON | YAML | YAML requires `pyyaml` dependency, adds complexity. JSON is sufficient for term lists. |
| dataclass | Pydantic | Pydantic adds validation but requires new dependency. Dataclass is lightweight, already Python 3.13 compatible |
| dataclass | TypedDict | TypedDict better for external data, dataclass better for return values with methods |
| json stdlib | jsonschema | Schema validation is overkill for internal config - type hints + tests suffice |

**Installation:**
```bash
# No new dependencies required - all stdlib
```

## Architecture Patterns

### Recommended Project Structure
```
solar-lead-scraper/
├── scraper.py           # Main scraper, imports filter
├── evaluate.py          # Evaluation script (unchanged)
├── filter/              # NEW: Filter module
│   ├── __init__.py      # Exports score_job(), load_config()
│   ├── config.py        # Configuration loading/validation
│   ├── scorer.py        # Weighted scoring engine
│   └── types.py         # ScoringResult dataclass
└── config/              # NEW: External configuration
    └── filter-config.json
```

### Alternative: Simpler Flat Structure
```
solar-lead-scraper/
├── scraper.py           # Main scraper
├── evaluate.py          # Evaluation script
├── filter_config.py     # Configuration loading
├── filter_scorer.py     # Weighted scoring engine
└── config/
    └── filter-config.json
```

**Recommendation:** Use the simpler flat structure initially. The project is small (3 Python files), and a module hierarchy adds unnecessary complexity. Can refactor to modules later if the filter grows.

### Pattern 1: Additive Weighted Scoring

**What:** Each signal (positive or negative) contributes points to a running score. The final score is compared against a configurable threshold.

**When to use:** When signals are independent and cumulative (our case).

**Example:**
```python
# Source: Standard weighted scoring pattern
from dataclasses import dataclass, field

@dataclass
class ScoringResult:
    score: float
    qualified: bool
    reasons: list[str] = field(default_factory=list)
    company_score: float = 0.0
    role_score: float = 0.0

def score_job(description: str, company_name: str | None, config: dict) -> ScoringResult:
    """Score a job posting and return detailed results."""
    score = 0.0
    reasons = []

    # Check blocklist first (immediate disqualification)
    if company_name and is_blocked_company(company_name, config):
        return ScoringResult(
            score=-100.0,
            qualified=False,
            reasons=["Company in blocklist"],
            company_score=-100.0
        )

    # Add positive signals
    for signal in config["positive_signals"]:
        if signal["pattern"] in description.lower():
            score += signal["weight"]
            reasons.append(f"+{signal['weight']}: {signal['name']}")

    # Subtract negative signals
    for signal in config["negative_signals"]:
        if signal["pattern"] in description.lower():
            score -= signal["weight"]
            reasons.append(f"-{signal['weight']}: {signal['name']}")

    threshold = config.get("threshold", 50.0)
    return ScoringResult(
        score=score,
        qualified=score >= threshold,
        reasons=reasons
    )
```

### Pattern 2: Configuration Schema

**What:** JSON configuration with typed term lists, weights, and thresholds.

**When to use:** Externalizing filter rules.

**Example:**
```json
{
  "version": "1.0",
  "threshold": 50.0,

  "company_blocklist": [
    "boeing", "spacex", "intel", "nvidia"
  ],

  "required_context": {
    "patterns": ["solar", "pv", "photovoltaic"],
    "description": "Must have solar/PV context"
  },

  "positive_signals": [
    {
      "name": "tier1_tool",
      "patterns": ["helioscope", "aurora solar", "pvsyst"],
      "weight": 100,
      "description": "Solar-specific design tools auto-qualify"
    },
    {
      "name": "tier2_strong",
      "patterns": ["stringing diagram", "module layout", "permit set"],
      "weight": 60,
      "requires": "design_role",
      "description": "Strong solar CAD signals"
    }
  ],

  "negative_signals": [
    {
      "name": "tennis_context",
      "patterns": ["tennis", "racquet", "racket"],
      "weight": 100,
      "description": "Tennis stringing false positives"
    },
    {
      "name": "installer_role",
      "patterns": ["installer", "technician", "foreman"],
      "weight": 80,
      "description": "Field installation, not design"
    }
  ],

  "design_role_indicators": [
    "designer", "drafter", "draftsman", "cad "
  ]
}
```

### Pattern 3: Separate Company and Role Scoring

**What:** Calculate company score and role score independently, then combine.

**When to use:** When company and role have different signal types (ARCH-03 requirement).

**Example:**
```python
# Source: Separation of concerns pattern
def score_company(company_name: str | None, config: dict) -> tuple[float, list[str]]:
    """Score based on company signals only."""
    if not company_name:
        return (0.0, [])

    company_lower = company_name.lower()

    # Blocklist check
    for blocked in config["company_blocklist"]:
        if blocked in company_lower:
            return (-100.0, [f"Company '{company_name}' in blocklist"])

    # Positive company signals (e.g., known solar companies)
    score = 0.0
    reasons = []
    for signal in config.get("company_positive_signals", []):
        if signal["pattern"] in company_lower:
            score += signal["weight"]
            reasons.append(f"+{signal['weight']}: {signal['name']}")

    return (score, reasons)

def score_role(description: str, config: dict) -> tuple[float, list[str]]:
    """Score based on role/description signals only."""
    # ... role-specific scoring logic
```

### Anti-Patterns to Avoid

- **Hardcoded thresholds:** Always make thresholds configurable in the JSON file
- **Magic numbers:** Document what each weight value means
- **Nested conditionals:** Use flat signal lists instead of if/elif chains
- **Mixing concerns:** Keep company scoring separate from role scoring
- **Ignoring reasons:** Always track WHY a score was assigned for debugging

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON parsing | Custom parser | `json.load()` | Stdlib handles edge cases |
| Path handling | String concatenation | `pathlib.Path` | Cross-platform, already in project |
| Type safety | Manual checks | `dataclass` | Auto `__init__`, `__repr__`, type hints |
| Config validation | Custom validators | Type hints + tests | Simpler for internal config |
| Pattern matching | Manual loops | List comprehensions | More Pythonic, cleaner |

**Key insight:** This project already uses minimal dependencies. The architecture refactoring should maintain that simplicity - no need for Pydantic, jsonschema, or rule engine libraries for this scope.

## Common Pitfalls

### Pitfall 1: Config File Location Discovery

**What goes wrong:** Hardcoding config path breaks when running from different directories.

**Why it happens:** Relative paths resolve from CWD, not script location.

**How to avoid:**
```python
# WRONG
config_path = "config/filter-config.json"

# RIGHT
from pathlib import Path
CONFIG_DIR = Path(__file__).parent / "config"
config_path = CONFIG_DIR / "filter-config.json"
```

**Warning signs:** Tests pass locally but fail in CI, or config not found errors.

### Pitfall 2: Weight Scale Confusion

**What goes wrong:** Mixing percentage weights (0-100) with absolute points leads to unexpected scoring.

**Why it happens:** No clear documentation of weight scale.

**How to avoid:** Document weight scale in config file and validate on load:
```json
{
  "_meta": {
    "weight_scale": "0-100 points, threshold 50 means 50% confidence",
    "version": "1.0"
  }
}
```

**Warning signs:** Scores cluster unexpectedly, threshold doesn't behave as expected.

### Pitfall 3: Mutating Configuration

**What goes wrong:** Accidental modification of loaded config affects subsequent calls.

**Why it happens:** Python dicts are mutable, loaded once and reused.

**How to avoid:**
```python
# Option 1: Load fresh each call (simple, slight overhead)
def get_config() -> dict:
    return json.load(open(config_path))

# Option 2: Freeze config (use frozen dataclass or deepcopy)
import copy
_CONFIG = None
def get_config() -> dict:
    global _CONFIG
    if _CONFIG is None:
        with open(config_path) as f:
            _CONFIG = json.load(f)
    return copy.deepcopy(_CONFIG)
```

**Warning signs:** Tests interfere with each other, order-dependent failures.

### Pitfall 4: Backward Compatibility with evaluate.py

**What goes wrong:** Changing `description_matches()` signature breaks `evaluate.py`.

**Why it happens:** `evaluate.py` imports and calls `description_matches(description, company)`.

**How to avoid:** Keep the old function as a compatibility wrapper:
```python
def description_matches(description: str, company_name: str = None) -> bool:
    """Legacy wrapper for backward compatibility with evaluate.py."""
    result = score_job(description, company_name)
    return result.qualified
```

**Warning signs:** Evaluation script breaks after refactoring.

### Pitfall 5: Threshold Drift

**What goes wrong:** Threshold tuned on one dataset doesn't generalize.

**Why it happens:** Overfitting threshold to golden test set.

**How to avoid:**
- Use the existing evaluation infrastructure to validate threshold changes
- Document baseline metrics before and after threshold changes
- Keep threshold configurable so it can be adjusted without code changes

**Warning signs:** Perfect scores on test set but poor production performance.

## Code Examples

Verified patterns from research:

### Configuration Loading
```python
# Source: Python stdlib json module
import json
from pathlib import Path
from typing import Any

def load_filter_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load filter configuration from JSON file.

    Args:
        config_path: Path to config file. Defaults to config/filter-config.json
                     relative to this file's location.

    Returns:
        Configuration dictionary with signals, weights, and threshold.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        json.JSONDecodeError: If config file is invalid JSON.
    """
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "filter-config.json"

    with open(config_path, encoding="utf-8") as f:
        return json.load(f)
```

### ScoringResult Dataclass
```python
# Source: Python stdlib dataclasses
from dataclasses import dataclass, field

@dataclass
class ScoringResult:
    """Result of scoring a job posting.

    Attributes:
        score: Total numeric score (higher = better match)
        qualified: Whether score meets threshold
        reasons: List of human-readable scoring explanations
        company_score: Points from company-level signals
        role_score: Points from role/description signals
        threshold: The threshold used for qualification
    """
    score: float
    qualified: bool
    reasons: list[str] = field(default_factory=list)
    company_score: float = 0.0
    role_score: float = 0.0
    threshold: float = 50.0
```

### Pattern Matching Helper
```python
# Source: Standard Python pattern
def matches_any(text: str, patterns: list[str]) -> str | None:
    """Check if text contains any pattern, return first match or None."""
    text_lower = text.lower()
    for pattern in patterns:
        if pattern in text_lower:
            return pattern
    return None
```

### Backward-Compatible Wrapper
```python
# Source: Adapter pattern for backward compatibility
def description_matches(description: str, company_name: str = None) -> bool:
    """Check if job description matches solar design criteria.

    DEPRECATED: Use score_job() for detailed scoring.
    This wrapper maintains backward compatibility with evaluate.py.
    """
    result = score_job(description, company_name)
    return result.qualified
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Boolean filter | Weighted scoring | This refactor | Enables confidence levels, tunable thresholds |
| Hardcoded terms | External JSON config | This refactor | Non-developers can tune without code changes |
| Single `True/False` | Score + reasons | This refactor | Better debugging, audit trail |
| Monolithic function | Separated company/role | This refactor | Easier to test and extend |

**Deprecated/outdated:**
- Rule engine libraries (durable-rules, pyknow): Overkill for this use case
- YAML configuration: Adds PyYAML dependency unnecessarily
- Pydantic for config: Adds dependency, validation not needed for internal config

## Open Questions

Things that couldn't be fully resolved:

1. **Weight calibration methodology**
   - What we know: Weights should reflect relative importance of signals
   - What's unclear: Optimal weight values for each tier
   - Recommendation: Start with simple tier mapping (Tier 1 = 100, Tier 2 = 60, Tier 3 = 40, etc.) and tune based on evaluation metrics

2. **Threshold selection**
   - What we know: Need a threshold to convert score to qualified/not
   - What's unclear: Optimal threshold value
   - Recommendation: Start at 50 (midpoint), adjust based on precision/recall tradeoffs on golden test set

3. **Config file versioning**
   - What we know: Config changes may affect scoring behavior
   - What's unclear: Whether to version configs or rely on git history
   - Recommendation: Include version field in config, document in CHANGELOG

## Sources

### Primary (HIGH confidence)
- Python 3.13 stdlib documentation - json, dataclasses, pathlib modules
- Current codebase analysis - scraper.py, evaluate.py, CONVENTIONS.md, STACK.md

### Secondary (MEDIUM confidence)
- [Weighted Scoring Model: Guide for Developers](https://daily.dev/blog/weighted-scoring-model-guide-for-developers) - General weighted scoring patterns
- [Type Without Tears: 7 Patterns for Python Dataclass & TypedDict](https://medium.com/@sparknp1/type-without-tears-7-patterns-for-python-dataclass-typeddict-9efc0393740e) - Dataclass best practices
- [Best Practices for Python Configuration](https://toxigon.com/best-practices-for-python-configuration) - Config file patterns
- [JSON vs YAML vs TOML](https://jsonberry.com/blog/json-vs-yaml-vs-toml/) - Format comparison

### Tertiary (LOW confidence)
- [Python Rule Engines](https://www.nected.ai/us/blog-us/python-rule-engines-automate-and-enforce-with-python) - Rule engine overview (not recommended for this use case)
- [Rules Engine Design Patterns](https://www.nected.ai/us/blog-us/rules-engine-design-pattern) - General design patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib, well-documented patterns
- Architecture: HIGH - Simple flat structure matches existing codebase style
- Pitfalls: HIGH - Based on actual codebase analysis and common Python issues

**Research date:** 2026-01-18
**Valid until:** 2026-03-18 (60 days - stable patterns, no fast-moving dependencies)
