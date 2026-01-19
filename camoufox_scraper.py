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


async def scrape_ziprecruiter_page(browser, search_term: str, location: str = "USA") -> list[dict]:
    """Scrape a single search from ZipRecruiter."""
    jobs = []
    page = None

    # Build search URL
    search_url = f"https://www.ziprecruiter.com/jobs-search?search={search_term.replace(' ', '+')}&location={location}"

    try:
        page = await browser.new_page()
        await page.goto(search_url, wait_until="domcontentloaded")

        # Wait for page to load and Cloudflare challenge to resolve
        await page.wait_for_timeout(5000)

        # Wait for job cards to appear
        try:
            await page.wait_for_selector('article.job_result', timeout=15000)
        except Exception:
            # No results found or page structure changed
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


async def scrape_glassdoor_page(browser, search_term: str, location: str = "United States") -> list[dict]:
    """Scrape a single search from Glassdoor."""
    jobs = []
    page = None

    # Build search URL
    search_url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={search_term.replace(' ', '+')}&locT=N&locId=1"

    try:
        page = await browser.new_page()
        await page.goto(search_url, wait_until="domcontentloaded")

        # Wait for page to load and Cloudflare challenge to resolve
        await page.wait_for_timeout(5000)

        # Wait for job listings to appear
        try:
            await page.wait_for_selector('[data-test="jobListing"]', timeout=15000)
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
    sites: list[str] = None
) -> tuple[pd.DataFrame, list[BrowserSearchError]]:
    """
    Scrape Cloudflare-protected job sites using Camoufox browser.

    Args:
        search_terms: List of job search terms
        sites: Which sites to scrape ('ziprecruiter', 'glassdoor'). Default: both.

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
            block_images=True,  # Faster loading
            block_webrtc=True,  # Privacy
            os="windows" if not is_linux else None,  # Spoof Windows on Linux
        ) as browser:
            print("[Camoufox] Browser started successfully")

            for i, term in enumerate(search_terms):
                print(f"[Camoufox] Searching for: {term} ({i + 1}/{len(search_terms)})")

                # Scrape ZipRecruiter
                if 'ziprecruiter' in sites:
                    try:
                        jobs = await scrape_ziprecruiter_page(browser, term)
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
                        jobs = await scrape_glassdoor_page(browser, term)
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


def run_camoufox_scraper(search_terms: list[str], sites: list[str] = None) -> tuple[pd.DataFrame, list[dict]]:
    """
    Synchronous wrapper for the async Camoufox scraper.

    Args:
        search_terms: List of job search terms
        sites: Which sites to scrape

    Returns:
        Tuple of (DataFrame of jobs, list of error dicts)
    """
    if not CAMOUFOX_AVAILABLE:
        print("[Camoufox] camoufox not available - install with: pip install camoufox && camoufox fetch")
        return pd.DataFrame(), []

    try:
        df, errors = asyncio.run(scrape_with_camoufox(search_terms, sites))
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


if __name__ == "__main__":
    # Test run
    test_terms = ["solar designer"]
    df, errors = run_camoufox_scraper(test_terms)
    print(f"\nResults: {len(df)} jobs, {len(errors)} errors")
    if not df.empty:
        print(df.head())
