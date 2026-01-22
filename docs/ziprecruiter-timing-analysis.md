# ZipRecruiter Description Fetching - Timing Analysis
**Date:** 2026-01-22
**Goal:** Identify bottlenecks and optimize to achieve 100 descriptions in < 6 hours total runtime

## Current Performance Breakdown

### Test Results (1 search, 100 jobs, 100 descriptions)
- **Total time:** 518 seconds (8.6 minutes)
- **Jobs found:** 100
- **Descriptions fetched:** 100 (100%)

### Time Allocation Analysis

**Per-Description Operations:**
1. `await card.click(timeout=5000)` - Click job card
   - Normal click attempt: 100-500ms
   - Fallback force click: 500-1000ms if first fails
   - **Estimated:** ~300-500ms average

2. `await page.wait_for_timeout(1500)` - Wait for panel to load
   - **Fixed delay:** 1,500ms
   - **This is the biggest bottleneck!**

3. `await dismiss_popups(page)` - Dismiss any popups
   - Usually quick: 50-200ms
   - **Estimated:** ~100ms average

4. `await page.evaluate(...)` - Extract description from DOM
   - JavaScript execution: 50-100ms
   - **Estimated:** ~75ms average

5. `await page.wait_for_timeout(300)` - Small delay between clicks
   - **Fixed delay:** 300ms

**Total per description (current):**
- Click: 400ms
- Wait for panel: **1,500ms** ← BOTTLENECK
- Dismiss popups: 100ms
- Extract: 75ms
- Post-click delay: 300ms
- **Total: ~2,375ms per description**

**Calculated time for 100 descriptions:**
- 100 × 2.375s = 237.5 seconds (4 minutes just for descriptions)
- Plus page navigation: ~30s
- Plus job extraction: ~50s
- Plus other overhead: ~200s
- **Expected total: ~517s** ✓ (Matches actual 518s)

## Optimization Opportunities

### 1. Reduce Panel Load Wait Time (HIGHEST IMPACT)
**Current:** 1,500ms fixed wait
**Optimization:** Use intelligent waiting with shorter timeout

```python
# Instead of:
await page.wait_for_timeout(1500)

# Use:
await page.wait_for_timeout(800)  # Reduced from 1500ms
```

**Why this works:**
- Panel usually loads in 500-800ms
- 1,500ms is overly conservative
- If description extraction fails, we already handle it gracefully

**Impact:**
- Save 700ms per description
- 100 descriptions × 700ms = **70 seconds saved**
- New time: 518s - 70s = **448s (7.5 minutes)**

### 2. Reduce Post-Click Delay (MEDIUM IMPACT)
**Current:** 300ms between each description fetch
**Optimization:** Reduce to 100ms or remove entirely

```python
# Instead of:
await page.wait_for_timeout(300)

# Use:
await page.wait_for_timeout(100)  # or 0
```

**Impact:**
- Save 200ms per description
- 100 descriptions × 200ms = **20 seconds saved**
- New time: 448s - 20s = **428s (7.1 minutes)**

### 3. Optimize Popup Dismissal (LOW-MEDIUM IMPACT)
**Current:** Call `dismiss_popups()` after every click
**Optimization:** Only dismiss popups periodically (every 5 clicks)

```python
if i % 5 == 0:  # Only every 5th click
    await dismiss_popups(page)
```

**Impact:**
- Save ~80 calls × 100ms = **8 seconds saved**
- New time: 428s - 8s = **420s (7 minutes)**

### 4. Parallelize Description Fetching (HIGH COMPLEXITY, HIGH IMPACT)
**Approach:** Open multiple panels simultaneously in different browser contexts

**Challenges:**
- ZipRecruiter's two-pane layout may not support this
- Risk of Cloudflare detection
- Complex implementation

**Skip for now** - Too risky and complex

### 5. Reduce Click Timeout (LOW IMPACT)
**Current:** 5000ms timeout for clicks
**Optimization:** Reduce to 3000ms

```python
await card.click(timeout=3000)  # Reduced from 5000ms
```

**Impact:**
- Only affects failed clicks (rare)
- Minimal time savings in practice
- **Save ~2-5 seconds total**

## Recommended Optimization Strategy

### Phase 1: Quick Wins (Implement Immediately)

```python
# In description fetching loop (line 870, 908):

# 1. Reduce panel wait from 1500ms to 800ms
await page.wait_for_timeout(800)  # Line 870

# 2. Reduce post-click delay from 300ms to 100ms
await page.wait_for_timeout(100)  # Line 908

# 3. Optimize popup dismissal (every 5 clicks instead of every click)
if i % 5 == 0:
    await dismiss_popups(page)
```

**Expected Results:**
- Current: 518s (8.6 min) per search
- After Phase 1: **~420s (7 min) per search**
- **Production: 65 × 7 min = 455 minutes (7.6 hours)** ← Still over limit!

### Phase 2: Alternative Approach - Fetch Descriptions from Job URLs

Instead of clicking panels, navigate directly to job pages:

```python
async def fetch_description_from_url(browser, job_url):
    """Fetch description by visiting job page directly."""
    try:
        page = await browser.new_page()
        await page.goto(job_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)

        # Extract description directly from job page
        description = await page.evaluate("""
            () => {
                // Job pages have full description in main content
                const main = document.querySelector('main, .job-description, [class*="description"]');
                return main ? main.innerText.trim() : '';
            }
        """)

        await page.close()
        return description
    except Exception:
        return ""
```

**Pros:**
- Could be faster (no panel waiting)
- More reliable (full page content)
- Can parallelize (open multiple pages)

**Cons:**
- More page loads (could trigger Cloudflare)
- Need to test if faster in practice

### Phase 3: Batch Parallelization (Infrastructure Change)

Split into 8 batches instead of 4:
- 8-9 searches per batch
- All batches run in parallel
- Max time per batch: 8 × 7min = 56 minutes ✓

**Changes needed:**
- `.github/workflows/scrape-leads.yml` - Update matrix
- `scraper.py` - Update batch calculation

## Immediate Action Plan

Let me implement Phase 1 optimizations now and test:

### Changes to Make:
1. Line 870: `await page.wait_for_timeout(800)` (was 1500)
2. Line 908: `await page.wait_for_timeout(100)` (was 300)
3. Line 871: Conditional popup dismissal

### Expected Outcome:
- ~420s per search (7 minutes)
- 65 searches = 455 minutes (7.6 hours)
- **Still 1.6 hours over 6-hour limit**

### Next Decision Point:
After testing Phase 1, we need to choose:

**Option A:** Phase 2 (Job URL fetching)
- Could be faster
- Need to test feasibility

**Option B:** Phase 3 (8-batch parallel)
- Guaranteed to work
- Infrastructure change required

**Option C:** Reduce to 80 descriptions (80% extraction)
- 80 descriptions × 4.2s = 336s (5.6 minutes)
- 65 searches = 364 minutes (6.1 hours) ✓ Just over but closer

**Option D:** Reduce to 70 descriptions (70% extraction)
- 70 descriptions × 4.2s = 294s (4.9 minutes)
- 65 searches = 318 minutes (5.3 hours) ✓ Safe margin

---

**Next Steps:**
1. Implement Phase 1 optimizations
2. Test locally with 1 search
3. Measure actual time savings
4. Decide on final approach based on results
