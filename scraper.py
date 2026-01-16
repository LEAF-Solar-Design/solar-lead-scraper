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
    """Check if job description matches our criteria for solar design roles."""
    if not description or pd.isna(description):
        return False

    desc_lower = description.lower()

    # Must have solar/PV context
    has_solar = 'solar' in desc_lower
    has_pv = 'pv' in desc_lower or 'photovoltaic' in desc_lower

    if not (has_solar or has_pv):
        return False

    # Exclude tennis/racquet sports (stringing false positives)
    tennis_terms = ['tennis', 'racquet', 'racket', 'pickleball', 'badminton']
    if any(term in desc_lower for term in tennis_terms):
        return False

    # Exclude field/installation roles (we want designers, not installers)
    installer_terms = [
        'installer', 'installation technician', 'roof lead', 'rooftop',
        'journeyman electrician', 'apprentice electrician', 'lineman', 'lineworker',
        'o&m technician', 'field technician', 'service technician'
    ]
    if any(term in desc_lower for term in installer_terms):
        return False

    # Strong qualification signals - if present with solar/PV, auto-qualify
    strong_signals = [
        'stringing', 'string size', 'string sizing', 'voltage drop',
        'conduit schedule', 'wiring schedule', 'single line', 'one-line',
        'pv design', 'solar design', 'system design'
    ]
    if any(term in desc_lower for term in strong_signals):
        return True

    # Secondary qualification: design tools + solar context
    design_tools = ['autocad', 'auto cad', 'cad', 'helioscope', 'aurora', 'pvsyst']
    design_roles = ['designer', 'drafter', 'design engineer']

    has_design_tool = any(term in desc_lower for term in design_tools)
    has_design_role = any(term in desc_lower for term in design_roles)

    return has_design_tool and has_design_role


def scrape_solar_jobs() -> pd.DataFrame:
    """Scrape solar design/CAD jobs from multiple sources."""

    # Massive search to cast a wide net - strong filters will narrow down
    search_terms = [
        # Core solar design terms
        "solar designer",
        "PV designer",
        "solar design engineer",
        "PV design engineer",
        "solar CAD",
        "PV CAD",
        "photovoltaic designer",

        # Engineering roles
        "solar engineer",
        "PV engineer",
        "solar electrical engineer",
        "renewable energy engineer",
        "solar project engineer",

        # Drafter/technician roles
        "solar drafter",
        "PV drafter",
        "solar CAD technician",
        "electrical drafter solar",

        # Stringing/electrical design specific
        "stringing solar",
        "voltage drop solar",
        "string sizing PV",
        "solar electrical design",
        "PV system design",

        # Tools-based searches
        "AutoCAD solar",
        "helioscope",
        "aurora solar",
        "PVsyst",

        # Broader catches
        "solar energy designer",
        "renewable designer",
        "utility scale solar",
        "commercial solar design",
        "residential solar design",
    ]

    all_jobs = []
    results_per_term = 1000  # 1000 x 37 terms = 37,000 total max

    for term in search_terms:
        print(f"Searching for: {term}")
        try:
            jobs = scrape_jobs(
                site_name=["indeed", "zip_recruiter", "glassdoor"],
                search_term=term,
                location="USA",
                results_wanted=results_per_term,
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

    # Filter by description content
    if 'description' in df.columns:
        before_filter = len(df)
        df = df[df['description'].apply(description_matches)]
        print(f"After filtering: {len(df)} qualified leads (filtered out {before_filter - len(df)})")
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
