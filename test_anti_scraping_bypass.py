"""
Test strategies to bypass Glassdoor's anti-scraping measures.

Detected patterns:
1. Concurrent page loads from same browser → 100% timeout
2. Rapid serial requests → Rate limiting (27-40s delays)
3. Consistent timing patterns → Detection

Potential solutions:
1. Random delays between requests
2. Rotate user agents (already doing)
3. Separate browser contexts for each job
4. Stealth browser fingerprinting
5. Session cookies/authentication
6. Reduce max_descriptions to minimize detection
"""

import asyncio
import time
import random
from camoufox.async_api import AsyncCamoufox
from camoufox_scraper import scrape_glassdoor_page, dismiss_popups


async def fetch_description_with_delay(page, job_url: str, delay_range=(2, 5)):
    """Fetch description with random delay to appear more human."""
    # Random delay before navigating
    delay = random.uniform(*delay_range)
    await asyncio.sleep(delay)

    try:
        await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)

        # Variable wait time (more human-like)
        wait_time = random.randint(800, 1500)
        await page.wait_for_timeout(wait_time)

        # Dismiss popups with timeout
        await dismiss_popups(page, max_time=3.0)

        # Extract description
        desc_selectors = [
            '[class*="jobDescription"]',
            '[data-test="jobDescription"]',
            '.jobDescriptionContent',
        ]

        for selector in desc_selectors:
            try:
                el = page.locator(selector).first
                if await el.count() > 0:
                    desc = await el.inner_text()
                    if desc and len(desc) > 50:
                        return desc.strip()[:5000]
            except Exception:
                continue

        return ""
    except Exception as e:
        print(f"    [delayed] Error: {str(e)[:50]}")
        return ""


async def fetch_with_separate_context(browser, job_url: str, idx: int):
    """Use separate browser context for isolation (more stealth)."""
    context = await browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080},
        locale='en-US',
        timezone_id='America/New_York',
    )

    page = await context.new_page()

    try:
        # Random delay before this context starts
        await asyncio.sleep(random.uniform(1, 3))

        await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(random.randint(800, 1500))
        await dismiss_popups(page, max_time=3.0)

        # Extract description
        desc_selectors = [
            '[class*="jobDescription"]',
            '[data-test="jobDescription"]',
        ]

        desc = ""
        for selector in desc_selectors:
            try:
                el = page.locator(selector).first
                if await el.count() > 0:
                    desc = await el.inner_text()
                    if desc and len(desc) > 50:
                        break
            except Exception:
                continue

        return idx, desc.strip()[:5000] if desc else "", None

    except Exception as e:
        return idx, "", str(e)[:100]
    finally:
        await context.close()


async def fetch_with_realistic_browsing(page, job_url: str):
    """Simulate realistic human browsing behavior."""
    try:
        # Navigate
        await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)

        # Variable wait (human-like)
        await page.wait_for_timeout(random.randint(1000, 2000))

        # Simulate scrolling (humans scroll to read)
        await page.evaluate("""
            async () => {
                // Smooth scroll to simulate reading
                window.scrollTo({top: 300, behavior: 'smooth'});
                await new Promise(r => setTimeout(r, 500));
                window.scrollTo({top: 600, behavior: 'smooth'});
                await new Promise(r => setTimeout(r, 500));
            }
        """)

        await page.wait_for_timeout(random.randint(500, 1000))

        # Dismiss popups
        await dismiss_popups(page, max_time=3.0)

        # Random mouse movements
        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        await page.wait_for_timeout(random.randint(200, 400))

        # Extract description
        desc_selectors = [
            '[class*="jobDescription"]',
            '[data-test="jobDescription"]',
        ]

        for selector in desc_selectors:
            try:
                el = page.locator(selector).first
                if await el.count() > 0:
                    desc = await el.inner_text()
                    if desc and len(desc) > 50:
                        return desc.strip()[:5000]
            except Exception:
                continue

        return ""

    except Exception as e:
        print(f"    [realistic] Error: {str(e)[:50]}")
        return ""


async def test_strategy_1_random_delays():
    """Strategy 1: Random delays between requests."""
    print("\n" + "="*80)
    print("STRATEGY 1: Random Delays (2-5s between requests)")
    print("="*80)

    async with AsyncCamoufox(headless=True, humanize=True, disable_coop=True) as browser:
        # Get jobs
        jobs = await scrape_glassdoor_page(browser, "solar designer", max_descriptions=0)
        job_urls = [f"https://www.glassdoor.com{j['job_url']}" if not j['job_url'].startswith('http') else j['job_url']
                    for j in jobs[:5] if j.get('job_url')]

        print(f"\nFetching {len(job_urls)} descriptions with random delays...\n")

        page = await browser.new_page()
        times = []
        successes = 0

        for i, url in enumerate(job_urls):
            start = time.time()
            desc = await fetch_description_with_delay(page, url, delay_range=(2, 5))
            elapsed = time.time() - start
            times.append(elapsed)

            if len(desc) > 50:
                successes += 1
                print(f"  Job {i+1}: {elapsed:.1f}s | {len(desc)} chars ✓")
            else:
                print(f"  Job {i+1}: {elapsed:.1f}s | FAILED")

        await page.close()

        avg_time = sum(times) / len(times) if times else 0
        success_rate = (successes / len(job_urls)) * 100 if job_urls else 0

        print(f"\n  Results:")
        print(f"    Success rate: {success_rate:.0f}% ({successes}/{len(job_urls)})")
        print(f"    Avg time: {avg_time:.1f}s per description")
        print(f"    Total time: {sum(times):.1f}s for {len(job_urls)} jobs")

        return success_rate, avg_time


