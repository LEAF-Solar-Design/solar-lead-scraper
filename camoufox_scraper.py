"""
Browser-based scraper using Camoufox for Cloudflare-protected job sites.
Camoufox is a Firefox-based anti-detect browser that works better in CI environments.

This module handles ZipRecruiter and Glassdoor which block standard HTTP requests.
"""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd

# Only import camoufox if available (optional dependency)
try:
    from camoufox.async_api import AsyncCamoufox
    CAMOUFOX_AVAILABLE = True
except ImportError:
    CAMOUFOX_AVAILABLE = False


@dataclass
class BrowserSearchError:
    """Record of a failed browser-based search."""
    search_term: str
    site: str
    error_type: str
    error_message: str
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "search_term": self.search_term,
            "site": self.site,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "timestamp": self.timestamp
        }


async def solve_cloudflare_turnstile(page, max_attempts: int = 3) -> bool:
    """
    Attempt to solve Cloudflare Turnstile challenge by clicking the checkbox.

    The technique locates the Cloudflare challenge iframe and clicks the checkbox
    at calculated coordinates within the frame.

    Args:
        page: Playwright page object
        max_attempts: Maximum number of click attempts

    Returns:
        True if challenge was solved, False otherwise
    """
    # Multiple iframe URL patterns that Cloudflare Turnstile may use
    iframe_patterns = [
        'iframe[src*="challenges.cloudflare.com"]',
        'iframe[src*="cloudflare.com/cdn-cgi"]',
        'iframe[src*="turnstile"]',
        'iframe[title*="Cloudflare"]',
        'iframe[title*="challenge"]',
        '.cf-turnstile iframe',
        '[data-turnstile] iframe',
        'div[class*="turnstile"] iframe',
    ]

    for attempt in range(max_attempts):
        # Wait for potential iframe to load
        await page.wait_for_timeout(2000)

        # Check if we're on a Cloudflare challenge page
        content = await page.content()
        if "challenge" not in content.lower() and "turnstile" not in content.lower() and "verify" not in content.lower():
            # No challenge present, we're good
            return True

        try:
            # Try each iframe selector pattern
            iframe_element = None
            matched_selector = None

            for selector in iframe_patterns:
                iframe_element = await page.query_selector(selector)
                if iframe_element:
                    matched_selector = selector
                    break

            # If no iframe found, try finding any iframe and check its attributes
            if not iframe_element:
                all_iframes = await page.query_selector_all('iframe')
                if all_iframes:
                    print(f"    [turnstile] Attempt {attempt + 1}: Found {len(all_iframes)} iframe(s), checking attributes...")
                    for idx, iframe in enumerate(all_iframes):
                        src = await iframe.get_attribute('src') or ''
                        title = await iframe.get_attribute('title') or ''
                        name = await iframe.get_attribute('name') or ''
                        print(f"      iframe[{idx}]: src={src[:80]}... title={title} name={name}")
                        # Check if this looks like a Turnstile iframe
                        if 'cloudflare' in src.lower() or 'turnstile' in src.lower() or 'challenge' in title.lower():
                            iframe_element = iframe
                            matched_selector = f"iframe[{idx}] (dynamic match)"
                            break

            if not iframe_element:
                # Try to find the widget container and click directly on it
                widget_selectors = [
                    '.cf-turnstile',
                    '[data-turnstile-widget]',
                    'div[class*="turnstile"]',
                    'div[id*="turnstile"]',
                    'input[type="checkbox"][name*="cf"]',
                ]
                widget_found = False
                for selector in widget_selectors:
                    widget = await page.query_selector(selector)
                    if widget:
                        box = await widget.bounding_box()
                        if box:
                            # Click near the left side where checkbox typically is
                            click_x = box['x'] + 30
                            click_y = box['y'] + (box['height'] / 2)
                            print(f"    [turnstile] Attempt {attempt + 1}: Found widget via {selector}, clicking at ({click_x:.0f}, {click_y:.0f})")
                            await page.mouse.click(click_x, click_y)
                            await page.wait_for_timeout(3000)
                            new_content = await page.content()
                            if "challenge" not in new_content.lower() or "success" in new_content.lower():
                                print(f"    [turnstile] Challenge solved via widget click on attempt {attempt + 1}")
                                return True
                            widget_found = True
                            break

                if not widget_found:
                    # Last resort: Look for the Cloudflare managed challenge checkbox
                    # These are full-page challenges with a visible checkbox, not embedded widgets
                    checkbox_selectors = [
                        'input[type="checkbox"]',  # Generic checkbox
                        'label:has-text("Verify")',
                        'label:has-text("human")',
                        '#challenge-form input',
                        '.challenge-form input',
                        '[class*="checkbox"]',
                        'span[class*="mark"]',  # Checkbox visual indicator
                    ]

                    for selector in checkbox_selectors:
                        try:
                            checkbox = await page.query_selector(selector)
                            if checkbox:
                                box = await checkbox.bounding_box()
                                if box:
                                    click_x = box['x'] + (box['width'] / 2)
                                    click_y = box['y'] + (box['height'] / 2)
                                    print(f"    [turnstile] Attempt {attempt + 1}: Found checkbox via {selector}, clicking at ({click_x:.0f}, {click_y:.0f})")
                                    await page.mouse.click(click_x, click_y)
                                    await page.wait_for_timeout(3000)
                                    new_content = await page.content()
                                    if "challenge" not in new_content.lower() or "success" in new_content.lower():
                                        print(f"    [turnstile] Challenge solved via checkbox click on attempt {attempt + 1}")
                                        return True
                                    break
                        except Exception:
                            continue

                    # Ultimate fallback: find any clickable element with "verify" text
                    try:
                        verify_elem = await page.query_selector('text=Verify you are human')
                        if verify_elem:
                            # The checkbox is usually to the left of this text
                            box = await verify_elem.bounding_box()
                            if box:
                                # Click to the left of the text where checkbox would be
                                click_x = box['x'] - 20
                                click_y = box['y'] + (box['height'] / 2)
                                print(f"    [turnstile] Attempt {attempt + 1}: Clicking left of 'Verify' text at ({click_x:.0f}, {click_y:.0f})")
                                await page.mouse.click(click_x, click_y)
                                await page.wait_for_timeout(3000)
                                new_content = await page.content()
                                if "challenge" not in new_content.lower() or "success" in new_content.lower():
                                    print(f"    [turnstile] Challenge solved via text-adjacent click on attempt {attempt + 1}")
                                    return True
                    except Exception:
                        pass

                print(f"    [turnstile] Attempt {attempt + 1}: No challenge iframe or widget found")
                await page.wait_for_timeout(1000)
                continue

            # Get bounding box of the iframe
            box = await iframe_element.bounding_box()
            if not box:
                print(f"    [turnstile] Attempt {attempt + 1}: Could not get iframe bounding box")
                continue

            # Calculate checkbox position (approximately 1/9 from left, middle vertically)
            # The checkbox is typically in the left portion of the Turnstile widget
            click_x = box['x'] + (box['width'] / 9)
            click_y = box['y'] + (box['height'] / 2)

            print(f"    [turnstile] Attempt {attempt + 1}: Found via {matched_selector}, clicking at ({click_x:.0f}, {click_y:.0f})")

            # Click with human-like delay
            await page.mouse.click(click_x, click_y)

            # Wait for challenge to process
            await page.wait_for_timeout(3000)

            # Check if challenge was solved (page should redirect or content should change)
            new_content = await page.content()
            if "challenge" not in new_content.lower() or "success" in new_content.lower():
                print(f"    [turnstile] Challenge solved on attempt {attempt + 1}")
                return True

        except Exception as e:
            print(f"    [turnstile] Attempt {attempt + 1} error: {str(e)[:100]}")

    print(f"    [turnstile] Failed to solve challenge after {max_attempts} attempts")
    return False


