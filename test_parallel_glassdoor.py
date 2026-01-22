"""
Test parallel description fetching with separate pages to avoid rate limiting.
"""

import asyncio
import time
from camoufox.async_api import AsyncCamoufox
from camoufox_scraper import scrape_glassdoor_page, fetch_job_description


async def fetch_with_own_page(browser, url, idx):
    """Fetch description using its own page to avoid rate limiting."""
    page = await browser.new_page()
    try:
        start = time.time()
        desc = await fetch_job_description(page, url, "glassdoor")
        elapsed = time.time() - start
        return idx, desc, elapsed, None
    except Exception as e:
        elapsed = time.time() - start
        return idx, "", elapsed, str(e)[:100]
    finally:
        await page.close()


async def main():
    print("="*80)
    print("TESTING PARALLEL FETCHING WITH SEPARATE PAGES")
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
        for job in jobs[:10]:
            url = job.get('job_url', '')
            if url:
                if not url.startswith('http'):
                    url = f"https://www.glassdoor.com{url}"
                job_urls.append(url)

        # Test 1: Serial (current approach)
        print(f"[2/3] SERIAL fetching (baseline)...")
        page = await browser.new_page()
        serial_times = []

        for i, url in enumerate(job_urls[:5]):
            start = time.time()
            desc = await fetch_job_description(page, url, "glassdoor")
            elapsed = time.time() - start
            serial_times.append(elapsed)
            print(f"  Job {i+1}/5: {elapsed:.1f}s | {len(desc)} chars")

        await page.close()
        serial_avg = sum(serial_times) / len(serial_times)
        serial_total = sum(serial_times)

        print(f"\n  Serial total: {serial_total:.1f}s")
        print(f"  Serial avg: {serial_avg:.1f}s per description\n")

        # Test 2: Parallel (3 concurrent with separate pages)
        print(f"[3/3] PARALLEL fetching (3 concurrent, separate pages)...")

        parallel_start = time.time()
        all_results = []

        # Fetch in batches of 3
        for batch_start in range(0, min(len(job_urls), 6), 3):
            batch_urls = job_urls[batch_start:batch_start+3]
            tasks = [fetch_with_own_page(browser, url, batch_start+i) for i, url in enumerate(batch_urls)]
            batch_results = await asyncio.gather(*tasks)
            all_results.extend(batch_results)

            for idx, desc, elapsed, error in batch_results:
                status = f"{len(desc)} chars" if not error else f"ERROR: {error}"
                print(f"  Job {idx+1}: {elapsed:.1f}s | {status}")

        parallel_total = time.time() - parallel_start

        # Calculate average for successful fetches
        successful_times = [elapsed for _, desc, elapsed, error in all_results if not error and len(desc) > 0]
        parallel_avg = sum(successful_times) / len(successful_times) if successful_times else 0

        print(f"\n  Parallel total: {parallel_total:.1f}s")
        print(f"  Parallel avg (successful): {parallel_avg:.1f}s per description")
        print(f"  Speedup: {serial_total/parallel_total:.1f}x")

        print("\n" + "="*80)
        print("ANALYSIS")
        print("="*80)

        print(f"\nSerial approach:")
        print(f"  - Uses same page for all fetches")
        print(f"  - Avg: {serial_avg:.1f}s per description")
        print(f"  - Total for 5: {serial_total:.1f}s")

        print(f"\nParallel approach (3 concurrent):")
        print(f"  - Creates new page for each fetch")
        print(f"  - Avg: {parallel_avg:.1f}s per description")
        print(f"  - Total for 6: {parallel_total:.1f}s")
        print(f"  - Speedup: {serial_total/parallel_total:.1f}x")

        print(f"\nProjections for 10 descriptions:")
        serial_10 = serial_avg * 10
        parallel_10 = parallel_avg * 10 / 3  # 3 concurrent
        print(f"  - Serial: {serial_10:.1f}s ({serial_10/60:.1f} min)")
        print(f"  - Parallel (3x): {parallel_10:.1f}s ({parallel_10/60:.1f} min)")
        print(f"  - Time saved: {serial_10 - parallel_10:.1f}s ({(serial_10 - parallel_10)/60:.1f} min)")

        # Check for rate limiting evidence
        print(f"\nRate limiting analysis:")
        if len(serial_times) > 1:
            first = serial_times[0]
            later_avg = sum(serial_times[1:]) / len(serial_times[1:])
            print(f"  - First fetch (serial): {first:.1f}s")
            print(f"  - Later fetches (serial): {later_avg:.1f}s avg")
            if later_avg > first * 2:
                print(f"  - EVIDENCE: Later fetches are {later_avg/first:.1f}x slower - likely rate limiting")
            else:
                print(f"  - No clear rate limiting pattern")

        print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
