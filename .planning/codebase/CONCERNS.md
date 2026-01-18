# Codebase Concerns

**Analysis Date:** 2025-01-18

## Tech Debt

**Monolithic description_matches function:**
- Issue: Single 150-line function (`description_matches`) with hardcoded filter lists spanning lines 71-221
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/scraper.py`
- Impact: Difficult to maintain and test; any filter change requires editing the function body
- Fix approach: Extract filter term lists to configuration (JSON/YAML) or constants module; break into smaller composable filter functions

**Hardcoded search terms:**
- Issue: 37 search terms hardcoded in `scrape_solar_jobs` function (lines 229-287)
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/scraper.py`
- Impact: Requires code change to modify search strategy; recent commits show frequent search term iteration
- Fix approach: Move search terms to external config file that can be modified without code changes

**Missing dependency versioning:**
- Issue: `requirements.txt` has no version pins (`python-jobspy`, `pandas`)
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/requirements.txt`
- Impact: Builds may break when dependencies update; no reproducibility guarantee
- Fix approach: Pin exact versions (e.g., `pandas==2.1.0`) or use version ranges

**requests not in requirements.txt:**
- Issue: `upload_results.py` imports `requests` but it is not in `requirements.txt`
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/requirements.txt`, `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/upload_results.py`
- Impact: Local runs fail without manually installing requests; CI workflow has workaround (`pip install requests` on line 29)
- Fix approach: Add `requests` to `requirements.txt`

## Known Bugs

**Silent failure on missing description column:**
- Symptoms: If job board returns data without `description` column, no filtering occurs
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/scraper.py` (lines 318-323)
- Trigger: Job board API changes or returns partial data
- Workaround: Warning is printed but unfiltered data proceeds to output

**Domain guessing always assumes .com:**
- Symptoms: `guess_domain` returns incorrect domain for non-.com companies
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/scraper.py` (lines 61-68)
- Trigger: Any company with .net, .org, .io, or international TLD
- Workaround: None; domain column will have wrong values

## Security Considerations

**API key exposure in error output:**
- Risk: If upload fails, response body is printed which could contain sensitive data
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/upload_results.py` (line 50)
- Current mitigation: Secrets stored in GitHub Actions secrets
- Recommendations: Sanitize error output; consider structured logging

**No request timeout on dashboard upload:**
- Risk: `requests.post` call has no timeout; can hang indefinitely
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/upload_results.py` (line 42)
- Current mitigation: None
- Recommendations: Add `timeout=30` parameter to requests call

**No HTTPS verification disabled - GOOD:**
- Current state: No `verify=False` found; SSL verification is default enabled

## Performance Bottlenecks

**Sequential search term iteration:**
- Problem: Each of 37 search terms runs sequentially; no parallelization
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/scraper.py` (lines 292-307)
- Cause: Simple for-loop over search terms with 1000 results each
- Improvement path: Use `concurrent.futures.ThreadPoolExecutor` for parallel scraping

**Large results_per_term value:**
- Problem: Requesting 1000 results per search term creates large dataset before filtering
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/scraper.py` (line 290)
- Cause: Wide net strategy with aggressive filtering
- Improvement path: Consider reducing per-term results or implementing incremental filtering

**In-memory DataFrame operations on large dataset:**
- Problem: All jobs concatenated in memory before filtering
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/scraper.py` (line 314)
- Cause: `pd.concat(all_jobs)` creates full copy
- Improvement path: Filter each batch before concatenating; use chunked processing

## Fragile Areas

**Filter logic in description_matches:**
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/scraper.py` (lines 71-221)
- Why fragile: 6-tier filtering with string matching; order matters; easy to introduce false positives/negatives
- Safe modification: Test filter changes with sample data before deploying; add unit tests for edge cases
- Test coverage: Zero automated tests

**LinkedIn URL generation:**
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/scraper.py` (lines 15-47)
- Why fragile: Google search URL format and LinkedIn URL patterns may change
- Safe modification: Verify URLs work manually after changes
- Test coverage: No automated tests

**External dependency on python-jobspy:**
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/scraper.py` (line 12)
- Why fragile: Third-party library scrapes job sites; site changes break scraper
- Safe modification: Monitor for library updates; have fallback strategy
- Test coverage: Cannot be mocked without significant refactoring

## Scaling Limits

**GitHub Actions runtime:**
- Current capacity: Runs on schedule, processes 37 search terms
- Limit: GitHub Actions has 6-hour job timeout; current approach linear in search terms
- Scaling path: Parallelize within job; split into multiple workflow jobs

**Memory usage:**
- Current capacity: Handles thousands of job listings
- Limit: All results held in memory; will OOM on very large result sets
- Scaling path: Stream results to disk; process in batches

## Dependencies at Risk

**python-jobspy:**
- Risk: Unofficial scraping library; could break with site changes or cease maintenance
- Impact: Core scraping functionality depends entirely on this library
- Migration plan: Build direct API integration with job boards; implement fallback scraper

**pandas:**
- Risk: Low; stable well-maintained library
- Impact: Data processing depends on it
- Migration plan: N/A - appropriate choice

## Missing Critical Features

**No retry logic:**
- Problem: Network failures during scraping cause term to be skipped
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/scraper.py` (lines 294-307)
- Blocks: Reliable data collection; silent data loss on transient failures

**No deduplication across runs:**
- Problem: Each run produces independent CSV; no tracking of previously seen companies
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/scraper.py` (line 343)
- Blocks: Incremental lead discovery; causes duplicate uploads to dashboard

**No logging framework:**
- Problem: All output via `print()` statements; no log levels, timestamps, or structured output
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/scraper.py`, `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/upload_results.py`
- Blocks: Production debugging; log aggregation; alerting

**No configuration management:**
- Problem: All settings hardcoded (search terms, filter lists, results count)
- Files: `c:/Users/ehaug/OneDrive/Documents/GitHub/solar-lead-scraper/scraper.py`
- Blocks: Environment-specific configuration; A/B testing of filters

## Test Coverage Gaps

**Zero test files exist:**
- What's not tested: Everything - no test files found in repository
- Files: All Python files lack corresponding test files
- Risk: Filter changes can introduce false positives/negatives undetected; refactoring unsafe
- Priority: High - filter logic is complex and frequently modified (see commit history)

**Critical untested areas:**
1. `description_matches()` - complex 6-tier filtering logic
2. `clean_company_name()` - regex transformations
3. `guess_domain()` - domain inference
4. LinkedIn URL generation functions - URL encoding

---

*Concerns audit: 2025-01-18*
