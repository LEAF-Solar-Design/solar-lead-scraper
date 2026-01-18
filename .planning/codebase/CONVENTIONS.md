# Coding Conventions

**Analysis Date:** 2025-01-18

## Naming Patterns

**Files:**
- Snake_case for Python files: `scraper.py`, `upload_results.py`
- All lowercase, underscores for word separation

**Functions:**
- Snake_case: `scrape_solar_jobs()`, `process_jobs()`, `get_latest_csv()`
- Verb-first naming: `generate_*`, `scrape_*`, `upload_*`, `clean_*`, `guess_*`
- Boolean-returning functions use verb phrases: `description_matches()`

**Variables:**
- Snake_case: `all_jobs`, `csv_content`, `search_terms`
- Descriptive names preferred: `results_per_term`, `before_filter`
- Single-letter only for iteration: `df`, `f`, `e`

**Constants:**
- Inline lists, not module-level constants
- Term lists defined within functions: `tennis_terms`, `space_terms`, `installer_terms`

**Types:**
- Type hints used for function signatures: `def clean_company_name(name: str) -> str:`
- Return type annotations present on all functions
- pandas DataFrame typed as `pd.DataFrame`

## Code Style

**Formatting:**
- No formal formatter configured (no `.prettierrc`, `black.toml`, etc.)
- 4-space indentation (Python standard)
- Line length varies, some lines exceed 120 characters

**Linting:**
- No linter configured (no `.flake8`, `pylintrc`, `ruff.toml`)
- Manual code review only

**Imports:**
- Standard library first
- Third-party packages second
- No blank lines between import groups
- Example from `scraper.py`:
```python
import re
import urllib.parse
from datetime import datetime
from pathlib import Path

import pandas as pd
from jobspy import scrape_jobs
```

## Import Organization

**Order:**
1. Standard library imports (`re`, `urllib.parse`, `datetime`, `pathlib`, `os`, `glob`)
2. Third-party imports (`pandas`, `jobspy`, `requests`)
3. No local imports (flat project structure)

**Path Aliases:**
- None configured

## Error Handling

**Patterns:**
- Try/except blocks with generic Exception catching
- Print error message and continue for non-critical failures
- Raise exceptions for critical failures (missing env vars, upload failures)

**Example from `scraper.py`:**
```python
try:
    jobs = scrape_jobs(...)
    if not jobs.empty:
        jobs['search_term'] = term
        all_jobs.append(jobs)
        print(f"  Found {len(jobs)} jobs")
except Exception as e:
    print(f"  Error searching '{term}': {e}")
```

**Example from `upload_results.py`:**
```python
if not dashboard_url:
    raise ValueError("DASHBOARD_URL environment variable not set")
```

**Critical vs Non-Critical:**
- Non-critical: Individual search term failures (logged, continue)
- Critical: Missing env vars, upload failures (raise Exception)

## Logging

**Framework:** `print()` statements (no logging library)

**Patterns:**
- Progress indicators: `print(f"Searching for: {term}")`
- Results summaries: `print(f"Total jobs found: {len(df)}")`
- Error messages: `print(f"  Error searching '{term}': {e}")`
- Section dividers: `print("=" * 50)`

**No log levels** - all output goes to stdout

## Comments

**When to Comment:**
- Module docstrings present at file top
- Function docstrings for all functions (single-line, triple quotes)
- Inline comments for logic explanation (e.g., tier explanations in filter)

**Docstring Style:**
```python
def clean_company_name(name: str) -> str:
    """Clean company name for domain guessing."""
```

**Inline Comments:**
```python
# TIER 1: Solar-specific design software (auto-qualify - these are ONLY used for solar design)
# TIER 2: Strong technical signals that are specific to solar CAD work
```

## Function Design

**Size:**
- Most functions under 30 lines
- One exception: `description_matches()` at ~150 lines (complex filtering logic)

**Parameters:**
- Simple types preferred (str, pd.DataFrame)
- Optional parameters have defaults: `job_title: str = None`

**Return Values:**
- Return type always annotated
- Empty DataFrame returned for no-results case
- Boolean for predicate functions

## Module Design

**Exports:**
- No `__all__` defined
- Functions defined at module level
- Main entry point via `if __name__ == "__main__":` pattern

**Barrel Files:**
- Not used (flat structure, only 2 Python files)

## Data Handling

**DataFrame Operations:**
- Method chaining on DataFrames
- Column existence checks before access: `if 'description' in df.columns:`
- Copy created before modifications: `df = df[available_cols].copy()`

**String Operations:**
- f-strings for all string formatting
- `re` module for regex operations
- `.lower()` for case-insensitive comparisons

## Configuration

**Environment Variables:**
- Accessed via `os.environ.get()` with explicit None check
- Required vars: `DASHBOARD_URL`, `DASHBOARD_API_KEY`
- No default values for secrets

**Hardcoded Values:**
- Search terms list in `scraper.py`
- Filter term lists in `description_matches()`
- Results limit: `results_per_term = 1000`

---

*Convention analysis: 2025-01-18*
