"""
Test optimized Glassdoor description fetching to verify improvements.
"""

import asyncio
import time
from camoufox.async_api import AsyncCamoufox
from camoufox_scraper import scrape_glassdoor_page, fetch_job_description


async def main():
    print("="*80)
    print("TESTING OPTIMIZED GLASSDOOR PERFORMANCE")
    print("="*80)
    print()

    async with AsyncCamoufox(headless=True, humanize=True, disable_coop=True) as browser:
        # Get jobs
        print("[1/3] Fetching job listings...")
        jobs = await scrape_glassdoor_page(
            browser,
            search_term="solar designer",
            max_descriptions=0
        )

        if not jobs:
            print("No jobs found!")
            return

        print(f"  Found {len(jobs)} jobs\n")

        # Make URLs absolute
        job_urls = []
        for job in jobs[:10]:  # Test with first 10
            url = job.get('job_url', '')
            if url:
                if not url.startswith('http'):
                    url = f"https://www.glassdoor.com{url}"
                job_urls.append(url)

        print(f"[2/3] Testing OPTIMIZED description fetching (5 jobs)...")
        print("  Optimizations applied:")
        print("    - dismiss_popups timeout: 3s (was unlimited)")
        print("    - post-nav wait: 500ms (was 2000ms)")
        print()

        page = await browser.new_page()
        times = []

        for i, url in enumerate(job_urls[:5]):
            start = time.time()
            desc = await fetch_job_description(page, url, "glassdoor")
            elapsed = time.time() - start
            times.append(elapsed)

            status = "OK" if len(desc) > 50 else "EMPTY"
            print(f"  Job {i+1}/5: {elapsed:.1f}s | {len(desc):,} chars [{status}]")

        await page.close()

        avg_time = sum(times) / len(times)

        print(f"\n[3/3] RESULTS SUMMARY")
        print("  " + "-"*76)
        print(f"  Average time per description: {avg_time:.1f}s")
        print(f"  Projected for 10 descriptions: {avg_time * 10:.1f}s ({avg_time * 10 / 60:.1f} min)")
        print()
        print("  COMPARISON WITH BASELINE:")
        print(f"    Baseline (from testing): 30.5s per description")
        print(f"    Optimized (current run): {avg_time:.1f}s per description")
        print(f"    Improvement: {((30.5 - avg_time) / 30.5 * 100):.1f}% faster")
        print(f"    Time saved per 10 desc: {(30.5 - avg_time) * 10:.1f}s ({(30.5 - avg_time) * 10 / 60:.1f} min)")
        print()
        print("  IMPACT ON FULL RUN (21 searches with jobs):")
        baseline_total = 30.5 * 10 * 21 / 60  # minutes
        optimized_total = avg_time * 10 * 21 / 60  # minutes
        print(f"    Baseline: {baseline_total:.1f} min for descriptions")
        print(f"    Optimized: {optimized_total:.1f} min for descriptions")
        print(f"    TIME SAVED: {baseline_total - optimized_total:.1f} minutes!")
        print()
        print("  PROJECTED NEW GLASSDOOR TOTAL:")
        # Page loads for 21 searches = 21 * 20s = 420s = 7 min
        # Zero-result searches = 44 * 20s = 880s = 14.7 min
        # Description fetches = optimized_total min
        new_total = 7 + 14.7 + optimized_total
        print(f"    Current total: 94.8 min")
        print(f"    Optimized total: {new_total:.1f} min")
        print(f"    TOTAL SAVINGS: {94.8 - new_total:.1f} minutes per run")
        print()

        if avg_time < 10:
            print("  SUCCESS! Optimizations are working effectively.")
        elif avg_time < 20:
            print("  GOOD: Significant improvement achieved.")
        else:
            print("  WARNING: Less improvement than expected. May need further optimization.")

        print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
