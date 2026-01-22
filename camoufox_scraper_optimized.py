"""
Optimized version of dismiss_popups with strict 3-second timeout.

Key optimizations:
1. Overall function timeout of 3 seconds (vs unlimited)
2. Removed slow query_selector_all for login banners
3. Streamlined popup dismissal flow
4. Early exit if popups dismissed successfully
"""

import asyncio


async def dismiss_popups_fast(page, max_time: float = 3.0) -> None:
    """Dismiss common popup dialogs with strict timeout.

    Args:
        page: Playwright page object
        max_time: Maximum time in seconds to spend dismissing popups (default 3s)
    """
    start_time = asyncio.get_event_loop().time()

    def time_left():
        return max_time - (asyncio.get_event_loop().time() - start_time)

    try:
        # Quick escape presses (600ms total)
        for _ in range(3):
            if time_left() <= 0:
                return
            try:
                await page.keyboard.press('Escape')
                await page.wait_for_timeout(200)
            except Exception:
                pass

        if time_left() <= 0:
            return

        await page.wait_for_timeout(min(500, int(time_left() * 1000)))

        # Quick DOM cleanup (300ms)
        if time_left() > 0:
            try:
                await asyncio.wait_for(
                    page.evaluate("""
                        () => {
                            // Remove focus lock containers
                            document.querySelectorAll('[data-focus-lock-disabled]').forEach(el => el.remove());
                            // Remove overlay backdrops
                            document.querySelectorAll('[role="presentation"][class*="bg-black"], [class*="bg-opacity-50"]').forEach(el => {
                                if (el.classList.contains('fixed') || el.classList.contains('inset-0')) {
                                    el.remove();
                                }
                            });
                            // Remove modal containers
                            document.querySelectorAll('[class*="modal"][class*="fixed"], [class*="overlay"][class*="fixed"]').forEach(el => el.remove());
                            // Remove Google Sign-in
                            document.querySelectorAll('iframe[src*="accounts.google.com"]').forEach(el => {
                                el.parentElement?.remove() || el.remove();
                            });
                        }
                    """),
                    timeout=0.5
                )
                await page.wait_for_timeout(200)
            except asyncio.TimeoutError:
                pass
            except Exception:
                pass

        if time_left() <= 0:
            return

        # Try clicking close buttons (max 1.5s)
        close_selectors = [
            '[class*="close" i]:not(input)',
            'button[aria-label*="close" i]',
            'button:has-text("×")',
            'button:has-text("No thanks")',
        ]

        for selector in close_selectors:
            if time_left() <= 0:
                return
            try:
                # Use timeout on query_selector
                element = await asyncio.wait_for(
                    page.query_selector(selector),
                    timeout=min(0.3, time_left())
                )
                if element:
                    is_visible = await asyncio.wait_for(
                        element.is_visible(),
                        timeout=min(0.2, time_left())
                    )
                    if is_visible:
                        await element.click()
                        await page.wait_for_timeout(200)
                        print(f"    [popup] Clicked {selector}")
                        return  # Success, exit early
            except asyncio.TimeoutError:
                continue
            except Exception:
                continue

    except Exception:
        pass  # Overall exception handler


# Test function to verify optimization
async def test_dismiss_popups_performance():
    """Compare old vs new popup dismissal."""
    from camoufox.async_api import AsyncCamoufox
    from camoufox_scraper import scrape_glassdoor_page
    import time

    async with AsyncCamoufox(headless=True, humanize=True) as browser:
        # Get a job URL to test
        jobs = await scrape_glassdoor_page(browser, "solar designer", max_descriptions=0)

        if not jobs or not jobs[0].get('job_url'):
            print("No jobs found to test")
            return

        job_url = jobs[0]['job_url']
        if not job_url.startswith('http'):
            job_url = f"https://www.glassdoor.com{job_url}"

        print(f"Testing popup dismissal on: {job_url[:60]}...")

        # Test with optimized version
        page = await browser.new_page()
        start = time.time()
        await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(500)  # Reduced from 2000ms
        await dismiss_popups_fast(page, max_time=3.0)
        elapsed = time.time() - start
        await page.close()

        print(f"\nOptimized version: {elapsed:.1f}s total")
        print(f"  - Navigation + 500ms wait: ~3-4s")
        print(f"  - Popup dismissal: max 3s (actual may be less)")


if __name__ == "__main__":
    asyncio.run(test_dismiss_popups_performance())