async def scrape_ziprecruiter_page(browser, search_term: str, location: str = "USA", debug_dir: str = None) -> list[dict]:
    """Scrape a single search from ZipRecruiter."""
    jobs = []
    page = None

    # Build search URL
    search_url = f"https://www.ziprecruiter.com/jobs-search?search={search_term.replace(' ', '+')}&location={location}"

    try:
        page = await browser.new_page()
        await page.goto(search_url, wait_until="domcontentloaded")

        # Wait for initial page load
        await page.wait_for_timeout(3000)

        # Check for and attempt to solve Cloudflare Turnstile challenge
        content = await page.content()
        if "challenge" in content.lower() or "verify" in content.lower():
            print(f"  [ziprecruiter] Cloudflare challenge detected, attempting to solve...")
            solved = await solve_cloudflare_turnstile(page)
            if solved:
                # Wait for redirect after solving
                await page.wait_for_timeout(3000)
            else:
                # Save screenshot of failed challenge
                if debug_dir:
                    safe_term = search_term.replace(' ', '_')[:20]
                    screenshot_path = f"{debug_dir}/ziprecruiter_{safe_term}_challenge.png"
                    try:
                        await page.screenshot(path=screenshot_path, full_page=True)
                    except Exception:
                        pass
                print(f"  [ziprecruiter] Could not solve Cloudflare challenge for '{search_term}'")
                return jobs

        # Wait for job cards to appear
        try:
            await page.wait_for_selector('article.job_result', timeout=15000)
        except Exception:
            # Debug: capture page title and check for Cloudflare
            try:
                title = await page.title()
                url = page.url
                # Check for Cloudflare challenge indicators
                content = await page.content()

                # Save debug screenshot if debug_dir provided
                if debug_dir:
                    safe_term = search_term.replace(' ', '_')[:20]
                    screenshot_path = f"{debug_dir}/ziprecruiter_{safe_term}.png"
                    try:
                        await page.screenshot(path=screenshot_path, full_page=True)
                        print(f"  [ziprecruiter] Saved debug screenshot: {screenshot_path}")
                    except Exception as e:
                        print(f"  [ziprecruiter] Failed to save screenshot: {e}")

                if "challenge" in content.lower() or "cloudflare" in content.lower():
                    print(f"  [ziprecruiter] Cloudflare challenge detected for '{search_term}'")
                elif "captcha" in content.lower():
                    print(f"  [ziprecruiter] CAPTCHA detected for '{search_term}'")
                else:
                    print(f"  [ziprecruiter] No job cards found for '{search_term}' (title: {title[:50]})")
            except Exception:
                print(f"  [ziprecruiter] No job cards found for '{search_term}'")
            return jobs

        # Get job cards using Playwright locators
        job_cards = await page.locator('article.job_result').all()

        for card in job_cards[:50]:  # Limit to 50 per search
            try:
                title_el = card.locator('h2.job_title a')
                company_el = card.locator('a.company_name')
                location_el = card.locator('span.job_location')
                snippet_el = card.locator('p.job_snippet')

                title = await title_el.inner_text() if await title_el.count() > 0 else ""
                company = await company_el.inner_text() if await company_el.count() > 0 else ""
                loc = await location_el.inner_text() if await location_el.count() > 0 else ""
                snippet = await snippet_el.inner_text() if await snippet_el.count() > 0 else ""
                link = await title_el.get_attribute('href') if await title_el.count() > 0 else ""

                if title and company:
                    jobs.append({
                        "title": title.strip(),
                        "company": company.strip(),
                        "location": loc.strip(),
                        "description": snippet.strip(),
                        "job_url": link.strip() if link else "",
                        "date_posted": "",
                        "salary": "",
                        "job_type": "",
                        "search_term": search_term,
                        "source_site": "ziprecruiter"
                    })
            except Exception:
                continue

    except Exception as e:
        print(f"  [ziprecruiter] Error parsing page: {str(e)[:100]}")
    finally:
        if page:
            await page.close()

    return jobs


