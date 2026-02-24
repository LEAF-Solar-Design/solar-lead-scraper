"""
NABCEP Career Center Scraper

Scrapes job listings from the NABCEP (North American Board of Certified Energy
Practitioners) career center at jobs.nabcep.org.

This is a niche job board focused on renewable energy professionals with NABCEP
certifications. Volume is low (~40-50 jobs total) but highly targeted.

Output format matches the main scraper for downstream processing.
"""

import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup


# NABCEP job board configuration
NABCEP_BASE_URL = "https://jobs.nabcep.org"
NABCEP_JOBS_URL = f"{NABCEP_BASE_URL}/jobs/"

# Categories relevant to solar design (from NABCEP's filter options)
DESIGN_CATEGORIES = [
    "Design/Engineering",
    "Engineering",
    "Consulting",
]

# Search terms to use — specific to solar design roles (avoid broad terms like
# "renewable energy" or generic "solar" that match academic/research/regulatory postings)
NABCEP_SEARCH_TERMS = [
    "solar designer",
    "solar engineer",
    "PV designer",
    "PV engineer",
    "solar design",
    "PV design",
]


@dataclass
class NABCEPJob:
    """Represents a job listing from NABCEP."""
    job_id: str
    title: str
    company: str
    location: str
    job_url: str
    description: str = ""
    date_posted: Optional[str] = None
    salary: Optional[str] = None
    employment_type: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary matching main scraper output format."""
        return {
            "id": self.job_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "job_url": self.job_url,
            "description": self.description,
            "date_posted": self.date_posted,
            "salary": self.salary,
            "site": "nabcep",
        }


def fetch_page(url: str, params: dict = None, timeout: int = 30) -> Optional[BeautifulSoup]:
    """Fetch a page and return parsed BeautifulSoup object.

    Args:
        url: URL to fetch
        params: Optional query parameters
        timeout: Request timeout in seconds

    Returns:
        BeautifulSoup object or None if request failed
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        print(f"[NABCEP] Error fetching {url}: {e}")
        return None


def parse_job_from_link(link, soup) -> Optional[NABCEPJob]:
    """Parse a job listing from a job link element.

    The NABCEP site structure has job links inside div.card-title,
    with the parent div.bti-grid-search-contentarea containing
    the full card with company and location.

    Args:
        link: BeautifulSoup <a> element with job URL
        soup: Full page soup for context

    Returns:
        NABCEPJob object or None if parsing failed
    """
    try:
        job_url = link.get("href", "")
        if not job_url.startswith("http"):
            job_url = NABCEP_BASE_URL + job_url

        # Extract job ID from URL (pattern: /jobs/12345678/title-slug)
        job_id_match = re.search(r"/jobs/(\d+)/", job_url)
        job_id = job_id_match.group(1) if job_id_match else ""

        # Get title from link text
        title = link.get_text(strip=True)

        # Navigate up to find the content area containing company/location
        # Structure: div.bti-grid-search-contentarea > div.card-title > a
        content_area = link.find_parent(class_="bti-grid-search-contentarea")
        if not content_area:
            # Try going up a few levels
            content_area = link.find_parent("div")
            if content_area:
                content_area = content_area.find_parent("div")

        company = ""
        location = ""

        if content_area:
            # Get all text parts from the content area
            text_parts = content_area.get_text(separator="|", strip=True).split("|")
            # Format is typically: Title|Company|Location...
            if len(text_parts) >= 2:
                company = text_parts[1].strip()
            if len(text_parts) >= 3:
                location = text_parts[2].strip()
                # Clean up location - remove trailing ellipsis or extra text
                if "..." in location:
                    location = location.split("...")[0].strip()

        if not title or not job_id:
            return None

        return NABCEPJob(
            job_id=job_id,
            title=title,
            company=company,
            location=location,
            job_url=job_url,
        )

    except Exception as e:
        print(f"[NABCEP] Error parsing job link: {e}")
        return None


def fetch_job_details(job: NABCEPJob) -> NABCEPJob:
    """Fetch full job details from the individual job page.

    Extracts data from JSON-LD structured data which is more reliable
    than parsing the JavaScript-rendered HTML.

    Args:
        job: NABCEPJob with basic info from listing

    Returns:
        NABCEPJob with description populated
    """
    import json

    soup = fetch_page(job.job_url)
    if not soup:
        return job

    try:
        # First try to get data from JSON-LD structured data
        json_ld = soup.find("script", type="application/ld+json")
        if json_ld and json_ld.string:
            data = json.loads(json_ld.string)

            # Extract description (may contain HTML)
            desc_html = data.get("description", "")
            if desc_html:
                # Strip HTML tags to get plain text
                desc_soup = BeautifulSoup(desc_html, "html.parser")
                job.description = desc_soup.get_text(separator=" ", strip=True)[:5000]

            # Extract salary
            base_salary = data.get("baseSalary", {})
            if isinstance(base_salary, dict):
                value = base_salary.get("value", {})
                if isinstance(value, dict):
                    salary_text = value.get("value", "")
                    if salary_text and "$" in str(salary_text):
                        job.salary = str(salary_text)

            # Extract employment type
            emp_type = data.get("employmentType", "")
            if emp_type:
                job.employment_type = emp_type.replace("_", " ").title()

            # Extract date posted
            date_posted = data.get("datePosted", "")
            if date_posted:
                job.date_posted = date_posted

        # Fallback: try to parse from HTML if JSON-LD didn't have description
        if not job.description:
            desc_elem = soup.find(class_="bti-jd-main-container")
            if desc_elem:
                text = desc_elem.get_text(separator=" ", strip=True)
                if len(text) > 100:  # Only use if substantial content
                    job.description = text[:5000]

    except json.JSONDecodeError as e:
        print(f"[NABCEP] JSON parse error for {job.job_url}: {e}")
    except Exception as e:
        print(f"[NABCEP] Error fetching details for {job.job_url}: {e}")

    return job