async def test_strategy_2_separate_contexts():
    """Strategy 2: Separate browser contexts (more isolation)."""
    print("\n" + "="*80)
    print("STRATEGY 2: Separate Browser Contexts")
    print("="*80)

    async with AsyncCamoufox(headless=True, humanize=True, disable_coop=True) as browser:
        # Get jobs
        jobs = await scrape_glassdoor_page(browser, "solar designer", max_descriptions=0)
        job_urls = [f"https://www.glassdoor.com{j['job_url']}" if not j['job_url'].startswith('http') else j['job_url']
                    for j in jobs[:5] if j.get('job_url')]

        print(f"\nFetching {len(job_urls)} descriptions with separate contexts...\n")

        start_all = time.time()
        results = []

        # Fetch sequentially with separate contexts
        for i, url in enumerate(job_urls):
            idx, desc, error = await fetch_with_separate_context(browser, url, i)
            elapsed = time.time() - start_all

            if len(desc) > 50:
                print(f"  Job {i+1}: {len(desc)} chars ✓")
                results.append((True, elapsed))
            else:
                print(f"  Job {i+1}: FAILED - {error if error else 'No description'}")
                results.append((False, elapsed))

        total_time = time.time() - start_all
        successes = sum(1 for success, _ in results if success)
        success_rate = (successes / len(results)) * 100 if results else 0
        avg_time = total_time / len(results) if results else 0

        print(f"\n  Results:")
        print(f"    Success rate: {success_rate:.0f}% ({successes}/{len(job_urls)})")
        print(f"    Avg time: {avg_time:.1f}s per description")
        print(f"    Total time: {total_time:.1f}s for {len(job_urls)} jobs")

        return success_rate, avg_time


async def test_strategy_3_realistic_browsing():
    """Strategy 3: Simulate realistic human browsing."""
    print("\n" + "="*80)
    print("STRATEGY 3: Realistic Human Browsing Simulation")
    print("="*80)

    async with AsyncCamoufox(headless=True, humanize=True, disable_coop=True) as browser:
        # Get jobs
        jobs = await scrape_glassdoor_page(browser, "solar designer", max_descriptions=0)
        job_urls = [f"https://www.glassdoor.com{j['job_url']}" if not j['job_url'].startswith('http') else j['job_url']
                    for j in jobs[:5] if j.get('job_url')]

        print(f"\nFetching {len(job_urls)} descriptions with realistic browsing...\n")

        page = await browser.new_page()
        times = []
        successes = 0

        for i, url in enumerate(job_urls):
            # Random delay before each request (2-6 seconds)
            if i > 0:  # Don't delay first request
                delay = random.uniform(2, 6)
                print(f"  Waiting {delay:.1f}s before next request...")
                await asyncio.sleep(delay)

            start = time.time()
            desc = await fetch_with_realistic_browsing(page, url)
            elapsed = time.time() - start
            times.append(elapsed)

            if len(desc) > 50:
                successes += 1
                print(f"  Job {i+1}: {elapsed:.1f}s | {len(desc)} chars ✓")
            else:
                print(f"  Job {i+1}: {elapsed:.1f}s | FAILED")

        await page.close()

        avg_time = sum(times) / len(times) if times else 0
        success_rate = (successes / len(job_urls)) * 100 if job_urls else 0

        print(f"\n  Results:")
        print(f"    Success rate: {success_rate:.0f}% ({successes}/{len(job_urls)})")
        print(f"    Avg time: {avg_time:.1f}s per description (excluding delays)")
        print(f"    Total time: {sum(times):.1f}s for {len(job_urls)} jobs")

        return success_rate, avg_time


async def main():
    print("="*80)
    print("ANTI-SCRAPING BYPASS STRATEGY TESTING")
    print("="*80)
    print("\nTesting 3 strategies to bypass Glassdoor's anti-scraping:")
    print("1. Random delays between requests (2-5s)")
    print("2. Separate browser contexts per request")
    print("3. Realistic human browsing simulation (scroll, mouse, variable timing)")

    # Test all strategies
    s1_success, s1_time = await test_strategy_1_random_delays()
    await asyncio.sleep(5)  # Cool down between tests

    s2_success, s2_time = await test_strategy_2_separate_contexts()
    await asyncio.sleep(5)

    s3_success, s3_time = await test_strategy_3_realistic_browsing()

    # Summary
    print("\n" + "="*80)
    print("STRATEGY COMPARISON")
    print("="*80)

    strategies = [
        ("Random Delays (2-5s)", s1_success, s1_time),
        ("Separate Contexts", s2_success, s2_time),
        ("Realistic Browsing", s3_success, s3_time),
    ]

    print(f"\n{'Strategy':<25} | Success Rate | Avg Time")
    print("-" * 60)
    for name, success, avg_time in strategies:
        print(f"{name:<25} | {success:>11.0f}% | {avg_time:>7.1f}s")

    # Recommendation
    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)

    best_strategy = max(strategies, key=lambda x: x[1])  # Highest success rate

    print(f"\nBest strategy: {best_strategy[0]}")
    print(f"  - Success rate: {best_strategy[1]:.0f}%")
    print(f"  - Avg time: {best_strategy[2]:.1f}s per description")

    if best_strategy[1] < 70:
        print("\n⚠️  WARNING: Even best strategy has <70% success rate.")
        print("   Glassdoor anti-scraping may be too sophisticated to bypass reliably.")
        print("   Consider alternative approaches:")
        print("   1. Reduce max_descriptions to 3-5 (less suspicious)")
        print("   2. Only fetch descriptions for high-confidence job titles")
        print("   3. Disable Glassdoor description fetching entirely")
    else:
        print(f"\n✓  {best_strategy[0]} shows promising results!")
        print("   Ready to implement in production.")

    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