async def scrape_glassdoor_page(browser, search_term: str, location: str = "United States", debug_dir: str = None) -> list[dict]:
    """Scrape a single search from Glassdoor."""
    jobs = []
    page = None

    # Build search URL
    search_url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={search_term.replace(' ', '+')}&locT=N&locId=1"

    try:
        page = await browser.new_page()
        await page.goto(search_url, wait_until="domcontentloaded")

        # Wait for initial page load
        await page.wait_for_timeout(3000)

        # Check for and attempt to solve Cloudflare Turnstile challenge
        content = await page.content()
        if "challenge" in content.lower() or "verify" in content.lower():
            print(f"  [glassdoor] Cloudflare challenge detected, attempting to solve...")
            solved = await solve_cloudflare_turnstile(page)
            if solved:
                # Wait for redirect after solving
                await page.wait_for_timeout(3000)
            else:
                # Save screenshot of failed challenge
                if debug_dir:
                    safe_term = search_term.replace(' ', '_')[:20]
                    screenshot_path = f"{debug_dir}/glassdoor_{safe_term}_challenge.png"
                    try:
                        await page.screenshot(path=screenshot_path, full_page=True)
                    except Exception:
                        pass
                print(f"  [glassdoor] Could not solve Cloudflare challenge for '{search_term}'")
                return jobs

        # Wait for job listings to appear
        try:
            await page.wait_for_selector('[data-test="jobListing"]', timeout=15000)
        except Exception:
            # Debug: capture page title and check for Cloudflare
            try:
                title = await page.title()
                content = await page.content()

                # Save debug screenshot if debug_dir provided
                if debug_dir:
                    safe_term = search_term.replace(' ', '_')[:20]
                    screenshot_path = f"{debug_dir}/glassdoor_{safe_term}.png"
                    try:
                        await page.screenshot(path=screenshot_path, full_page=True)
                        print(f"  [glassdoor] Saved debug screenshot: {screenshot_path}")
                    except Exception as e:
                        print(f"  [glassdoor] Failed to save screenshot: {e}")

                if "challenge" in content.lower() or "cloudflare" in content.lower():
                    print(f"  [glassdoor] Cloudflare challenge detected for '{search_term}'")
                elif "captcha" in content.lower():
                    print(f"  [glassdoor] CAPTCHA detected for '{search_term}'")
                else:
                    print(f"  [glassdoor] No job listings found for '{search_term}' (title: {title[:50]})")
            except Exception:
                print(f"  [glassdoor] No job listings found for '{search_term}'")
            return jobs

        # Get job cards
        job_cards = await page.locator('[data-test="jobListing"]').all()

        for card in job_cards[:50]:  # Limit to 50 per search
            try:
                title_el = card.locator('[data-test="job-title"]')
                company_el = card.locator('[data-test="employer-name"]')
                location_el = card.locator('[data-test="emp-location"]')

                title = await title_el.inner_text() if await title_el.count() > 0 else ""
                company = await company_el.inner_text() if await company_el.count() > 0 else ""
                loc = await location_el.inner_text() if await location_el.count() > 0 else ""

                link_el = card.locator('a').first
                link = await link_el.get_attribute('href') if await link_el.count() > 0 else ""

                if title and company:
                    jobs.append({
                        "title": title.strip(),
                        "company": company.strip(),
                        "location": loc.strip(),
                        "description": "",  # Glassdoor doesn't show snippet in search results
                        "job_url": link.strip() if link else "",
                        "date_posted": "",
                        "salary": "",
                        "job_type": "",
                        "search_term": search_term,
                        "source_site": "glassdoor"
                    })
            except Exception:
                continue

    except Exception as e:
        print(f"  [glassdoor] Error parsing page: {str(e)[:100]}")
    finally:
        if page:
            await page.close()

    return jobs


