"""
Test script to profile Glassdoor description fetching performance.
Identifies bottlenecks and tests optimization strategies.
"""

import asyncio
import time
from datetime import datetime
from camoufox.async_api import AsyncCamoufox
from camoufox_scraper import scrape_glassdoor_page, fetch_job_description, dismiss_popups


async def fetch_job_description_profiled(page, job_url: str, site: str = "glassdoor", timeout: int = 30000):
    """Profiled version of fetch_job_description with timing breakdown."""
    if not job_url:
        return "", {}

    timings = {}
    overall_start = time.time()

    try:
        # Time: Page navigation
        nav_start = time.time()
        await page.goto(job_url, wait_until="domcontentloaded", timeout=timeout)
        timings['navigation'] = (time.time() - nav_start) * 1000

        # Time: Post-navigation wait
        wait_start = time.time()
        await page.wait_for_timeout(2000)
        timings['post_nav_wait'] = (time.time() - wait_start) * 1000

        # Time: Popup dismissal
        popup_start = time.time()
        await dismiss_popups(page)
        timings['popup_dismiss'] = (time.time() - popup_start) * 1000

        description = ""

        # Time: Selector matching
        selector_start = time.time()
        desc_selectors = [
            '[class*="jobDescription"]',
            '[data-test="jobDescription"]',
            '.jobDescriptionContent',
            '.desc',
            '[class*="description"]',
        ]

        for selector in desc_selectors:
            try:
                el = page.locator(selector).first
                if await el.count() > 0:
                    description = await el.inner_text()
                    if description and len(description) > 50:
                        break
            except Exception:
                continue

        timings['selector_match'] = (time.time() - selector_start) * 1000
        timings['total'] = (time.time() - overall_start) * 1000

        return description.strip()[:5000] if description else "", timings

    except Exception as e:
        timings['error'] = str(e)[:100]
        timings['total'] = (time.time() - overall_start) * 1000
        return "", timings


async def fetch_description_optimized(page, job_url: str, site: str = "glassdoor"):
    """Optimized version with reduced waits and faster timeout."""
    if not job_url:
        return ""

    try:
        # Reduced timeout from 30s to 10s
        await page.goto(job_url, wait_until="domcontentloaded", timeout=10000)

        # Reduced wait from 2s to 500ms
        await page.wait_for_timeout(500)

        # Skip popup dismiss for speed (may cause issues but testing)

        description = ""
        desc_selectors = [
            '[class*="jobDescription"]',
            '[data-test="jobDescription"]',
            '.jobDescriptionContent',
        ]

        for selector in desc_selectors:
            try:
                el = page.locator(selector).first
                if await el.count() > 0:
                    description = await el.inner_text()
                    if description and len(description) > 50:
                        break
            except Exception:
                continue

        return description.strip()[:5000] if description else ""

    except Exception as e:
        print(f"    [optimized] Error: {str(e)[:50]}")
        return ""


async def test_serial_vs_parallel(browser, job_urls: list[str]):
    """Compare serial vs parallel description fetching."""
    print("\n" + "="*80)
    print("TEST: Serial vs Parallel Description Fetching")
    print("="*80)

    # Test 1: Serial fetching (current approach)
    print("\n[1/2] Testing SERIAL fetching (current method)...")
    page = await browser.new_page()

    serial_start = time.time()
    serial_results = []
    for i, url in enumerate(job_urls[:5]):  # Test with 5 jobs
        desc, timings = await fetch_job_description_profiled(page, url, "glassdoor")
        serial_results.append({
            'url': url,
            'desc_len': len(desc),
            'timings': timings
        })
        print(f"  Job {i+1}/5: {timings.get('total', 0):.0f}ms | {len(desc)} chars")

    serial_total = time.time() - serial_start
    await page.close()

    print(f"\n  Serial total: {serial_total:.1f}s for 5 descriptions")
    print(f"  Avg per description: {serial_total/5:.1f}s")

    # Test 2: Parallel fetching (3 concurrent)
    print("\n[2/2] Testing PARALLEL fetching (3 concurrent pages)...")

    async def fetch_with_page(url, idx):
        page = await browser.new_page()
        try:
            desc, timings = await fetch_job_description_profiled(page, url, "glassdoor")
            return idx, desc, timings
        finally:
            await page.close()

    parallel_start = time.time()

    # Fetch in batches of 3
    parallel_results = []
    for i in range(0, min(5, len(job_urls)), 3):
        batch_urls = job_urls[i:i+3]
        tasks = [fetch_with_page(url, i+j) for j, url in enumerate(batch_urls)]
        batch_results = await asyncio.gather(*tasks)
        parallel_results.extend(batch_results)

        for idx, desc, timings in batch_results:
            print(f"  Job {idx+1}/5: {timings.get('total', 0):.0f}ms | {len(desc)} chars")

    parallel_total = time.time() - parallel_start

    print(f"\n  Parallel total: {parallel_total:.1f}s for 5 descriptions")
    print(f"  Avg per description: {parallel_total/5:.1f}s")
    print(f"  Speedup: {serial_total/parallel_total:.1f}x")

    return serial_results, parallel_results, serial_total, parallel_total


