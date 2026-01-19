"""
Browser-based scraper for Cloudflare-protected job sites.
Uses nodriver (successor to undetected-chromedriver) with Xvfb virtual display.

This module handles ZipRecruiter and Glassdoor which block standard HTTP requests.
"""

import asyncio
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd

# Only import nodriver if available (optional dependency)
try:
    import nodriver as uc
    NODRIVER_AVAILABLE = True
except ImportError:
    NODRIVER_AVAILABLE = False


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

    # Build search URL
    search_url = f"https://www.ziprecruiter.com/jobs-search?search={search_term.replace(' ', '+')}&location={location}"

    try:
        page = await browser.get(search_url)

        # Wait for page to load and Cloudflare challenge to resolve
        await asyncio.sleep(5)

        # Wait for job cards to appear
        await page.wait_for_selector('article.job_result', timeout=15)

        # Get page content
        content = await page.get_content()

        # Parse job cards (simple extraction)
        # ZipRecruiter uses article.job_result for job cards
        job_cards = await page.query_selector_all('article.job_result')

        for card in job_cards[:50]:  # Limit to 50 per search
            try:
                title_el = await card.query_selector('h2.job_title a')
                company_el = await card.query_selector('a.company_name')
                location_el = await card.query_selector('span.job_location')
                snippet_el = await card.query_selector('p.job_snippet')

                title = await title_el.get_property('textContent') if title_el else ""
                company = await company_el.get_property('textContent') if company_el else ""
                loc = await location_el.get_property('textContent') if location_el else ""
                snippet = await snippet_el.get_property('textContent') if snippet_el else ""
                link = await title_el.get_property('href') if title_el else ""

                if title and company:
                    jobs.append({
                        "title": str(title).strip(),
                        "company": str(company).strip(),
                        "location": str(loc).strip(),
                        "description": str(snippet).strip(),
                        "job_url": str(link).strip(),
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

    return jobs


async def scrape_glassdoor_page(browser, search_term: str, location: str = "United States") -> list[dict]:
    """Scrape a single search from Glassdoor."""
    jobs = []

    # Build search URL
    search_url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={search_term.replace(' ', '+')}&locT=N&locId=1"

    try:
        page = await browser.get(search_url)

        # Wait for page to load and Cloudflare challenge to resolve
        await asyncio.sleep(5)

        # Wait for job listings to appear
        await page.wait_for_selector('[data-test="jobListing"]', timeout=15)

        # Get job cards
        job_cards = await page.query_selector_all('[data-test="jobListing"]')

        for card in job_cards[:50]:  # Limit to 50 per search
            try:
                title_el = await card.query_selector('[data-test="job-title"]')
                company_el = await card.query_selector('[data-test="employer-name"]')
                location_el = await card.query_selector('[data-test="emp-location"]')

                title = await title_el.get_property('textContent') if title_el else ""
                company = await company_el.get_property('textContent') if company_el else ""
                loc = await location_el.get_property('textContent') if location_el else ""
                link_el = await card.query_selector('a')
                link = await link_el.get_property('href') if link_el else ""

                if title and company:
                    jobs.append({
                        "title": str(title).strip(),
                        "company": str(company).strip(),
                        "location": str(loc).strip(),
                        "description": "",  # Glassdoor doesn't show snippet in search results
                        "job_url": str(link).strip(),
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

    return jobs


async def scrape_with_browser(
    search_terms: list[str],
    sites: list[str] = None
) -> tuple[pd.DataFrame, list[BrowserSearchError]]:
    """
    Scrape Cloudflare-protected job sites using a real browser.

    Args:
        search_terms: List of job search terms
        sites: Which sites to scrape ('ziprecruiter', 'glassdoor'). Default: both.

    Returns:
        Tuple of (DataFrame of jobs, list of errors)
    """
    if not NODRIVER_AVAILABLE:
        print("[Browser] nodriver not installed - skipping browser-based scraping")
        return pd.DataFrame(), []

    if sites is None:
        sites = ['ziprecruiter', 'glassdoor']

    all_jobs = []
    errors = []

    print(f"\n--- Browser Scraping ({', '.join(sites)}) ---")
    print("Starting browser (this may take a moment)...")

    try:
        # Start browser with Xvfb-compatible settings
        browser = await uc.start(
            headless=False,  # Use Xvfb instead of headless for better anti-detection
            browser_args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--window-size=1920,1080',
            ]
        )

        print("Browser started successfully")

        for i, term in enumerate(search_terms):
            print(f"[Browser] Searching for: {term} ({i + 1}/{len(search_terms)})")

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

        # Close browser
        browser.stop()

    except Exception as e:
        print(f"[Browser] Fatal error: {str(e)[:200]}")
        errors.append(BrowserSearchError(
            search_term="*",
            site="browser",
            error_type="fatal",
            error_message=str(e)[:500],
            timestamp=datetime.now().isoformat()
        ))

    if all_jobs:
        df = pd.DataFrame(all_jobs)
        print(f"[Browser] Total: {len(df)} jobs from browser scraping")
        return df, errors

    return pd.DataFrame(), errors


def run_browser_scraper(search_terms: list[str], sites: list[str] = None) -> tuple[pd.DataFrame, list[dict]]:
    """
    Synchronous wrapper for the async browser scraper.

    Args:
        search_terms: List of job search terms
        sites: Which sites to scrape

    Returns:
        Tuple of (DataFrame of jobs, list of error dicts)
    """
    if not NODRIVER_AVAILABLE:
        print("[Browser] nodriver not available - install with: pip install nodriver")
        return pd.DataFrame(), []

    # Check if we're in a display-less environment
    display = os.environ.get('DISPLAY')
    if not display:
        print("[Browser] No DISPLAY set - browser scraping requires Xvfb")
        print("[Browser] Set up with: Xvfb :99 -screen 0 1920x1080x24 & export DISPLAY=:99")
        return pd.DataFrame(), []

    try:
        df, errors = asyncio.get_event_loop().run_until_complete(
            scrape_with_browser(search_terms, sites)
        )
        return df, [e.to_dict() for e in errors]
    except RuntimeError:
        # No event loop running, create one
        df, errors = asyncio.run(scrape_with_browser(search_terms, sites))
        return df, [e.to_dict() for e in errors]


if __name__ == "__main__":
    # Test run
    test_terms = ["solar designer"]
    df, errors = run_browser_scraper(test_terms)
    print(f"\nResults: {len(df)} jobs, {len(errors)} errors")
    if not df.empty:
        print(df.head())