async def scrape_with_camoufox(
    search_terms: list[str],
    sites: list[str] = None,
    debug_screenshots: bool = False
) -> tuple[pd.DataFrame, list[BrowserSearchError]]:
    """
    Scrape Cloudflare-protected job sites using Camoufox browser.

    Args:
        search_terms: List of job search terms
        sites: Which sites to scrape ('ziprecruiter', 'glassdoor'). Default: both.
        debug_screenshots: If True, save screenshots when no results found (for CI debugging)

    Returns:
        Tuple of (DataFrame of jobs, list of errors)
    """
    if not CAMOUFOX_AVAILABLE:
        print("[Camoufox] camoufox not installed - skipping browser-based scraping")
        return pd.DataFrame(), []

    if sites is None:
        sites = ['ziprecruiter', 'glassdoor']

    all_jobs = []
    errors = []

    # Set up debug directory if screenshots enabled
    debug_dir = None
    if debug_screenshots:
        debug_dir = "output/debug_screenshots"
        os.makedirs(debug_dir, exist_ok=True)
        print(f"[Camoufox] Debug screenshots will be saved to: {debug_dir}")

    print(f"\n--- Camoufox Browser Scraping ({', '.join(sites)}) ---")
    print("Starting Camoufox browser (this may take a moment)...")

    try:
        # Camoufox configuration for CI environments
        # headless="virtual" uses Xvfb-like virtual display (Linux only)
        # headless=True uses standard headless mode
        is_linux = os.name != 'nt'
        headless_mode = "virtual" if is_linux else True

        print(f"[Camoufox] Platform: {'Linux' if is_linux else 'Windows'}, headless={headless_mode}")

        async with AsyncCamoufox(
            headless=headless_mode,
            humanize=True,  # Human-like mouse movements
            block_images=False,  # Need images for Turnstile challenge
            block_webrtc=True,  # Privacy
            os="windows" if not is_linux else None,  # Spoof Windows on Linux
            disable_coop=True,  # Allow clicking inside cross-origin iframes (for Turnstile)
        ) as browser:
            print("[Camoufox] Browser started successfully")

            for i, term in enumerate(search_terms):
                print(f"[Camoufox] Searching for: {term} ({i + 1}/{len(search_terms)})")

                # Scrape ZipRecruiter
                if 'ziprecruiter' in sites:
                    try:
                        jobs = await scrape_ziprecruiter_page(browser, term, debug_dir=debug_dir)
                        if jobs:
                            all_jobs.extend(jobs)
                            print(f"  [ziprecruiter] Found {len(jobs)} jobs")
                        else:
                            print(f"  [ziprecruiter] No results")
                    except Exception as e:
                        error_msg = str(e)[:500]
                        print(f"  [ziprecruiter] Error: {error_msg[:100]}")
                        errors.append(BrowserSearchError(
                            search_term=term,
                            site="ziprecruiter",
                            error_type="browser_error",
                            error_message=error_msg,
                            timestamp=datetime.now().isoformat()
                        ))

                # Small delay between sites
                await asyncio.sleep(2)

                # Scrape Glassdoor
                if 'glassdoor' in sites:
                    try:
                        jobs = await scrape_glassdoor_page(browser, term, debug_dir=debug_dir)
                        if jobs:
                            all_jobs.extend(jobs)
                            print(f"  [glassdoor] Found {len(jobs)} jobs")
                        else:
                            print(f"  [glassdoor] No results")
                    except Exception as e:
                        error_msg = str(e)[:500]
                        print(f"  [glassdoor] Error: {error_msg[:100]}")
                        errors.append(BrowserSearchError(
                            search_term=term,
                            site="glassdoor",
                            error_type="browser_error",
                            error_message=error_msg,
                            timestamp=datetime.now().isoformat()
                        ))

                # Delay between searches to avoid detection
                if i < len(search_terms) - 1:
                    delay = 5 + (i % 3) * 2  # 5-9 seconds, varies slightly
                    print(f"  Waiting {delay}s before next search...")
                    await asyncio.sleep(delay)

    except Exception as e:
        print(f"[Camoufox] Fatal error: {str(e)[:200]}")
        errors.append(BrowserSearchError(
            search_term="*",
            site="camoufox",
            error_type="fatal",
            error_message=str(e)[:500],
            timestamp=datetime.now().isoformat()
        ))

    if all_jobs:
        df = pd.DataFrame(all_jobs)
        print(f"[Camoufox] Total: {len(df)} jobs from browser scraping")
        return df, errors

    return pd.DataFrame(), errors