async def test_optimized_timeouts(browser, job_urls: list[str]):
    """Test optimized version with reduced timeouts."""
    print("\n" + "="*80)
    print("TEST: Optimized Timeouts (10s navigation, 500ms wait)")
    print("="*80)

    page = await browser.new_page()

    opt_start = time.time()
    opt_results = []

    for i, url in enumerate(job_urls[:5]):
        desc_start = time.time()
        desc = await fetch_description_optimized(page, url)
        desc_time = time.time() - desc_start

        opt_results.append({
            'url': url,
            'desc_len': len(desc),
            'time': desc_time
        })
        print(f"  Job {i+1}/5: {desc_time:.1f}s | {len(desc)} chars")

    opt_total = time.time() - opt_start
    await page.close()

    print(f"\n  Optimized total: {opt_total:.1f}s for 5 descriptions")
    print(f"  Avg per description: {opt_total/5:.1f}s")

    return opt_results, opt_total


async def analyze_timing_breakdown(serial_results):
    """Analyze where time is spent in description fetching."""
    print("\n" + "="*80)
    print("TIMING BREAKDOWN ANALYSIS")
    print("="*80)

    total_nav = 0
    total_wait = 0
    total_popup = 0
    total_selector = 0
    count = len(serial_results)

    for result in serial_results:
        timings = result.get('timings', {})
        total_nav += timings.get('navigation', 0)
        total_wait += timings.get('post_nav_wait', 0)
        total_popup += timings.get('popup_dismiss', 0)
        total_selector += timings.get('selector_match', 0)

    print(f"\nAverage time breakdown per description:")
    print(f"  Navigation (page load):  {total_nav/count/1000:.2f}s ({total_nav/count/10:.0f}%)")
    print(f"  Post-nav wait (2000ms):  {total_wait/count/1000:.2f}s ({total_wait/count/10:.0f}%)")
    print(f"  Popup dismissal:         {total_popup/count/1000:.2f}s ({total_popup/count/10:.0f}%)")
    print(f"  Selector matching:       {total_selector/count/1000:.2f}s ({total_selector/count/10:.0f}%)")
    print(f"  Total:                   {(total_nav+total_wait+total_popup+total_selector)/count/1000:.2f}s")

    return {
        'avg_navigation_ms': total_nav / count,
        'avg_wait_ms': total_wait / count,
        'avg_popup_ms': total_popup / count,
        'avg_selector_ms': total_selector / count,
    }


