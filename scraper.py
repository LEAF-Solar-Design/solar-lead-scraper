"""
Solar Job Lead Scraper
Finds companies hiring for solar CAD/design roles to use as sales leads.
"""

import re
import urllib.parse
from datetime import datetime
from pathlib import Path

import pandas as pd
from jobspy import scrape_jobs


def generate_linkedin_search_url(company_name: str, job_title: str = None) -> str:
    """Generate a Google search URL for LinkedIn profiles at a company."""
    clean_name = clean_company_name(company_name)
    query = f'site:linkedin.com/in/ "{clean_name}" (solar OR design OR engineering) (manager OR director OR lead)'
    encoded_query = urllib.parse.quote(query)
    return f"https://www.google.com/search?q={encoded_query}"


def generate_linkedin_role_search_url(company_name: str, job_title: str) -> str:
    """Generate a Google search URL for people in the specific role at a company."""
    clean_name = clean_company_name(company_name)
    # Clean up job title - remove special chars, keep core terms
    clean_title = re.sub(r'[^\w\s-]', '', job_title) if job_title else ''
    query = f'site:linkedin.com/in/ "{clean_name}" "{clean_title}"'
    encoded_query = urllib.parse.quote(query)
    return f"https://www.google.com/search?q={encoded_query}"


def generate_linkedin_hiring_search_url(company_name: str) -> str:
    """Generate a Google search URL for recruiters and hiring managers at a company."""
    clean_name = clean_company_name(company_name)
    query = f'site:linkedin.com/in/ "{clean_name}" (recruiter OR "talent acquisition" OR "hiring manager" OR HR OR "human resources")'
    encoded_query = urllib.parse.quote(query)
    return f"https://www.google.com/search?q={encoded_query}"


def generate_linkedin_enduser_search_url(company_name: str, job_title: str) -> str:
    """Generate a Google search URL for end users - people in CAD/design roles at the company."""
    clean_name = clean_company_name(company_name)
    # Search for people who would actually use solar design software
    query = f'site:linkedin.com/in/ "{clean_name}" (designer OR drafter OR "CAD technician" OR "design engineer" OR AutoCAD OR "solar design")'
    encoded_query = urllib.parse.quote(query)
    return f"https://www.google.com/search?q={encoded_query}"


def clean_company_name(name: str) -> str:
    """Clean company name for domain guessing."""
    if not name:
        return ""
    # Remove common suffixes
    name = re.sub(r'\s*(LLC|Inc\.?|Corp\.?|Co\.?|Ltd\.?|L\.L\.C\.?|INC|CORP)\.?\s*$', '', name, flags=re.IGNORECASE)
    # Remove special characters, keep alphanumeric and spaces
    name = re.sub(r'[^\w\s-]', '', name)
    return name.strip()


def guess_domain(company_name: str) -> str:
    """Guess company domain from name. Returns empty string if can't guess."""
    cleaned = clean_company_name(company_name)
    if not cleaned:
        return ""
    # Convert to lowercase, replace spaces with nothing or hyphen
    simple = re.sub(r'\s+', '', cleaned.lower())
    return f"{simple}.com"


def description_matches(description: str) -> bool:
    """Check if job description contains solar/PV AND AutoCAD AND stringing-related terms."""
    if not description or pd.isna(description):
        return False

    desc_lower = description.lower()

    # Must contain solar or PV related terms
    has_solar = any(term in desc_lower for term in [
        'solar', 'pv', 'photovoltaic'
    ])

    # Must contain AutoCAD
    has_autocad = 'autocad' in desc_lower or 'auto cad' in desc_lower

    # Must contain stringing/wiring related terms
    has_stringing = any(term in desc_lower for term in [
        'wiring schematic', 'wiring diagram', 'stringing', 'voltage drop',
        'string design', 'electrical design', 'single line', 'one-line'
    ])

    return has_solar and has_autocad and has_stringing


