# ZipRecruiter Performance Analysis - 100% Description Extraction
**Date:** 2026-01-22
**Status:** ⚠️ Needs Optimization for Production

## Test Results

### Single Search Performance (100% Descriptions)

| Metric | Value |
|--------|-------|
| Jobs found | 100 |
| Descriptions | 100/100 (100%) |
| Duration | 518.0s (8.6 minutes) |
| Avg time per job | 5.2s |
| Avg time per description | ~2.0s |

### Breakdown
- Page navigation: ~30s (5 pages × 6s)
- Job extraction: ~50s (100 jobs × 0.5s)
- Description fetching: ~400s (100 descriptions × 4s)
- Popup dismissal overhead: ~38s

## Production Projection (65 search terms)

### Full 100% Description Extraction

| Configuration | Total Time | Within 6hr Limit? |
|--------------|------------|-------------------|
| 65 searches × 8.6 min | **557 minutes (9.3 hours)** | ❌ NO |

**Problem:** Exceeds GitHub Actions 6-hour (360 minute) limit by 197 minutes (3.3 hours).

### Alternative Configurations

#### Option 1: Reduce Pages (60% descriptions)
```python
max_pages=3  # 60 jobs per search
max_descriptions=60  # All jobs on 3 pages
```
- **Time per search**: ~310s (5.2 minutes)
- **Total time**: 338 minutes (5.6 hours) ✅ Within limit
- **Jobs**: 3,900 total (60 × 65)
- **Descriptions**: 3,900 (100% of scraped jobs)
- **Trade-off**: 40% fewer jobs but all have descriptions

#### Option 2: Selective Description Fetching (50% descriptions)
```python
max_pages=5  # 100 jobs per search
max_descriptions=50  # Only first 50 jobs
```
- **Time per search**: ~318s (5.3 minutes)
- **Total time**: 345 minutes (5.75 hours) ✅ Within limit
- **Jobs**: 6,500 total (100 × 65)
- **Descriptions**: 3,250 (50% of scraped jobs)
- **Trade-off**: All jobs but only half have descriptions

#### Option 3: Fast Mode - No Descriptions (0% descriptions)
```python
max_pages=5  # 100 jobs per search
max_descriptions=0  # No descriptions
```
- **Time per search**: ~120s (2 minutes)
- **Total time**: 130 minutes (2.2 hours) ✅ Fast
- **Jobs**: 6,500 total (100 × 65)
- **Descriptions**: 0 (0%)
- **Trade-off**: Maximum job volume, minimal time, but no descriptions

#### Option 4: Tiered Approach (80% descriptions)
```python
max_pages=5  # 100 jobs per search
max_descriptions=80  # First 80 jobs (4 pages worth)
```
- **Time per search**: ~430s (7.2 minutes)
- **Total time**: 468 minutes (7.8 hours) ❌ Over limit
- **Jobs**: 6,500 total
- **Descriptions**: 5,200 (80%)

## Recommendation Analysis

### Priority: Time vs Quality

**Question:** What matters more?
1. **Maximum job volume** → Option 3 (fast mode, no descriptions)
2. **100% description quality** → Option 1 (fewer jobs, all with descriptions)
3. **Balanced approach** → Option 2 (all jobs, 50% descriptions)

### Recommended: Option 2 (Balanced)

**Rationale:**
- ✅ Stays within 6-hour GitHub Actions limit
- ✅ Maintains 5-page scraping (100 jobs per search)
- ✅ Fetches descriptions for most relevant jobs (first 50)
- ✅ Provides good data quality without excessive time
- ✅ Can be adjusted easily if needed

**Configuration:**
```python
# camoufox_scraper.py, line 1245
jobs = await scrape_ziprecruiter_page(
    browser,
    term,
    debug_dir=debug_dir,
    max_pages=5,  # Scrape 5 pages (~100 jobs)
    max_descriptions=50  # Fetch descriptions for first 50 jobs (50% extraction)
)
```

## Comparison with Other Sites

| Site | Time/Search | Jobs/Search | Desc Rate | ROI (jobs/min) |
|------|------------|-------------|-----------|----------------|
| Indeed | 8.7s | 635.3 | ~80% | 4,377 |
| LinkedIn | 127.6s | 101.8 | ~90% | 48 |
| ZipRecruiter (Option 2) | 318s | 100 | 50% | 19 |
| ZipRecruiter (100% desc) | 518s | 100 | 100% | 12 |

**Analysis:**
- Option 2 provides 60% better ROI than 100% description mode
- Still slower than LinkedIn but comparable job volume
- 50% description rate is acceptable given quality of data

## Alternative Approach: Parallel Batch Processing

If we want 100% descriptions AND stay within time limits:

### Split into More Batches
Currently: 4 batches (16-17 searches each)
Proposed: 8 batches (8-9 searches each)

**Math:**
- 8 searches × 8.6 min = 69 minutes per batch
- With parallel execution: All batches complete in ~69 minutes ✅

**Changes Required:**
- Update `.github/workflows/scrape-leads.yml`
- Change batch matrix from `[0, 1, 2, 3]` to `[0, 1, 2, 3, 4, 5, 6, 7]`
- Update batch size calculation in `scraper.py`

**Trade-offs:**
- ✅ Achieves 100% description extraction
- ✅ Stays within 6-hour limit
- ➕ Better parallelization
- ➖ Uses more GitHub Actions compute minutes (cost)
- ➖ More complex merge logic

## Final Recommendation

### For Immediate Deployment: **Option 2** (50% Descriptions)

```python
max_pages=5
max_descriptions=50
```

**Why:**
- Minimal code change (just change one number)
- Stays within time limits
- Good balance of volume and quality
- Can be adjusted based on real production results

### For Future Enhancement: **8-Batch Parallel** (100% Descriptions)

After validating Option 2 works in production, consider implementing 8-batch parallelization to achieve 100% descriptions without exceeding time limits.

## Implementation Steps

1. **Update camoufox_scraper.py line 1245:**
   ```python
   max_descriptions=50  # Changed from 100
   ```

2. **Test locally:** Verify time is ~318s per search

3. **Deploy to GitHub Actions**

4. **Monitor first run:**
   - Check total run time (target: < 6 hours)
   - Verify description extraction rate (~50%)
   - Confirm no Cloudflare blocking

5. **Evaluate results:**
   - Are 50% descriptions sufficient for filtering?
   - Should we increase to 60-70 descriptions?
   - Or move to 8-batch parallel for 100%?

---

**Analysis By:** Claude Sonnet 4.5
**Date:** 2026-01-22
**Status:** Ready for Implementation
