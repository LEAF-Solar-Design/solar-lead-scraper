# Testing Patterns

**Analysis Date:** 2025-01-18

## Test Framework

**Runner:**
- None configured

**Assertion Library:**
- None configured

**Run Commands:**
```bash
# No test commands available - no tests exist
```

## Test File Organization

**Location:**
- No test files present

**Naming:**
- Not established

**Structure:**
- Not established

## Current State

**No automated tests exist in this codebase.**

Files analyzed:
- `scraper.py` - 409 lines, 0 tests
- `upload_results.py` - 61 lines, 0 tests

## Recommended Test Setup

Based on the codebase structure, if tests were to be added:

**Suggested Framework:**
- pytest (standard for Python projects)
- pytest-mock for mocking

**Suggested Structure:**
```
tests/
├── __init__.py
├── test_scraper.py
├── test_upload.py
└── conftest.py        # Shared fixtures
```

**Priority Functions to Test:**

1. **`description_matches()`** in `scraper.py`
   - Most complex function (150+ lines)
   - Contains 6 tiers of filtering logic
   - High business value (determines lead quality)
   - Pure function, easy to test

2. **`clean_company_name()`** in `scraper.py`
   - Pure function
   - String transformation logic
   - Edge cases: empty string, special chars, various suffixes

3. **`guess_domain()`** in `scraper.py`
   - Pure function
   - Domain generation logic

4. **`generate_linkedin_*_url()`** functions in `scraper.py`
   - Pure functions
   - URL encoding logic

## Mocking

**Framework:**
- Not established

**What Would Need Mocking:**
- `jobspy.scrape_jobs()` - external API calls
- `requests.post()` - HTTP requests
- `os.environ.get()` - environment variables
- File system operations in `get_latest_csv()`

## Fixtures and Factories

**Test Data:**
- Not established

**Suggested Fixtures:**
```python
# Sample job descriptions for testing description_matches()
@pytest.fixture
def solar_designer_job():
    return """
    Solar Designer position using AutoCAD and Helioscope.
    Design residential solar PV systems...
    """

@pytest.fixture
def non_solar_job():
    return """
    Software Engineer position at tech company.
    Building web applications...
    """

# Sample DataFrames for testing process_jobs()
@pytest.fixture
def sample_jobs_df():
    return pd.DataFrame({
        'company': ['Solar Co', 'Energy Inc'],
        'title': ['Solar Designer', 'CAD Drafter'],
        'location': ['Austin, TX', 'Denver, CO'],
        'job_url': ['http://example.com/1', 'http://example.com/2'],
        'description': ['...', '...']
    })
```

## Coverage

**Requirements:** None enforced

**View Coverage:**
```bash
# Not configured
```

## Test Types

**Unit Tests:**
- Not present
- Would cover: `description_matches()`, `clean_company_name()`, `guess_domain()`, URL generators

**Integration Tests:**
- Not present
- Would cover: `scrape_solar_jobs()` with mocked API, `process_jobs()` pipeline

**E2E Tests:**
- Not present
- Would cover: Full scrape-to-upload flow with mocked externals

## Manual Testing

**Current Approach:**
- Run `python scraper.py` manually
- Review CSV output in `output/` directory
- Check GitHub Actions workflow results

## CI/CD Integration

**Current State:**
- GitHub Actions workflow exists (`.github/workflows/scrape-leads.yml`)
- No test step in pipeline
- Workflow runs scraper directly without validation

**Suggested Addition:**
```yaml
- name: Run tests
  run: |
    pip install pytest pytest-cov
    pytest tests/ -v --cov=. --cov-report=xml
```

## Common Test Patterns (Recommended)

**Testing `description_matches()`:**
```python
def test_description_matches_helioscope():
    """Tier 1: Solar-specific tools auto-qualify."""
    desc = "Use Helioscope for solar PV design"
    assert description_matches(desc) is True

def test_description_matches_excludes_tennis():
    """Tennis/racquet terms excluded."""
    desc = "Solar powered tennis court with PV"
    assert description_matches(desc) is False

def test_description_matches_excludes_space():
    """Space/satellite context excluded."""
    desc = "Solar panels for satellite spacecraft"
    assert description_matches(desc) is False
```

**Testing `clean_company_name()`:**
```python
@pytest.mark.parametrize("input,expected", [
    ("Acme Inc.", "Acme"),
    ("Solar Co LLC", "Solar Co"),
    ("Energy Corp", "Energy"),
    ("", ""),
    (None, ""),
])
def test_clean_company_name(input, expected):
    assert clean_company_name(input) == expected
```

**Async Testing:**
- Not applicable (no async code)

**Error Testing:**
```python
def test_upload_missing_url():
    """Raises ValueError when DASHBOARD_URL not set."""
    with pytest.raises(ValueError, match="DASHBOARD_URL"):
        upload_to_dashboard("test.csv")
```

---

*Testing analysis: 2025-01-18*
