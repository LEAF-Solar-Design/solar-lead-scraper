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


async def dismiss_popups(page) -> None:
    """Dismiss common popup dialogs that may block interaction with the page.

    This includes Google Sign-in dialogs, cookie consent banners, email signup modals, etc.
    """
    # First, try pressing Escape multiple times which dismisses most modals
    for _ in range(3):
        try:
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(200)
        except Exception:
            pass

    await page.wait_for_timeout(500)

    # Check if there's still a visible modal and try clicking outside it
    # This works for most overlay-style modals
    try:
        modal = await page.query_selector('[role="dialog"], [class*="modal" i], [class*="overlay" i]')
        if modal and await modal.is_visible():
            print(f"    [popup] Modal still visible, clicking outside to dismiss...")
            # Click in the far corner which should be on the backdrop
            await page.mouse.click(5, 5)
            await page.wait_for_timeout(500)

            # Also try escape again
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(500)
    except Exception:
        pass

    # Try specific close button selectors
    close_selectors = [
        'button[aria-label*="close" i]',
        'button[aria-label*="dismiss" i]',
        '[class*="close" i]:not(input)',
        'button:has-text("×")',
        'button:has-text("Close")',
        'button:has-text("No thanks")',
        'button:has-text("Skip")',
    ]

    for selector in close_selectors:
        try:
            element = await page.query_selector(selector)
            if element and await element.is_visible():
                await element.click()
                await page.wait_for_timeout(500)
                print(f"    [popup] Clicked {selector}")
                # Check if modal is gone
                modal = await page.query_selector('[role="dialog"]:visible')
                if not modal:
                    return
        except Exception:
            continue

    # Special handling for Google Sign-in iframe
    try:
        google_iframe = await page.query_selector('iframe[src*="accounts.google.com"]')
        if google_iframe:
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(500)
            print(f"    [popup] Pressed Escape to dismiss Google Sign-in")
    except Exception:
        pass


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
    # First, try to dismiss any popups (Google Sign-in, etc.) that may block the challenge
    await dismiss_popups(page)

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

    initial_url = page.url

    for attempt in range(max_attempts):
        # Wait for potential iframe to load
        await page.wait_for_timeout(2000)

        # Check if URL has changed (redirected after solving)
        if page.url != initial_url and "challenge" not in page.url.lower():
            print(f"    [turnstile] URL changed to {page.url[:60]}... - challenge solved")
            return True

        # Check if we're on a Cloudflare challenge page by looking for specific elements
        # Don't just check for "challenge" text as it may appear in JS/footer even after solving
        challenge_indicators = await page.query_selector_all('text=Verify you are human, text=checking your browser, text=needs to review')
        if not challenge_indicators:
            # Also check for the checkbox widget itself
            checkbox_present = await page.query_selector('input[type="checkbox"]:not([style*="display: none"])')
            verify_text = await page.query_selector('text=Verify you are human')
            if not checkbox_present and not verify_text:
                # No visible challenge elements, we're good
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
                    candidate_iframes = []
                    for idx, iframe in enumerate(all_iframes):
                        src = await iframe.get_attribute('src') or ''
                        title = await iframe.get_attribute('title') or ''
                        name = await iframe.get_attribute('name') or ''
                        print(f"      iframe[{idx}]: src={src[:80]}... title={title} name={name}")
                        # Check if this looks like a Turnstile iframe
                        if 'cloudflare' in src.lower() or 'turnstile' in src.lower() or 'challenge' in title.lower():
                            iframe_element = iframe
                            matched_selector = f"iframe[{idx}] (cloudflare match)"
                            break
                        # Also consider iframes with empty/blob src as potential Turnstile (they often load dynamically)
                        # Skip known non-Turnstile iframes like Google Sign-in
                        if 'google' not in src.lower() and 'facebook' not in src.lower():
                            if not src or src.startswith('blob:') or src == 'about:blank':
                                candidate_iframes.append((idx, iframe))

                    # If no explicit cloudflare match, try candidate iframes with empty src
                    if not iframe_element and candidate_iframes:
                        for idx, iframe in candidate_iframes:
                            box = await iframe.bounding_box()
                            if box and box['width'] > 50 and box['height'] > 30:  # Reasonable size for Turnstile widget
                                iframe_element = iframe
                                matched_selector = f"iframe[{idx}] (empty-src candidate, {box['width']:.0f}x{box['height']:.0f})"
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

            # Wait for challenge to process - need longer wait for Cloudflare verification
            await page.wait_for_timeout(5000)

            # Check if challenge was solved - prefer URL change detection
            if page.url != initial_url and "challenge" not in page.url.lower():
                print(f"    [turnstile] Challenge solved on attempt {attempt + 1} (URL changed)")
                return True

            # Check if the verify text/checkbox disappeared
            verify_text = await page.query_selector('text=Verify you are human')
            if not verify_text:
                print(f"    [turnstile] Challenge solved on attempt {attempt + 1} (verify element gone)")
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

        # Dismiss any popups (email signup modal, etc.) that may block job listings
        await dismiss_popups(page)

        # Wait for job cards to appear - try multiple selector patterns
        # ZipRecruiter's HTML structure changes periodically
        job_card_selectors = [
            'article[id^="job-card-"]',  # Current structure as of 2024: article elements with id="job-card-XXX"
            'article[data-testid="job-card"]',
            'div[data-testid="job-card"]',
            'article.job_result',  # Legacy selector
            '.job_result_item',
            '.job-listing',
            'div[class*="JobCard"]',
            'li[class*="job"]',
        ]

        job_cards_found = False
        matched_selector = None

        for selector in job_card_selectors:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    matched_selector = selector
                    job_cards_found = True
                    print(f"  [ziprecruiter] Found {count} job cards via '{selector}'")
                    break
            except Exception:
                continue

        if not job_cards_found:
            # Save debug screenshot and log info
            try:
                title = await page.title()
                content = await page.content()

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
                    # Debug: print available element types
                    for test_sel in ['article', 'div[class*="job"]', 'li', 'a[href*="job"]']:
                        try:
                            count = await page.locator(test_sel).count()
                            if count > 0:
                                print(f"    Debug: Found {count} '{test_sel}' elements")
                        except Exception:
                            pass
            except Exception:
                print(f"  [ziprecruiter] No job cards found for '{search_term}'")
            return jobs

        # Get job cards using the matched selector
        job_cards = await page.locator(matched_selector).all()

        for card in job_cards[:50]:  # Limit to 50 per search
            try:
                # Title is inside h2 element (current ZipRecruiter structure)
                # Note: The title is inside a button, not a link - so we just extract text
                title = ""
                link = ""
                for title_sel in ['h2', 'a[data-testid="job-card-title"]', 'h2 a', '.job_title a']:
                    title_el = card.locator(title_sel)
                    if await title_el.count() > 0:
                        title = await title_el.first.inner_text()
                        # Try to get href if it's a link
                        try:
                            link = await title_el.first.get_attribute('href') or ""
                        except Exception:
                            pass
                        break

                # Company: data-testid="job-card-company"
                company = ""
                company_link = ""
                for company_sel in ['a[data-testid="job-card-company"]', 'a[data-testid="employer-name"]', 'a.company_name']:
                    company_el = card.locator(company_sel)
                    if await company_el.count() > 0:
                        company = await company_el.first.inner_text()
                        try:
                            company_link = await company_el.first.get_attribute('href') or ""
                        except Exception:
                            pass
                        break

                # Location: data-testid="job-card-location"
                loc = ""
                for loc_sel in ['a[data-testid="job-card-location"]', 'p[data-testid="job-card-location"]', 'span.job_location']:
                    loc_el = card.locator(loc_sel)
                    if await loc_el.count() > 0:
                        loc = await loc_el.first.inner_text()
                        break

                # For the job URL, if no direct link, construct from card ID
                if not link:
                    try:
                        card_id = await card.get_attribute('id')
                        if card_id and card_id.startswith('job-card-'):
                            job_id = card_id.replace('job-card-', '')
                            link = f"https://www.ziprecruiter.com/jobs/{job_id}"
                    except Exception:
                        pass

                if title and company:
                    jobs.append({
                        "title": title.strip(),
                        "company": company.strip(),
                        "location": loc.strip() if loc else "",
                        "description": "",  # Description not shown in card list
                        "job_url": link,
                        "date_posted": "",
                        "salary": "",
                        "job_type": "",
                        "search_term": search_term,
                        "source_site": "ziprecruiter"
                    })
            except Exception as e:
                continue

        # If no jobs found with card selectors, try extracting from job links directly
        if not jobs:
            print(f"  [ziprecruiter] Trying fallback link extraction...")
            try:
                # Look for job links in the sidebar/list
                job_links = await page.locator('a[href*="/job/"], a[href*="/jobs/"]').all()
                seen_titles = set()
                for link_el in job_links[:50]:
                    try:
                        href = await link_el.get_attribute('href') or ""
                        text = await link_el.inner_text()
                        if text and text.strip() and len(text.strip()) > 5 and text.strip() not in seen_titles:
                            # Skip navigation/filter links
                            if any(skip in text.lower() for skip in ['search', 'filter', 'sort', 'page', 'next', 'prev']):
                                continue
                            seen_titles.add(text.strip())
                            jobs.append({
                                "title": text.strip(),
                                "company": "",  # Not available from link alone
                                "location": "",
                                "description": "",
                                "job_url": href,
                                "date_posted": "",
                                "salary": "",
                                "job_type": "",
                                "search_term": search_term,
                                "source_site": "ziprecruiter"
                            })
                    except Exception:
                        continue
                if jobs:
                    print(f"  [ziprecruiter] Extracted {len(jobs)} jobs from links")
            except Exception as e:
                print(f"  [ziprecruiter] Link extraction failed: {str(e)[:50]}")

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

        # Dismiss any popups first (Google Sign-in, email signup, etc.)
        await dismiss_popups(page)

        # Check if job listings are already visible - if so, skip challenge detection
        job_listings_present = await page.locator('[data-test="jobListing"]').count() > 0

        if not job_listings_present:
            # Check for Cloudflare challenge by looking for actual challenge elements
            # Don't just search for keywords in content as they can appear in JS/footer
            challenge_indicators = await page.query_selector_all('text=Verify you are human, text=checking your browser, input[type="checkbox"]')
            turnstile_iframe = await page.query_selector('iframe[src*="challenges.cloudflare.com"], iframe[src*="turnstile"]')

            if challenge_indicators or turnstile_iframe:
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
                # Title: a[data-test="job-title"]
                title = ""
                link = ""
                title_el = card.locator('a[data-test="job-title"]')
                if await title_el.count() > 0:
                    title = await title_el.first.inner_text()
                    link = await title_el.first.get_attribute('href') or ""

                # Company: The employer name is in a span with class containing "compactEmployerName"
                # There's no data-test="employer-name" attribute
                company = ""
                for company_sel in ['span[class*="compactEmployerName"]', '[data-test="employer-name"]', 'span[class*="EmployerName"]']:
                    company_el = card.locator(company_sel)
                    if await company_el.count() > 0:
                        company = await company_el.first.inner_text()
                        break

                # Location: div[data-test="emp-location"]
                loc = ""
                loc_el = card.locator('[data-test="emp-location"]')
                if await loc_el.count() > 0:
                    loc = await loc_el.first.inner_text()

                # Salary (bonus): div[data-test="detailSalary"]
                salary = ""
                salary_el = card.locator('[data-test="detailSalary"]')
                if await salary_el.count() > 0:
                    salary = await salary_el.first.inner_text()

                if title and company:
                    jobs.append({
                        "title": title.strip(),
                        "company": company.strip(),
                        "location": loc.strip() if loc else "",
                        "description": "",  # Glassdoor doesn't show snippet in search results
                        "job_url": link,
                        "date_posted": "",
                        "salary": salary.strip() if salary else "",
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
