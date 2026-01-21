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


@dataclass
class BrowserSearchAttempt:
    """Detailed record of a browser-based search attempt for deep analytics.

    Captures timing, selector matching, Cloudflare handling, and results
    to help diagnose issues with ZipRecruiter and Glassdoor scraping.
    """
    search_term: str
    site: str
    timestamp: str
    success: bool = False
    jobs_found: int = 0
    duration_ms: int = 0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    selectors_tried: list = None
    selector_matched: Optional[str] = None
    cloudflare_detected: bool = False
    cloudflare_solved: Optional[bool] = None
    page_title: Optional[str] = None
    pages_scraped: int = 1

    def __post_init__(self):
        if self.selectors_tried is None:
            self.selectors_tried = []

    def to_dict(self) -> dict:
        return {
            "search_term": self.search_term,
            "site": self.site,
            "timestamp": self.timestamp,
            "success": self.success,
            "jobs_found": self.jobs_found,
            "duration_ms": self.duration_ms,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "selectors_tried": self.selectors_tried if self.selectors_tried else None,
            "selector_matched": self.selector_matched,
            "cloudflare_detected": self.cloudflare_detected,
            "cloudflare_solved": self.cloudflare_solved,
            "page_title": self.page_title,
            "pages_scraped": self.pages_scraped,
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

    # ZipRecruiter-specific: Handle focus lock modal overlay
    # This overlay has class "bg-black bg-opacity-50" and role="presentation"
    try:
        await page.evaluate("""
            () => {
                // Remove focus lock containers (email signup modals)
                document.querySelectorAll('[data-focus-lock-disabled]').forEach(el => {
                    el.remove();
                });
                // Remove any overlay backdrop
                document.querySelectorAll('[role="presentation"][class*="bg-black"], [class*="bg-opacity-50"]').forEach(el => {
                    if (el.classList.contains('fixed') || el.classList.contains('inset-0')) {
                        el.remove();
                    }
                });
                // Remove generic modal containers
                document.querySelectorAll('[class*="modal"][class*="fixed"], [class*="overlay"][class*="fixed"]').forEach(el => {
                    el.remove();
                });
            }
        """)
        await page.wait_for_timeout(300)
    except Exception:
        pass

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

    # Special handling for Google Sign-in iframe/prompt
    try:
        # Google One Tap sign-in appears in an iframe
        google_iframe = await page.query_selector('iframe[src*="accounts.google.com"]')
        if google_iframe:
            # Try to find and click the close button within the iframe, or dismiss it
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(300)

            # Also try to hide/remove the Google iframe container
            # This is more aggressive but sometimes necessary
            await page.evaluate("""
                () => {
                    // Remove Google Sign-in iframes
                    document.querySelectorAll('iframe[src*="accounts.google.com"]').forEach(el => {
                        el.parentElement?.remove() || el.remove();
                    });
                    // Remove Google credential containers
                    document.querySelectorAll('[id*="credential_picker"], [class*="g_id"], [id*="google"]').forEach(el => {
                        if (el.querySelector('iframe') || el.tagName === 'IFRAME') {
                            el.remove();
                        }
                    });
                }
            """)
            await page.wait_for_timeout(300)
            print(f"    [popup] Dismissed Google Sign-in prompt")
    except Exception:
        pass

    # Also dismiss any "Sign up" / "Log in" banners that overlay the content
    try:
        login_banners = await page.query_selector_all('[class*="login" i], [class*="signup" i], [class*="signin" i], [class*="register" i]')
        for banner in login_banners:
            try:
                # Only remove if it looks like an overlay (positioned fixed/absolute with high z-index)
                is_overlay = await page.evaluate("""
                    (el) => {
                        const style = window.getComputedStyle(el);
                        return (style.position === 'fixed' || style.position === 'absolute') &&
                               parseInt(style.zIndex) > 100;
                    }
                """, banner)
                if is_overlay:
                    await page.evaluate("(el) => el.remove()", banner)
                    print(f"    [popup] Removed login/signup overlay")
            except Exception:
                pass
    except Exception:
        pass


async def solve_cloudflare_turnstile(page, max_attempts: int = 3) -> bool:
    """
    Attempt to solve Cloudflare Turnstile challenge.

    Handles two types of Cloudflare challenges:
    1. Checkbox challenge: Shows "Verify you are human" with a checkbox to click
    2. Auto-verification: Shows "Verifying..." while Cloudflare automatically checks

    Args:
        page: Playwright page object
        max_attempts: Maximum number of attempts

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

    # First, check if this is an auto-verification challenge ("Verifying...")
    # These don't require clicking - just waiting for Cloudflare to complete verification
    content = await page.content()
    if "verifying..." in content.lower() or "this may take a few seconds" in content.lower():
        print(f"    [turnstile] Auto-verification detected, waiting for completion...")

        # Wait up to 30 seconds for auto-verification to complete
        for wait_attempt in range(15):
            await page.wait_for_timeout(2000)

            # Check if URL changed (redirected to actual content)
            if page.url != initial_url:
                print(f"    [turnstile] Auto-verification complete (URL changed)")
                return True

            # Check if the verifying text is gone
            new_content = await page.content()
            if "verifying..." not in new_content.lower():
                # Check if we now have job content or if challenge cleared
                has_jobs = await page.locator('article, [class*="job"], [data-test="jobListing"]').count() > 0
                still_challenging = "verify you are human" in new_content.lower() or "needs to review" in new_content.lower()

                if has_jobs:
                    print(f"    [turnstile] Auto-verification complete (jobs visible)")
                    return True
                elif not still_challenging:
                    print(f"    [turnstile] Auto-verification complete (challenge cleared)")
                    return True
                else:
                    # Switched from auto-verify to checkbox challenge
                    print(f"    [turnstile] Auto-verification timed out, falling back to checkbox click")
                    break

            if wait_attempt % 3 == 0:
                print(f"    [turnstile] Still verifying... (waited {(wait_attempt + 1) * 2}s)")

        # If we get here, auto-verification may have failed - continue to checkbox logic

    for attempt in range(max_attempts):
        # Wait for potential iframe to load
        await page.wait_for_timeout(2000)

        # Check if URL has changed (redirected after solving)
        if page.url != initial_url and "challenge" not in page.url.lower():
            print(f"    [turnstile] URL changed to {page.url[:60]}... - challenge solved")
            return True

        # Re-check for auto-verification state (it might have switched)
        content = await page.content()
        if "verifying..." in content.lower():
            print(f"    [turnstile] Attempt {attempt + 1}: Auto-verification in progress, waiting...")
            await page.wait_for_timeout(5000)
            if page.url != initial_url:
                return True
            continue

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
                            await page.wait_for_timeout(5000)

                            # Check if Turnstile is gone (more reliable than text check)
                            turnstile_count = await page.locator('iframe[src*="challenges.cloudflare.com"], iframe[src*="turnstile"], .cf-turnstile').count()
                            verify_elem = await page.query_selector('text=Verify you are human')
                            if turnstile_count == 0 and not verify_elem:
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
                                    await page.wait_for_timeout(5000)

                                    # Check if Turnstile is gone
                                    turnstile_count = await page.locator('iframe[src*="challenges.cloudflare.com"], iframe[src*="turnstile"], .cf-turnstile').count()
                                    verify_elem = await page.query_selector('text=Verify you are human')
                                    if turnstile_count == 0 and not verify_elem:
                                        print(f"    [turnstile] Challenge solved via checkbox click on attempt {attempt + 1}")
                                        return True
                                    break
                        except Exception:
                            continue

                    # Ultimate fallback: find the Turnstile widget and click the checkbox
                    # The Turnstile widget has a checkbox on the left side within the widget box
                    try:
                        # Use JavaScript to find the Turnstile widget checkbox precisely
                        # The checkbox is inside a label element within the widget
                        widget_info = await page.evaluate("""
                            () => {
                                // Look for the Turnstile checkbox - it's typically in a label with specific structure
                                // Method 1: Find by the checkbox input directly
                                const checkbox = document.querySelector('input[type="checkbox"][name*="cf"], input[type="checkbox"][id*="cf"]');
                                if (checkbox) {
                                    const rect = checkbox.getBoundingClientRect();
                                    if (rect.width > 0 && rect.height > 0) {
                                        return { x: rect.x + rect.width/2, y: rect.y + rect.height/2, method: 'checkbox' };
                                    }
                                }

                                // Method 2: Find the label element containing the checkbox visual
                                // Cloudflare Turnstile uses a custom-styled checkbox
                                const labels = document.querySelectorAll('label');
                                for (const label of labels) {
                                    const text = label.innerText || '';
                                    if (text.includes('Verify you are human')) {
                                        const rect = label.getBoundingClientRect();
                                        // Checkbox is at the left edge of the label, about 15-20px in
                                        return { x: rect.x + 18, y: rect.y + rect.height/2, method: 'label' };
                                    }
                                }

                                // Method 3: Find the widget container with specific dimensions
                                // Turnstile widget is typically ~300x65 pixels
                                const divs = document.querySelectorAll('div');
                                for (const div of divs) {
                                    const rect = div.getBoundingClientRect();
                                    const style = window.getComputedStyle(div);
                                    // Look for widget-like dimensions with border/background
                                    if (rect.width > 180 && rect.width < 400 &&
                                        rect.height > 40 && rect.height < 100 &&
                                        (style.border || style.backgroundColor !== 'rgba(0, 0, 0, 0)')) {
                                        const text = div.innerText || '';
                                        if (text.includes('Verify') && text.includes('human')) {
                                            // Found the widget, checkbox is ~15-20px from left edge
                                            return { x: rect.x + 18, y: rect.y + rect.height/2, method: 'widget-div', width: rect.width, height: rect.height };
                                        }
                                    }
                                }

                                // Method 4: Find any element with exact "Verify you are human" text (not the instruction text above)
                                const allElements = document.querySelectorAll('*');
                                for (const el of allElements) {
                                    // Use textContent to avoid matching partial text
                                    const text = el.textContent || '';
                                    const directText = el.childNodes.length === 1 && el.childNodes[0].nodeType === 3 ? el.childNodes[0].textContent : '';
                                    if (directText && directText.trim() === 'Verify you are human') {
                                        const rect = el.getBoundingClientRect();
                                        // For a text-only element, the checkbox should be to its left
                                        // Get parent rect for more context
                                        const parentRect = el.parentElement ? el.parentElement.getBoundingClientRect() : rect;
                                        return { x: parentRect.x + 18, y: rect.y + rect.height/2, method: 'exact-text' };
                                    }
                                }

                                return null;
                            }
                        """)

                        if widget_info:
                            click_x = widget_info['x']
                            click_y = widget_info['y']
                            method = widget_info.get('method', 'unknown')
                            print(f"    [turnstile] Attempt {attempt + 1}: Found widget via {method}, clicking at ({click_x:.0f}, {click_y:.0f})")
                            await page.mouse.click(click_x, click_y)
                            await page.wait_for_timeout(5000)

                            # Check if challenge was solved
                            verify_gone = await page.query_selector('label:has-text("Verify you are human")') is None
                            url_changed = page.url != initial_url

                            if verify_gone or url_changed:
                                print(f"    [turnstile] Challenge solved via {method} click on attempt {attempt + 1}")
                                return True
                        else:
                            print(f"    [turnstile] Attempt {attempt + 1}: Could not locate Turnstile widget via JS")

                    except Exception as e:
                        print(f"    [turnstile] Widget click error: {str(e)[:50]}")

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


async def fetch_job_description(page, job_url: str, site: str, timeout: int = 10000) -> str:
    """
    Fetch job description by navigating to the job detail page.

    Args:
        page: Playwright page object (will navigate and return)
        job_url: URL of the job posting
        site: Site name for selector logic ('ziprecruiter', 'glassdoor')
        timeout: Max time to wait for description element

    Returns:
        Job description text, or empty string if failed
    """
    if not job_url:
        return ""

    try:
        await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        # Dismiss any popups
        await dismiss_popups(page)

        description = ""

        if site == "ziprecruiter":
            # ZipRecruiter job description selectors
            desc_selectors = [
                '[class*="job_description"]',
                '[data-testid="job-description"]',
                '.jobDescriptionSection',
                '#job-description',
                '[class*="Description"]',
                'div[class*="description"]',
            ]
        elif site == "glassdoor":
            # Glassdoor job description selectors
            # IMPORTANT: [class*="jobDescription"] must come before [class*="JobDetails"]
            # because JobDetails captures the entire panel including header/buttons
            # while jobDescription captures just the description content
            desc_selectors = [
                '[class*="jobDescription"]',  # JobDetails_jobDescription__uW_fK - actual description
                '[data-test="jobDescription"]',
                '.jobDescriptionContent',
                '.desc',
                '[class*="description"]',
                # [class*="JobDetails"] removed - captures entire panel with header/buttons
            ]
        else:
            desc_selectors = ['[class*="description"]', '.description', '#description']

        for selector in desc_selectors:
            try:
                el = page.locator(selector).first
                if await el.count() > 0:
                    description = await el.inner_text()
                    if description and len(description) > 50:
                        break
            except Exception:
                continue

        # Debug: if no description found, log the page title to help diagnose
        if not description:
            try:
                title = await page.title()
                print(f"    [desc] No description found on page: {title[:60]}")
            except Exception:
                pass

        return description.strip()[:5000] if description else ""

    except Exception as e:
        print(f"    [desc] Error fetching {job_url[:50]}: {str(e)[:50]}")
        return ""


async def scrape_ziprecruiter_page(browser, search_term: str, location: str = "USA", debug_dir: str = None, max_descriptions: int = 10, max_pages: int = 1) -> list[dict]:
    """Scrape a single search from ZipRecruiter.

    Args:
        browser: Camoufox browser instance
        search_term: Job search term
        location: Location to search
        debug_dir: Directory for debug screenshots
        max_descriptions: Maximum number of job descriptions to fetch (to limit time)
        max_pages: Maximum number of result pages to scrape (default 1, max ~39 available)
    """
    jobs = []
    page = None
    all_job_cards = []  # Store cards from all pages for description fetching

    # Base search URL (page number will be appended)
    base_url = f"https://www.ziprecruiter.com/jobs-search?search={search_term.replace(' ', '+')}&location={location}"

    try:
        page = await browser.new_page()

        # Loop through pages
        for page_num in range(1, max_pages + 1):
            search_url = f"{base_url}&page={page_num}"
            if page_num > 1:
                print(f"  [ziprecruiter] Loading page {page_num}...")

            await page.goto(search_url, wait_until="domcontentloaded")

            # Wait for page load
            await page.wait_for_timeout(3000)

            # Check for and attempt to solve Cloudflare Turnstile challenge (only on first page typically)
            if page_num == 1:
                content = await page.content()
                # Check for Turnstile challenge - look for actual challenge elements, not just text
                has_turnstile = await page.locator('iframe[src*="challenges.cloudflare.com"], iframe[src*="turnstile"], .cf-turnstile, [data-turnstile]').count() > 0
                has_verify_text = "verify you are human" in content.lower()

                if has_turnstile or has_verify_text:
                    print(f"  [ziprecruiter] Cloudflare challenge detected, attempting to solve...")
                    solved = await solve_cloudflare_turnstile(page)
                    if solved:
                        # After solving Turnstile, we need to wait for the page to actually load results
                        # Sometimes ZipRecruiter redirects, sometimes it shows results on same page
                        await page.wait_for_timeout(3000)

                        # Check if we now have job cards - if not, try reloading the page
                        job_card_check = await page.locator('article[id^="job-card-"], article[data-testid="job-card"]').count()
                        if job_card_check == 0:
                            print(f"  [ziprecruiter] No job cards after Turnstile, reloading page...")
                            await page.reload(wait_until="domcontentloaded")
                            await page.wait_for_timeout(3000)

                            # Check for Turnstile again after reload
                            has_turnstile_again = await page.locator('iframe[src*="challenges.cloudflare.com"], iframe[src*="turnstile"], .cf-turnstile').count() > 0
                            if has_turnstile_again:
                                print(f"  [ziprecruiter] Turnstile reappeared after reload, solving again...")
                                await solve_cloudflare_turnstile(page)
                                await page.wait_for_timeout(3000)
                    else:
                        if debug_dir:
                            safe_term = search_term.replace(' ', '_')[:20]
                            screenshot_path = f"{debug_dir}/ziprecruiter_{safe_term}_challenge.png"
                            try:
                                await page.screenshot(path=screenshot_path, full_page=True)
                            except Exception:
                                pass
                        print(f"  [ziprecruiter] Could not solve Cloudflare challenge for '{search_term}'")
                        return jobs

            # Dismiss any popups
            await dismiss_popups(page)

            # Wait for job cards to appear - try multiple selector patterns
            job_card_selectors = [
                'article[id^="job-card-"]',
                'article[data-testid="job-card"]',
                'div[data-testid="job-card"]',
                'article.job_result',
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
                        if page_num == 1:
                            print(f"  [ziprecruiter] Found {count} job cards via '{selector}'")
                        break
                except Exception:
                    continue

            if not job_cards_found:
                if page_num == 1:
                    # Save debug screenshot and log info only for first page failure
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

                        # Check for actual Turnstile elements, not just text containing "challenge"
                        has_turnstile = await page.locator('iframe[src*="challenges.cloudflare.com"], iframe[src*="turnstile"], .cf-turnstile, [data-turnstile]').count() > 0
                        has_verify = "verify you are human" in content.lower()

                        if has_turnstile or has_verify:
                            print(f"  [ziprecruiter] Cloudflare Turnstile still present for '{search_term}'")
                        elif "captcha" in content.lower():
                            print(f"  [ziprecruiter] CAPTCHA detected for '{search_term}'")
                        elif "blocked" in content.lower() or "access denied" in content.lower():
                            print(f"  [ziprecruiter] Access blocked for '{search_term}'")
                        else:
                            print(f"  [ziprecruiter] No job cards found for '{search_term}' (title: {title[:50]})")
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
                else:
                    # No more pages with results, stop pagination
                    print(f"  [ziprecruiter] No more results after page {page_num - 1}")
                    break

            # Get job cards using the matched selector
            job_cards = await page.locator(matched_selector).all()
            jobs_before = len(jobs)

            for card in job_cards[:50]:  # Limit to 50 per page
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
                            "description": "",  # Will be fetched below
                            "job_url": link,
                            "date_posted": "",
                            "salary": "",
                            "job_type": "",
                            "search_term": search_term,
                            "source_site": "ziprecruiter"
                        })
                except Exception as e:
                    continue

            # Report jobs found on this page
            jobs_on_page = len(jobs) - jobs_before
            if page_num > 1 or max_pages > 1:
                print(f"  [ziprecruiter] Page {page_num}: {jobs_on_page} jobs (total: {len(jobs)})")

            # Small delay between pages to avoid rate limiting
            if page_num < max_pages:
                await page.wait_for_timeout(1000)

        # End of pagination loop - now fetch descriptions
        # Go back to page 1 for description fetching (most relevant results)
        if max_pages > 1 and len(jobs) > 0:
            await page.goto(f"{base_url}&page=1", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            await dismiss_popups(page)

        # Re-fetch job cards on current page for description extraction
        job_cards = await page.locator(matched_selector).all() if matched_selector else []

        # Fetch descriptions by clicking job cards and extracting from right panel
        # ZipRecruiter uses a two-pane layout where clicking a card shows the description
        if jobs and job_cards:
            jobs_to_fetch = min(len(jobs), len(job_cards), max_descriptions)
            print(f"  [ziprecruiter] Fetching descriptions for {jobs_to_fetch} jobs via panel...")

            # Set wider viewport to ensure two-pane layout (desktop mode)
            await page.set_viewport_size({"width": 1920, "height": 1080})
            await page.wait_for_timeout(500)

            # Dismiss any modal overlays BEFORE clicking job cards
            await dismiss_popups(page)
            await page.wait_for_timeout(500)

            fetched_count = 0
            for i in range(jobs_to_fetch):
                try:
                    # Click on the job card to open description panel
                    # Use force=True to bypass any remaining overlay elements
                    card = job_cards[i]
                    try:
                        await card.click(timeout=5000)
                    except Exception:
                        # If normal click fails, try force click
                        await card.click(force=True, timeout=5000)
                    await page.wait_for_timeout(2000)  # Wait for panel to load

                    # Dismiss any popups that appeared
                    await dismiss_popups(page)

                    # Extract description from the right panel
                    # ZipRecruiter structure: h2 "Job description" followed by div with content
                    description = ""
                    try:
                        description = await page.evaluate("""
                            () => {
                                // Find the "Job description" header (case insensitive)
                                const h2s = document.querySelectorAll('h2');
                                for (const h2 of h2s) {
                                    const headerText = (h2.innerText || '').toLowerCase().trim();
                                    if (headerText === 'job description') {
                                        // Get the next sibling DIV which contains the description
                                        const descDiv = h2.nextElementSibling;
                                        if (descDiv && descDiv.innerText && descDiv.innerText.length > 100) {
                                            return descDiv.innerText.trim();
                                        }
                                        // If no immediate sibling, try parent's children after h2
                                        const parent = h2.parentElement;
                                        if (parent) {
                                            const children = Array.from(parent.children);
                                            const h2Index = children.indexOf(h2);
                                            for (let i = h2Index + 1; i < children.length; i++) {
                                                const child = children[i];
                                                if (child.innerText && child.innerText.length > 100) {
                                                    return child.innerText.trim();
                                                }
                                            }
                                        }
                                    }
                                }
                                return '';
                            }
                        """)
                    except Exception:
                        pass

                    if description:
                        jobs[i]["description"] = description
                        fetched_count += 1

                    await page.wait_for_timeout(500)  # Small delay between clicks

                except Exception as e:
                    continue

            print(f"  [ziprecruiter] Fetched {fetched_count}/{jobs_to_fetch} descriptions")

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


async def scrape_glassdoor_page(browser, search_term: str, location: str = "United States", debug_dir: str = None, max_descriptions: int = 10, max_pages: int = 1) -> list[dict]:
    """Scrape a single search from Glassdoor.

    Args:
        browser: Camoufox browser instance
        search_term: Job search term
        location: Location to search
        debug_dir: Directory for debug screenshots
        max_descriptions: Maximum number of job descriptions to fetch (to limit time)
        max_pages: Maximum number of pages to load via "Show more jobs" button (default 1)
    """
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

        # Pagination: click "Show more jobs" button to load additional pages
        # Glassdoor shows ~30 jobs per page
        if max_pages > 1:
            for page_num in range(2, max_pages + 1):
                try:
                    # Look for the "Show more jobs" button
                    show_more_btn = page.locator('button:has-text("Show more jobs"), button:has-text("Load more"), [data-test="load-more"]')
                    if await show_more_btn.count() > 0 and await show_more_btn.first.is_visible():
                        jobs_before = await page.locator('[data-test="jobListing"]').count()

                        # Scroll to and click the button
                        await show_more_btn.first.scroll_into_view_if_needed()
                        await page.wait_for_timeout(500)
                        await show_more_btn.first.click()

                        # Wait for new jobs to load
                        await page.wait_for_timeout(3000)
                        await dismiss_popups(page)

                        jobs_after = await page.locator('[data-test="jobListing"]').count()
                        print(f"  [glassdoor] Page {page_num}: {jobs_after - jobs_before} new jobs (total: {jobs_after})")

                        if jobs_after == jobs_before:
                            # No new jobs loaded, stop pagination
                            print(f"  [glassdoor] No more jobs to load after page {page_num - 1}")
                            break
                    else:
                        # Button not found or not visible, stop pagination
                        print(f"  [glassdoor] 'Show more' button not available after page {page_num - 1}")
                        break
                except Exception as e:
                    print(f"  [glassdoor] Pagination error on page {page_num}: {str(e)[:50]}")
                    break

        # Get job cards
        job_cards = await page.locator('[data-test="jobListing"]').all()

        # Limit based on pagination - 30 jobs per page max
        max_jobs_to_process = min(len(job_cards), max_pages * 30)
        for card in job_cards[:max_jobs_to_process]:
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
                        "description": "",  # Will be fetched below
                        "job_url": link,
                        "date_posted": "",
                        "salary": salary.strip() if salary else "",
                        "job_type": "",
                        "search_term": search_term,
                        "source_site": "glassdoor"
                    })
            except Exception:
                continue

        # Fetch descriptions for top jobs (limit to avoid excessive time)
        if jobs:
            jobs_to_fetch = min(len(jobs), max_descriptions)
            print(f"  [glassdoor] Fetching descriptions for {jobs_to_fetch} jobs...")
            desc_page = await browser.new_page()
            try:
                for i in range(jobs_to_fetch):
                    if jobs[i]["job_url"]:
                        try:
                            # Make URL absolute if needed
                            job_url = jobs[i]["job_url"]
                            if job_url.startswith("/"):
                                job_url = f"https://www.glassdoor.com{job_url}"
                            desc = await fetch_job_description(desc_page, job_url, "glassdoor")
                            if desc:
                                jobs[i]["description"] = desc
                            await desc_page.wait_for_timeout(1000)  # Small delay between fetches
                        except Exception:
                            continue
            finally:
                await desc_page.close()

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
) -> tuple[pd.DataFrame, list[BrowserSearchError], list[BrowserSearchAttempt]]:
    """
    Scrape Cloudflare-protected job sites using Camoufox browser.

    Args:
        search_terms: List of job search terms
        sites: Which sites to scrape ('ziprecruiter', 'glassdoor'). Default: both.
        debug_screenshots: If True, save screenshots when no results found (for CI debugging)

    Returns:
        Tuple of (DataFrame of jobs, list of errors, list of search attempts for analytics)
    """
    if not CAMOUFOX_AVAILABLE:
        print("[Camoufox] camoufox not installed - skipping browser-based scraping")
        return pd.DataFrame(), [], []

    if sites is None:
        sites = ['ziprecruiter', 'glassdoor']

    all_jobs = []
    errors = []
    search_attempts = []  # Track detailed analytics for each search

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
                    import time
                    start_time = time.time()
                    attempt = BrowserSearchAttempt(
                        search_term=term,
                        site="ziprecruiter",
                        timestamp=datetime.now().isoformat(),
                    )
                    try:
                        jobs = await scrape_ziprecruiter_page(browser, term, debug_dir=debug_dir)
                        attempt.duration_ms = int((time.time() - start_time) * 1000)
                        if jobs:
                            all_jobs.extend(jobs)
                            attempt.success = True
                            attempt.jobs_found = len(jobs)
                            print(f"  [ziprecruiter] Found {len(jobs)} jobs")
                        else:
                            # No results is still technically a success (site responded)
                            attempt.success = True
                            attempt.jobs_found = 0
                            print(f"  [ziprecruiter] No results")
                    except Exception as e:
                        attempt.duration_ms = int((time.time() - start_time) * 1000)
                        error_msg = str(e)[:500]
                        attempt.success = False
                        attempt.error_type = "browser_error"
                        attempt.error_message = error_msg
                        # Check for Cloudflare indicators
                        error_lower = str(e).lower()
                        if "cloudflare" in error_lower or "turnstile" in error_lower or "captcha" in error_lower:
                            attempt.cloudflare_detected = True
                            attempt.cloudflare_solved = False
                        print(f"  [ziprecruiter] Error: {error_msg[:100]}")
                        errors.append(BrowserSearchError(
                            search_term=term,
                            site="ziprecruiter",
                            error_type="browser_error",
                            error_message=error_msg,
                            timestamp=datetime.now().isoformat()
                        ))
                    search_attempts.append(attempt)

                # Small delay between sites
                await asyncio.sleep(2)

                # Scrape Glassdoor
                if 'glassdoor' in sites:
                    import time
                    start_time = time.time()
                    attempt = BrowserSearchAttempt(
                        search_term=term,
                        site="glassdoor",
                        timestamp=datetime.now().isoformat(),
                    )
                    try:
                        jobs = await scrape_glassdoor_page(browser, term, debug_dir=debug_dir)
                        attempt.duration_ms = int((time.time() - start_time) * 1000)
                        if jobs:
                            all_jobs.extend(jobs)
                            attempt.success = True
                            attempt.jobs_found = len(jobs)
                            print(f"  [glassdoor] Found {len(jobs)} jobs")
                        else:
                            attempt.success = True
                            attempt.jobs_found = 0
                            print(f"  [glassdoor] No results")
                    except Exception as e:
                        attempt.duration_ms = int((time.time() - start_time) * 1000)
                        error_msg = str(e)[:500]
                        attempt.success = False
                        attempt.error_type = "browser_error"
                        attempt.error_message = error_msg
                        error_lower = str(e).lower()
                        if "cloudflare" in error_lower or "turnstile" in error_lower or "captcha" in error_lower:
                            attempt.cloudflare_detected = True
                            attempt.cloudflare_solved = False
                        print(f"  [glassdoor] Error: {error_msg[:100]}")
                        errors.append(BrowserSearchError(
                            search_term=term,
                            site="glassdoor",
                            error_type="browser_error",
                            error_message=error_msg,
                            timestamp=datetime.now().isoformat()
                        ))
                    search_attempts.append(attempt)

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
        return df, errors, search_attempts

    return pd.DataFrame(), errors, search_attempts


def run_camoufox_scraper(search_terms: list[str], sites: list[str] = None, debug_screenshots: bool = None) -> tuple[pd.DataFrame, list[dict], list[dict]]:
    """
    Synchronous wrapper for the async Camoufox scraper.

    Args:
        search_terms: List of job search terms
        sites: Which sites to scrape
        debug_screenshots: If True, save screenshots when no results found.
                          If None, auto-detect from CAMOUFOX_DEBUG env var.

    Returns:
        Tuple of (DataFrame of jobs, list of error dicts, list of search attempt dicts for analytics)
    """
    if not CAMOUFOX_AVAILABLE:
        print("[Camoufox] camoufox not available - install with: pip install camoufox && camoufox fetch")
        return pd.DataFrame(), [], []

    # Auto-detect debug mode from environment if not specified
    if debug_screenshots is None:
        debug_screenshots = os.environ.get("CAMOUFOX_DEBUG", "0") == "1"

    try:
        df, errors, search_attempts = asyncio.run(scrape_with_camoufox(search_terms, sites, debug_screenshots=debug_screenshots))
        return df, [e.to_dict() for e in errors], [a.to_dict() for a in search_attempts]
    except Exception as e:
        print(f"[Camoufox] Error running scraper: {str(e)[:200]}")
        return pd.DataFrame(), [{
            "search_term": "*",
            "site": "camoufox",
            "error_type": "fatal",
            "error_message": str(e)[:500],
            "timestamp": datetime.now().isoformat()
        }], []


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


async def test_description_fetching():
    """Test that job description fetching works correctly."""
    if not CAMOUFOX_AVAILABLE:
        print("Camoufox not installed")
        return

    import os
    os.makedirs("debug_screenshots", exist_ok=True)

    print("=" * 60)
    print("Testing Job Description Fetching")
    print("=" * 60)

    async with AsyncCamoufox(
        headless=True,
        humanize=True,
        disable_coop=True,
    ) as browser:
        # Test full scrape with descriptions for Glassdoor
        print("\n--- Testing Glassdoor (with descriptions) ---")
        jobs = await scrape_glassdoor_page(
            browser,
            search_term="solar designer",
            debug_dir="debug_screenshots",
            max_descriptions=3  # Fetch only 3 for quick testing
        )

        print(f"\nGlassdoor Results: {len(jobs)} jobs found")
        jobs_with_desc = [j for j in jobs if j.get("description")]
        print(f"Jobs with descriptions: {len(jobs_with_desc)}")

        for i, job in enumerate(jobs[:5]):
            print(f"\n  Job {i+1}: {job['title'][:50]}")
            print(f"    Company: {job['company']}")
            print(f"    URL: {job['job_url'][:60]}..." if job['job_url'] else "    URL: (none)")
            desc_preview = job['description'][:150] + "..." if len(job.get('description', '')) > 150 else job.get('description', '(none)')
            print(f"    Description: {desc_preview}")

        # Test full scrape with descriptions for ZipRecruiter
        print("\n--- Testing ZipRecruiter (with descriptions) ---")
        jobs = await scrape_ziprecruiter_page(
            browser,
            search_term="solar designer",
            debug_dir="debug_screenshots",
            max_descriptions=3
        )

        print(f"\nZipRecruiter Results: {len(jobs)} jobs found")
        jobs_with_desc = [j for j in jobs if j.get("description")]
        print(f"Jobs with descriptions: {len(jobs_with_desc)}")

        for i, job in enumerate(jobs[:5]):
            print(f"\n  Job {i+1}: {job['title'][:50]}")
            print(f"    Company: {job['company']}")
            print(f"    URL: {job['job_url'][:60]}..." if job['job_url'] else "    URL: (none)")
            desc_preview = job['description'][:150] + "..." if len(job.get('description', '')) > 150 else job.get('description', '(none)')
            print(f"    Description: {desc_preview}")

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


async def debug_ziprecruiter_job_page():
    """Debug ZipRecruiter job card click behavior to find description."""
    if not CAMOUFOX_AVAILABLE:
        print("Camoufox not installed")
        return

    import os
    os.makedirs("debug_screenshots", exist_ok=True)

    print("=" * 60)
    print("Debugging ZipRecruiter Job Card Click Behavior")
    print("=" * 60)

    async with AsyncCamoufox(
        headless=True,
        humanize=True,
        disable_coop=True,
    ) as browser:
        page = await browser.new_page()

        # Set a wide viewport to trigger desktop two-pane layout
        await page.set_viewport_size({"width": 1920, "height": 1080})
        print("Set viewport to 1920x1080 (desktop)")

        search_url = "https://www.ziprecruiter.com/jobs-search?search=solar+designer&location=USA"

        print(f"\n--- Navigating to search page ---")
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)
        await dismiss_popups(page)

        # Check for Turnstile
        if await page.locator('iframe[src*="challenges.cloudflare.com"], iframe[src*="turnstile"]').count() > 0:
            print("  [ziprecruiter] Turnstile challenge detected, solving...")
            await solve_turnstile_challenge(page)
            await page.wait_for_timeout(3000)

        # Screenshot before click
        await page.screenshot(path="debug_screenshots/ziprecruiter_before_click.png", full_page=True)
        print("Saved: debug_screenshots/ziprecruiter_before_click.png")

        # Find job cards
        job_cards = await page.locator('article[id^="job-card-"]').all()
        print(f"Found {len(job_cards)} job cards")

        if not job_cards:
            print("No job cards found")
            await page.close()
            return

        # Examine the first card's structure
        first_card = job_cards[0]
        print("\n--- First card structure ---")

        # Get all links in the card
        links = await first_card.locator('a').all()
        print(f"Links in card: {len(links)}")
        for i, link in enumerate(links[:5]):
            href = await link.get_attribute('href') or "(no href)"
            text = (await link.inner_text())[:30] or "(no text)"
            print(f"  Link {i+1}: {text} -> {href[:60]}...")

        # Check for buttons in the card
        buttons = await first_card.locator('button').all()
        print(f"Buttons in card: {len(buttons)}")
        for i, btn in enumerate(buttons[:5]):
            text = (await btn.inner_text())[:30] or "(no text)"
            btn_class = await btn.get_attribute('class') or "(no class)"
            print(f"  Button {i+1}: '{text}' class={btn_class[:40]}...")

        # Look for any "Quick Apply" or similar links/buttons
        quick_apply = first_card.locator('a[href*="apply"], button:has-text("apply"), a:has-text("apply")')
        if await quick_apply.count() > 0:
            href = await quick_apply.first.get_attribute('href') or "(button, no href)"
            print(f"Found Quick Apply element: {href[:60] if href != '(button, no href)' else href}")

        # Get the clickable title button/element
        # Try multiple selectors for the clickable element
        title_selectors = ['h2 button', 'button h2', 'h2', '[data-testid="job-card-title"]', 'button[class*="job"]']
        title_btn = None
        for sel in title_selectors:
            btn = first_card.locator(sel).first
            if await btn.count() > 0:
                title_btn = btn
                title_text = await btn.inner_text()
                print(f"\nTitle element found via '{sel}': {title_text[:50]}")
                break

        if title_btn:
            # Get URL before click
            url_before = page.url

            # Click the title to open the job detail panel
            print("\n--- Clicking job title to open detail panel ---")

            # Try clicking the entire card first (not just the title)
            try:
                await first_card.click()
                print("Clicked on card element")
            except Exception as e:
                print(f"Card click failed: {e}, trying title button")
                await title_btn.click()

            await page.wait_for_timeout(3000)  # Wait for JS to load

            # Dismiss Google Sign-in and other popups that may have appeared
            print("Dismissing any popups after click...")
            await dismiss_popups(page)
            await page.wait_for_timeout(2000)

            # Check for iframes that might contain job details
            iframes = await page.locator('iframe').all()
            print(f"Found {len(iframes)} iframes on page")
            for i, iframe in enumerate(iframes[:3]):
                src = await iframe.get_attribute('src') or "(no src)"
                print(f"  Iframe {i+1}: {src[:60]}...")

            # Check if URL changed
            url_after = page.url
            print(f"URL before: {url_before[:60]}...")
            print(f"URL after:  {url_after[:60]}...")
            if url_before != url_after:
                print("URL CHANGED - navigated to new page!")

            # Screenshot after click
            await page.screenshot(path="debug_screenshots/ziprecruiter_after_click.png", full_page=True)
            print("Saved: debug_screenshots/ziprecruiter_after_click.png")

            # Check page content for any description-like text
            print("\n--- Checking page structure ---")
            # Look for common job page elements
            structure_selectors = [
                'article',
                'main',
                'section',
                '[role="main"]',
                '[class*="content"]',
                '[class*="body"]',
            ]
            for sel in structure_selectors:
                try:
                    count = await page.locator(sel).count()
                    if count > 0:
                        el = page.locator(sel).first
                        text = await el.inner_text()
                        if len(text) > 200:
                            print(f"  '{sel}' has {len(text)} chars of text")
                            # Show a preview of section content
                            if sel == 'section':
                                preview = text[:500].replace('\n', ' | ')
                                print(f"    Preview: {preview}...")
                except Exception:
                    pass

            # Look for any new elements that might contain description after click
            print("\n--- Searching for description text patterns ---")
            # Get all text blocks that look like job descriptions
            try:
                # Find elements with substantial text that appeared after clicking
                long_text_elements = await page.evaluate("""
                    () => {
                        const results = [];
                        const elements = document.querySelectorAll('div, section, article, aside, p');
                        for (const el of elements) {
                            const text = el.innerText || '';
                            // Look for elements with description-like content
                            if (text.length > 300 && text.length < 10000) {
                                // Check if it contains job-related keywords
                                const lower = text.toLowerCase();
                                if (lower.includes('responsibil') || lower.includes('qualif') ||
                                    lower.includes('require') || lower.includes('experience') ||
                                    lower.includes('skills') || lower.includes('about the')) {
                                    results.push({
                                        tag: el.tagName,
                                        className: el.className || '',
                                        textLength: text.length,
                                        preview: text.substring(0, 200)
                                    });
                                }
                            }
                        }
                        return results.slice(0, 5);
                    }
                """)
                for item in long_text_elements:
                    print(f"  Found <{item['tag']}> class='{item['className'][:50]}' ({item['textLength']} chars)")
                    print(f"    Preview: {item['preview'][:150]}...")
            except Exception as e:
                print(f"  Error searching: {e}")

            # Check for description panel/drawer
            print("\n--- Looking for job description in panel ---")
            desc_selectors = [
                '[class*="job_description"]',
                '[data-testid="job-description"]',
                '[class*="JobDescription"]',
                '[class*="jobDescription"]',
                '.job_description',
                '#job_description',
                '[class*="Description"]:not(button)',
                'div[class*="description"]:not([class*="meta"])',
                '[class*="detail"] [class*="description"]',
                '[class*="drawer"] [class*="description"]',
                '[class*="panel"] [class*="description"]',
                '[class*="modal"] [class*="description"]',
                '[role="dialog"] [class*="description"]',
                'aside [class*="description"]',
                '[class*="sidebar"] [class*="description"]',
            ]

            for sel in desc_selectors:
                try:
                    count = await page.locator(sel).count()
                    if count > 0:
                        el = page.locator(sel).first
                        text = await el.inner_text()
                        if len(text) > 50:
                            text_preview = text[:150].replace('\n', ' ') + "..."
                            print(f"  FOUND '{sel}': {text_preview}")
                except Exception:
                    pass

            # Also look for any element that appeared after clicking
            print("\n--- All classes containing 'descr' or 'detail' ---")
            try:
                classes = await page.evaluate("""
                    () => {
                        const allElements = document.querySelectorAll('*');
                        const classes = new Set();
                        allElements.forEach(el => {
                            if (el.className && typeof el.className === 'string') {
                                el.className.split(' ').forEach(c => {
                                    if (c.toLowerCase().includes('descr') || c.toLowerCase().includes('detail') || c.toLowerCase().includes('drawer') || c.toLowerCase().includes('panel')) {
                                        classes.add(c);
                                    }
                                });
                            }
                        });
                        return Array.from(classes).slice(0, 40);
                    }
                """)
                for c in classes:
                    print(f"  .{c}")
            except Exception as e:
                print(f"  Error: {e}")

        # Alternative approach: Try to find job URLs by looking at all links on page
        print("\n--- Looking for job detail URLs anywhere on page ---")
        all_links = await page.locator('a[href*="/c/"], a[href*="/job/"], a[href*="/jobs/"]').all()
        seen_urls = set()
        for link in all_links[:20]:
            try:
                href = await link.get_attribute('href')
                if href and href not in seen_urls and '/job' in href.lower():
                    seen_urls.add(href)
                    text = (await link.inner_text())[:40] or "(no text)"
                    print(f"  {text}: {href[:70]}...")
            except Exception:
                pass

        # Try navigating to a direct job page with a known format
        print("\n--- Trying alternative job page URL format ---")
        # ZipRecruiter job URLs often look like: /c/Company-Name/Job/Title?jid=xxx
        # Let's try to find one and test it
        test_job_links = await page.locator('a[href*="/c/"][href*="/Job/"]').all()
        if test_job_links:
            test_url = await test_job_links[0].get_attribute('href')
            if test_url:
                full_url = f"https://www.ziprecruiter.com{test_url}" if test_url.startswith('/') else test_url
                print(f"Testing job URL: {full_url[:80]}...")

                # Navigate to the job page
                await page.goto(full_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
                await dismiss_popups(page)

                await page.screenshot(path="debug_screenshots/ziprecruiter_job_page.png", full_page=True)
                print("Saved: debug_screenshots/ziprecruiter_job_page.png")

                # Check for description on this page
                print("\nSearching for description on job page...")
                desc_selectors = [
                    '[class*="job_description"]',
                    '[class*="description"]',
                    '[class*="jobDescription"]',
                    'article',
                    'main',
                    '.job-details',
                    '#job-description',
                ]
                for sel in desc_selectors:
                    try:
                        count = await page.locator(sel).count()
                        if count > 0:
                            el = page.locator(sel).first
                            text = await el.inner_text()
                            if len(text) > 100:
                                print(f"  FOUND '{sel}' ({len(text)} chars): {text[:200].replace(chr(10), ' ')}...")
                    except Exception:
                        pass

        await page.close()

    print("\n" + "=" * 60)
    print("Debug Complete")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        # Debug mode: save screenshots
        import asyncio
        asyncio.run(debug_single_search())
    elif len(sys.argv) > 1 and sys.argv[1] == "--test-descriptions":
        # Test description fetching specifically
        import asyncio
        asyncio.run(test_description_fetching())
    elif len(sys.argv) > 1 and sys.argv[1] == "--debug-ziprecruiter":
        # Debug ZipRecruiter job detail page specifically
        import asyncio
        asyncio.run(debug_ziprecruiter_job_page())
    else:
        # Normal test run - full scrape with descriptions
        print("Running full test scrape (use --test-descriptions for quick test)")
        print("Use --debug for screenshot-only debug mode")
        print()
        test_terms = ["solar designer"]
        df, errors = run_camoufox_scraper(test_terms)
        print(f"\nResults: {len(df)} jobs, {len(errors)} errors")
        if not df.empty:
            # Show description stats
            has_desc = df['description'].apply(lambda x: len(str(x)) > 50 if x else False)
            print(f"Jobs with descriptions: {has_desc.sum()}/{len(df)}")
            print("\nSample jobs:")
            for idx, row in df.head(5).iterrows():
                print(f"\n  {row['title'][:50]}")
                print(f"    Company: {row['company']}")
                print(f"    Source: {row['source_site']}")
                desc = row.get('description', '')
                desc_preview = desc[:100] + "..." if len(str(desc)) > 100 else desc or "(no description)"
                print(f"    Description: {desc_preview}")