def search_jobs(keyword: str = "", category: str = "") -> list[NABCEPJob]:
    """Search for jobs on NABCEP with optional keyword and category filters.

    Args:
        keyword: Search keyword (e.g., "solar designer")
        category: Job category filter (e.g., "Design/Engineering")

    Returns:
        List of NABCEPJob objects
    """
    jobs = []
    params = {}

    if keyword:
        params["keywords"] = keyword
    if category:
        params["categories"] = category

    print(f"[NABCEP] Searching: keyword='{keyword}', category='{category}'")

    soup = fetch_page(NABCEP_JOBS_URL, params=params)
    if not soup:
        return jobs

    # Find all links to job pages with numeric IDs
    job_links = soup.find_all("a", href=re.compile(r"/jobs/\d+/"))

    # Deduplicate by URL
    seen_urls = set()
    for link in job_links:
        url = link.get("href", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)

        job = parse_job_from_link(link, soup)
        if job:
            jobs.append(job)

    print(f"[NABCEP] Found {len(jobs)} jobs for search")
    return jobs


def scrape_nabcep(
    search_terms: list[str] = None,
    categories: list[str] = None,
    fetch_details: bool = False,
    delay_between_requests: float = 1.0,
) -> pd.DataFrame:
    """Scrape jobs from NABCEP career center.

    Args:
        search_terms: List of keywords to search. Defaults to NABCEP_SEARCH_TERMS.
        categories: List of categories to filter. Defaults to DESIGN_CATEGORIES.
        fetch_details: If True, fetch full job descriptions (slower).
        delay_between_requests: Seconds to wait between requests.

    Returns:
        DataFrame with columns matching main scraper output:
        - id, title, company, location, job_url, description, date_posted, site
    """
    if search_terms is None:
        search_terms = NABCEP_SEARCH_TERMS
    if categories is None:
        categories = DESIGN_CATEGORIES

    all_jobs = {}  # Use dict to deduplicate by job_id

    # Search by keywords
    for term in search_terms:
        jobs = search_jobs(keyword=term)
        for job in jobs:
            if job.job_id not in all_jobs:
                all_jobs[job.job_id] = job
        time.sleep(delay_between_requests)

    # Search by categories
    for category in categories:
        jobs = search_jobs(category=category)
        for job in jobs:
            if job.job_id not in all_jobs:
                all_jobs[job.job_id] = job
        time.sleep(delay_between_requests)

    print(f"[NABCEP] Total unique jobs found: {len(all_jobs)}")

    # Optionally fetch full details for each job
    if fetch_details and all_jobs:
        print(f"[NABCEP] Fetching details for {len(all_jobs)} jobs...")
        for i, job in enumerate(all_jobs.values()):
            fetch_job_details(job)
            if (i + 1) % 10 == 0:
                print(f"[NABCEP] Fetched details for {i + 1}/{len(all_jobs)} jobs")
            time.sleep(delay_between_requests)

    # Convert to DataFrame
    if not all_jobs:
        return pd.DataFrame(columns=["id", "title", "company", "location", "job_url", "description", "date_posted", "site"])

    df = pd.DataFrame([job.to_dict() for job in all_jobs.values()])

    # Add date_scraped column
    df["date_scraped"] = datetime.now().strftime("%Y-%m-%d")

    return df


def run_nabcep_scraper(fetch_details: bool = False) -> tuple[pd.DataFrame, list[dict]]:
    """Run the NABCEP scraper and return results.

    Args:
        fetch_details: If True, fetch full job descriptions.

    Returns:
        Tuple of (DataFrame with jobs, list of error dicts)
    """
    errors = []

    try:
        print("[NABCEP] Starting NABCEP career center scrape...")
        start_time = time.time()

        df = scrape_nabcep(fetch_details=fetch_details)

        elapsed = time.time() - start_time
        print(f"[NABCEP] Completed in {elapsed:.1f}s. Found {len(df)} jobs.")

        return df, errors

    except Exception as e:
        error = {
            "source": "nabcep",
            "error_type": "scrape_error",
            "error_message": str(e)[:500],
            "timestamp": datetime.now().isoformat(),
        }
        errors.append(error)
        print(f"[NABCEP] Scrape failed: {e}")
        return pd.DataFrame(), errors


# CLI entry point for testing
if __name__ == "__main__":
    import sys

    fetch_details = "--details" in sys.argv

    print("=" * 60)
    print("NABCEP Career Center Scraper - Test Run")
    print("=" * 60)

    df, errors = run_nabcep_scraper(fetch_details=fetch_details)

    if not df.empty:
        print(f"\nResults ({len(df)} jobs):")
        print("-" * 60)
        for _, row in df.iterrows():
            print(f"  {row['title']}")
            print(f"    Company: {row['company']}")
            print(f"    Location: {row['location']}")
            print(f"    URL: {row['job_url']}")
            if row.get('description'):
                print(f"    Description: {row['description'][:100]}...")
            print()
    else:
        print("\nNo jobs found.")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")