def run_camoufox_scraper(search_terms: list[str], sites: list[str] = None, debug_screenshots: bool = None) -> tuple[pd.DataFrame, list[dict]]:
    """
    Synchronous wrapper for the async Camoufox scraper.

    Args:
        search_terms: List of job search terms
        sites: Which sites to scrape
        debug_screenshots: If True, save screenshots when no results found.
                          If None, auto-detect from CAMOUFOX_DEBUG env var.

    Returns:
        Tuple of (DataFrame of jobs, list of error dicts)
    """
    if not CAMOUFOX_AVAILABLE:
        print("[Camoufox] camoufox not available - install with: pip install camoufox && camoufox fetch")
        return pd.DataFrame(), []

    # Auto-detect debug mode from environment if not specified
    if debug_screenshots is None:
        debug_screenshots = os.environ.get("CAMOUFOX_DEBUG", "0") == "1"

    try:
        df, errors = asyncio.run(scrape_with_camoufox(search_terms, sites, debug_screenshots=debug_screenshots))
        return df, [e.to_dict() for e in errors]
    except Exception as e:
        print(f"[Camoufox] Error running scraper: {str(e)[:200]}")
        return pd.DataFrame(), [{
            "search_term": "*",
            "site": "camoufox",
            "error_type": "fatal",
            "error_message": str(e)[:500],
            "timestamp": datetime.now().isoformat()
        }]