def scrape_solar_jobs() -> pd.DataFrame:
    """Scrape solar design/CAD jobs from multiple sources."""

    # Broader search terms since we're filtering by description
    search_terms = [
        "solar AutoCAD",
        "PV AutoCAD",
        "solar designer",
        "solar CAD",
        "PV designer",
        "photovoltaic designer",
    ]

    all_jobs = []

    for term in search_terms:
        print(f"Searching for: {term}")
        try:
            jobs = scrape_jobs(
                site_name=["indeed", "zip_recruiter", "glassdoor"],
                search_term=term,
                location="USA",
                results_wanted=100,  # Get more since we'll filter down
                country_indeed="USA",
            )
            if not jobs.empty:
                jobs['search_term'] = term
                all_jobs.append(jobs)
                print(f"  Found {len(jobs)} jobs")
        except Exception as e:
            print(f"  Error searching '{term}': {e}")

    if not all_jobs:
        print("No jobs found!")
        return pd.DataFrame()

    # Combine all results
    df = pd.concat(all_jobs, ignore_index=True)
    print(f"\nTotal jobs found: {len(df)}")

    # Filter by description content - must have solar/PV AND AutoCAD
    if 'description' in df.columns:
        before_filter = len(df)
        df = df[df['description'].apply(description_matches)]
        print(f"After filtering for solar/PV + AutoCAD in description: {len(df)} jobs (filtered out {before_filter - len(df)})")
    else:
        print("Warning: No description column available for filtering")

    return df


def process_jobs(df: pd.DataFrame) -> pd.DataFrame:
    """Process and dedupe jobs, extract company info."""

    if df.empty:
        return df

    # Keep relevant columns
    columns_to_keep = ['company', 'title', 'location', 'job_url']
    available_cols = [c for c in columns_to_keep if c in df.columns]
    df = df[available_cols].copy()

    # Remove rows without company name
    df = df[df['company'].notna() & (df['company'] != '')]

    # Dedupe by company - keep first occurrence
    df = df.drop_duplicates(subset=['company'], keep='first')

    # Add domain guess
    df['domain'] = df['company'].apply(guess_domain)

    # Add scrape date
    df['date_scraped'] = datetime.now().strftime('%Y-%m-%d')

    # Rename columns for clarity
    df = df.rename(columns={'title': 'job_title', 'job_url': 'posting_url'})

    print(f"Unique companies: {len(df)}")

    # Generate Google search URLs for LinkedIn profiles
    df['linkedin_managers'] = df['company'].apply(generate_linkedin_search_url)
    df['linkedin_hiring'] = df['company'].apply(generate_linkedin_hiring_search_url)
    df['linkedin_role'] = df.apply(lambda row: generate_linkedin_role_search_url(row['company'], row['job_title']), axis=1)
    df['google_enduser'] = df.apply(lambda row: generate_linkedin_enduser_search_url(row['company'], row['job_title']), axis=1)

    # Reorder columns
    final_columns = ['company', 'domain', 'job_title', 'location', 'posting_url', 'linkedin_managers', 'linkedin_hiring', 'linkedin_role', 'google_enduser', 'date_scraped']
    df = df[[c for c in final_columns if c in df.columns]]

    return df


def main():
    print("=" * 50)
    print("Solar Job Lead Scraper")
    print("=" * 50)
    print()

    # Scrape jobs
    raw_jobs = scrape_solar_jobs()

    if raw_jobs.empty:
        print("No jobs to process. Exiting.")
        return

    # Process and dedupe
    leads = process_jobs(raw_jobs)

    if leads.empty:
        print("No leads after processing. Exiting.")
        return

    # Save to CSV
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"solar_leads_{timestamp}.csv"

    leads.to_csv(output_file, index=False)

    print()
    print("=" * 50)
    print(f"Saved {len(leads)} leads to: {output_file}")
    print("=" * 50)

    # Preview first few
    print("\nPreview of leads:")
    print(leads.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
