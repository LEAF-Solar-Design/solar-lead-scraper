# Issues To Address

Production issues that should be fixed. Ordered by severity.

---

## CRITICAL

### 1. ~~Unhandled Exception in CSV Upload~~ FIXED
- **File:** [upload_results.py:557-563](upload_results.py#L557-L563)
- **Fix:** Added broader exception handling around `upload_to_dashboard()`

### 2. ~~Non-Deterministic Deduplication in Merge~~ FIXED
- **File:** [.github/workflows/scrape-leads.yml:160-161](.github/workflows/scrape-leads.yml#L160-L161)
- **Fix:** Sort by confidence_score (descending) before deduplication to keep highest-confidence occurrence

### 3. ~~Batch Output Filename Collisions~~ FIXED
- **File:** [scraper.py:1694](scraper.py#L1694)
- **Fix:** Include batch number in filename: `solar_leads_{timestamp}_batch{batch}.csv`

---

## HIGH

### 4. ~~JSON Parsing Without Error Handling~~ FIXED
- **File:** [upload_results.py](upload_results.py)
- **Fix:** Added try-except around all json.load() calls in merge functions

### 5. ~~Division by Zero Vulnerabilities~~ VERIFIED OK
- Already had guards in place (`if x > 0 else 0`)

### 6. ~~Missing API Response Validation~~ FIXED
- **File:** [upload_results.py:60-62](upload_results.py#L60-L62)
- **Fix:** Added try-except for JSONDecodeError on response.json()

### 7. ~~Confidence Score Index Mismatch After Dedup~~ VERIFIED OK
- Code correctly preserves indices through filtering; confidence is mapped before dedup

---

## MEDIUM

### 8. ~~Missing Filter Config Schema Validation~~ FIXED
- **File:** [scraper.py:541-570](scraper.py#L541-L570)
- **Fix:** Added validation for required keys and required_context.patterns

### 9. ~~Incomplete Error Categorization~~ FIXED
- **File:** [scraper.py:932-967](scraper.py#L932-L967)
- **Fix:** Added all exclusion categories from filter-config.json

### 10. ~~Test Coverage Gaps~~ FIXED
- **File:** [tests/test_edge_cases.py](tests/test_edge_cases.py)
- **Fix:** Added 20 new edge case tests covering None values, empty inputs, config validation, etc.

---

## Additional Fixes Made

- Fixed `pd.NA` handling in `score_role()` which caused TypeError
- Fixed categorize_rejection matching "cto" substring in "semiconductor"

---

*All issues resolved: 2025-01-23*