async def main():
    print("="*80)
    print("GLASSDOOR PERFORMANCE PROFILING TEST")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize browser
    print("\nInitializing Camoufox browser...")
    async with AsyncCamoufox(
        headless=True,
        humanize=True,
        disable_coop=True,
    ) as browser:

        # First, scrape a search to get job URLs
        print("\n[STEP 1] Scraping Glassdoor search to get job URLs...")
        search_start = time.time()
        jobs = await scrape_glassdoor_page(
            browser,
            search_term="solar designer",
            debug_dir="output/debug_screenshots",
            max_descriptions=0  # Don't fetch descriptions yet
        )
        search_time = time.time() - search_start

        print(f"  Found {len(jobs)} jobs in {search_time:.1f}s")

        if not jobs:
            print("\n❌ No jobs found. Cannot test description fetching.")
            return

        # Extract job URLs
        job_urls = [j['job_url'] for j in jobs if j.get('job_url')]
        print(f"  Extracted {len(job_urls)} job URLs for testing")

        if len(job_urls) < 5:
            print(f"\n⚠️  Only {len(job_urls)} URLs available, need at least 5 for testing")
            return

        # Make URLs absolute
        job_urls = [url if url.startswith('http') else f"https://www.glassdoor.com{url}" for url in job_urls]

        print(f"\nSample URLs:")
        for i, url in enumerate(job_urls[:3]):
            print(f"  {i+1}. {url[:80]}...")

        # Run tests
        print("\n" + "="*80)
        print("RUNNING PERFORMANCE TESTS")
        print("="*80)

        # Test 1: Serial vs Parallel
        serial_results, parallel_results, serial_time, parallel_time = await test_serial_vs_parallel(browser, job_urls)

        # Test 2: Timing breakdown analysis
        timing_breakdown = await analyze_timing_breakdown(serial_results)

        # Test 3: Optimized timeouts
        opt_results, opt_time = await test_optimized_timeouts(browser, job_urls)

        # Summary
        print("\n" + "="*80)
        print("SUMMARY & RECOMMENDATIONS")
        print("="*80)

        print(f"\nCurrent performance (serial, 30s timeout, 2s wait):")
        print(f"  Time for 5 descriptions: {serial_time:.1f}s")
        print(f"  Avg per description: {serial_time/5:.1f}s")
        print(f"  Projected time for 10 descriptions: {serial_time/5*10:.1f}s")

        print(f"\nParallel fetching (3 concurrent):")
        print(f"  Time for 5 descriptions: {parallel_time:.1f}s")
        print(f"  Speedup: {serial_time/parallel_time:.1f}x")
        print(f"  Projected time for 10 descriptions: {parallel_time/5*10:.1f}s")
        print(f"  TIME SAVED: {serial_time/5*10 - parallel_time/5*10:.1f}s per search")

        print(f"\nOptimized timeouts (10s timeout, 500ms wait):")
        print(f"  Time for 5 descriptions: {opt_time:.1f}s")
        print(f"  Speedup vs current: {serial_time/opt_time:.1f}x")
        print(f"  Projected time for 10 descriptions: {opt_time/5*10:.1f}s")
        print(f"  TIME SAVED: {serial_time/5*10 - opt_time/5*10:.1f}s per search")

        print(f"\nBest case (parallel + optimized):")
        estimated_best = (opt_time / serial_time) * parallel_time
        print(f"  Estimated time for 5 descriptions: {estimated_best:.1f}s")
        print(f"  Speedup vs current: {serial_time/estimated_best:.1f}x")
        print(f"  Projected time for 10 descriptions: {estimated_best/5*10:.1f}s")
        print(f"  TIME SAVED: {serial_time/5*10 - estimated_best/5*10:.1f}s per search")

        # Calculate impact on full run
        print(f"\n" + "="*80)
        print("IMPACT ON FULL RUN (65 searches, 21 with jobs)")
        print("="*80)

        current_glassdoor_time = 228.2  # From analysis
        time_per_desc_current = serial_time / 5
        time_per_desc_best = estimated_best / 5

        new_time_per_search = 20 + (10 * time_per_desc_best)  # 20s page load + 10 descriptions

        print(f"\nCurrent: {current_glassdoor_time:.1f}s per search with jobs")
        print(f"Optimized: {new_time_per_search:.1f}s per search with jobs")
        print(f"Savings per search: {current_glassdoor_time - new_time_per_search:.1f}s")
        print(f"\nTotal savings for 21 searches: {(current_glassdoor_time - new_time_per_search) * 21 / 60:.1f} minutes")
        print(f"New Glassdoor total time: {(new_time_per_search * 21 + 20*44) / 60:.1f} minutes")
        print(f"  (vs current: 94.8 minutes)")

        print(f"\n✅ Testing complete!")


if __name__ == "__main__":
    asyncio.run(main())