async def debug_single_search():
    """Debug mode: scrape a single search and save screenshots."""
    if not CAMOUFOX_AVAILABLE:
        print("Camoufox not installed")
        return

    import os
    os.makedirs("debug_screenshots", exist_ok=True)

    print("Starting debug scrape...")

    async with AsyncCamoufox(
        headless=True,  # Use true headless for local testing
        humanize=True,
    ) as browser:
        # Test ZipRecruiter
        print("\n--- Testing ZipRecruiter ---")
        page = await browser.new_page()
        await page.goto("https://www.ziprecruiter.com/jobs-search?search=solar+designer&location=USA")
        await page.wait_for_timeout(8000)  # Wait longer

        title = await page.title()
        print(f"Page title: {title}")

        await page.screenshot(path="debug_screenshots/ziprecruiter.png", full_page=True)
        print("Saved screenshot to debug_screenshots/ziprecruiter.png")

        # Check for various selectors
        selectors_to_try = [
            'article.job_result',
            '.job_result',
            '[data-job-id]',
            '.jobList',
            '.job-listing',
            '.job_content',
        ]
        for sel in selectors_to_try:
            count = await page.locator(sel).count()
            if count > 0:
                print(f"  Found {count} elements matching '{sel}'")

        await page.close()

        # Test Glassdoor
        print("\n--- Testing Glassdoor ---")
        page = await browser.new_page()
        await page.goto("https://www.glassdoor.com/Job/jobs.htm?sc.keyword=solar+designer&locT=N&locId=1")
        await page.wait_for_timeout(8000)

        title = await page.title()
        print(f"Page title: {title}")

        await page.screenshot(path="debug_screenshots/glassdoor.png", full_page=True)
        print("Saved screenshot to debug_screenshots/glassdoor.png")

        # Check for various selectors
        selectors_to_try = [
            '[data-test="jobListing"]',
            '.JobsList_jobListItem',
            '.job-listing',
            '.jobCard',
            'li[data-id]',
        ]
        for sel in selectors_to_try:
            count = await page.locator(sel).count()
            if count > 0:
                print(f"  Found {count} elements matching '{sel}'")

        await page.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        # Debug mode: save screenshots
        import asyncio
        asyncio.run(debug_single_search())
    else:
        # Normal test run
        test_terms = ["solar designer"]
        df, errors = run_camoufox_scraper(test_terms)
        print(f"\nResults: {len(df)} jobs, {len(errors)} errors")
        if not df.empty:
            print(df.head())
