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


# Company blocklist - known false positive industries
# Aerospace/defense companies use "solar" for spacecraft solar panels
# Semiconductor companies use "CAD" for chip design tools
COMPANY_BLOCKLIST = {
    # Aerospace/Defense
    'boeing', 'northrop grumman', 'lockheed', 'lockheed martin',
    'raytheon', 'spacex', 'blue origin', 'general dynamics',
    'bae systems', 'l3harris', 'leidos', 'huntington ingalls',
    'rtx', 'rtx corporation', 'sierra nevada corporation',
    # Semiconductor
    'intel', 'nvidia', 'amd', 'qualcomm', 'broadcom',
    'texas instruments', 'micron', 'applied materials',
    'lam research', 'kla', 'asml', 'marvell', 'microchip',
}


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


def description_matches(description: str, company_name: str = None) -> bool:
    """Check if job description matches our criteria for solar design roles."""
    # Company blocklist check FIRST (before any description analysis)
    if company_name:
        company_lower = company_name.lower()
        for blocked in COMPANY_BLOCKLIST:
            if blocked in company_lower:
                return False

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

    # Exclude space/aerospace/satellite context (solar panels on spacecraft)
    space_terms = [
        'spacecraft', 'satellite', 'space system', 'aerospace', 'starlink',
        'orbit', 'launch vehicle', 'avionics', 'space exploration'
    ]
    if any(term in desc_lower for term in space_terms):
        return False

    # Exclude semiconductor/chip design (different kind of CAD)
    semiconductor_terms = [
        'semiconductor', 'rtl', 'asic', 'fpga', 'vlsi', 'chip design',
        'physical verification', 'synthesis', 'place and route', 'foundry',
        'wafer', 'silicon', 'integrated circuit', 'ic design'
    ]
    if any(term in desc_lower for term in semiconductor_terms):
        return False

    # Exclude field/installation roles (we want designers, not installers)
    installer_terms = [
        'installer', 'installation technician', 'roof lead', 'rooftop',
        'journeyman electrician', 'apprentice electrician', 'lineman', 'lineworker',
        'o&m technician', 'field technician', 'service technician',
        'field service', 'commissioning technician', 'maintenance technician',
        'solar technician', 'pv technician', 'array supervisor',
        # Added in Phase 2 - installer false positives
        'stringer',           # Tennis/racquet AND solar stringing labor
        'roofer',             # Roofing labor, not design
        'foreman',            # Construction supervision
        'crew lead',          # Installation crew supervision
        'panel installer',    # Explicit installer role
    ]
    if any(term in desc_lower for term in installer_terms):
        return False

    # Exclude sales/marketing roles
    sales_terms = [
        'sales director', 'sales manager', 'marketing director', 'marketing manager',
        'account executive', 'business development', 'sales representative',
        'sales team', 'sales & marketing', 'sales and marketing',
        'sales consultant', 'sales engineer', 'sales specialist',
        'account manager', 'territory manager'
    ]
    if any(term in desc_lower for term in sales_terms):
        return False

    # Exclude management/non-design roles
    mgmt_terms = [
        'project manager', 'construction manager', 'operations manager',
        'program manager', 'development manager', 'site manager',
        'general manager', 'director of operations', 'vp ', 'vice president',
        'chief ', 'ceo', 'cto', 'cfo'
    ]
    if any(term in desc_lower for term in mgmt_terms):
        return False

    # Exclude non-design engineering roles
    other_eng_terms = [
        'application engineer', 'applications engineer', 'technical sales', 'technical support',
        'field engineer', 'commissioning engineer', 'product engineer',
        'project engineer', 'construction engineer', 'site engineer',
        'structural engineer', 'civil engineer', 'mechanical engineer',
        'manufacturing engineer', 'process engineer', 'quality engineer',
        'systems engineer', 'transmission engineer', 'substation engineer',
        'protection and control', 'p&c engineer', 'relay engineer',
        'estimator', 'preconstruction',
        # Added in Phase 2 - utility/grid engineering false positives
        'interconnection engineer',  # Utility interface role
        'grid engineer',             # Grid/utility focus
        'protection engineer',       # Utility protection systems
        'metering engineer',         # Utility metering
    ]
    if any(term in desc_lower for term in other_eng_terms):
        return False

    # TIER 1: Solar-specific design software (auto-qualify - these are ONLY used for solar design)
    solar_specific_tools = ['helioscope', 'aurora solar', 'pvsyst', 'solaredge designer', 'opensolaris']
    if any(tool in desc_lower for tool in solar_specific_tools):
        return True

    # TIER 2: Strong technical signals that are specific to solar CAD work
    # These must appear with a design role context
    strong_technical_signals = [
        'string sizing', 'stringing diagram', 'stringing layout',
        'module layout', 'array layout', 'panel layout',
        'single line diagram', 'one-line diagram', 'sld ',
        'conduit schedule', 'wiring schedule', 'wire schedule',
        'permit set', 'plan set', 'permit package', 'construction drawing',
        'voltage drop calculation', 'voltage drop calc'
    ]
    design_role_indicators = [
        'designer', 'drafter', 'draftsman', 'drafting', 'cad ',
        'design engineer', 'design technician', 'cad technician'
    ]

    has_strong_signal = any(sig in desc_lower for sig in strong_technical_signals)
    has_design_role = any(role in desc_lower for role in design_role_indicators)

    if has_strong_signal and has_design_role:
        return True

    # TIER 3: General CAD tools + design role + solar project type
    general_cad_tools = ['autocad', 'auto cad', 'revit', 'sketchup', 'bluebeam', 'solidworks']
    solar_project_types = [
        'solar array', 'pv array', 'solar installation', 'pv installation',
        'solar project', 'pv project', 'solar system', 'pv system',
        'residential solar', 'commercial solar', 'utility solar', 'utility-scale solar',
        'rooftop solar', 'ground mount solar', 'carport solar'
    ]

    has_cad_tool = any(tool in desc_lower for tool in general_cad_tools)
    has_solar_project = any(proj in desc_lower for proj in solar_project_types)

    if has_cad_tool and has_design_role and has_solar_project:
        return True

    # TIER 4: Job title contains explicit solar design role
    title_signals = [
        'solar designer', 'pv designer', 'solar drafter', 'pv drafter',
        'solar design engineer', 'pv design engineer', 'solar cad',
        'photovoltaic designer', 'solar design technician'
    ]
    # Check first 200 chars (usually contains title)
    title_area = desc_lower[:200]
    if any(sig in title_area for sig in title_signals):
        return True

    # TIER 5: Design role + CAD tool + solar/PV mentioned (simpler 2-way with solar context)
    # This catches generic CAD jobs at solar companies
    if has_cad_tool and has_design_role:
        # Already passed the solar/PV check at the top, so this is a CAD design job with solar context
        return True

    # TIER 6: Design role titles that explicitly include solar/PV/renewable
    solar_design_titles = [
        'electrical designer', 'electrical drafter', 'cad designer', 'cad drafter',
        'cad technician', 'cad operator', 'design technician', 'drafting technician',
        'bim modeler', 'bim technician', 'design assistant', 'permit designer'
    ]
    # If the job has one of these titles AND passed the solar/PV context check, qualify it
    if any(title in desc_lower for title in solar_design_titles):
        return True

    return False


def scrape_solar_jobs() -> pd.DataFrame:
    """Scrape solar design/CAD jobs from multiple sources."""

    # Wide net search - generic role names that our filter will narrow down
    # The filter is strict, so we can afford to search broadly here
    search_terms = [
        # Core drafter/designer roles
        "electrical designer",
        "electrical drafter",
        "CAD designer",
        "CAD drafter",
        "CAD technician",
        "CAD operator",
        "AutoCAD drafter",
        "AutoCAD designer",
        "AutoCAD operator",

        # Technician/assistant variants
        "design technician",
        "drafting technician",
        "engineering technician electrical",
        "design assistant",
        "drafting assistant",

        # Coordinator/specialist roles
        "design coordinator",
        "CAD coordinator",
        "electrical detailer",

        # BIM roles (often overlap with solar design)
        "BIM modeler",
        "BIM technician",

        # Permit/plans specific
        "permit designer",
        "plans designer",

        # Solar-specific searches
        "solar designer",
        "solar drafter",
        "solar design engineer",
        "PV designer",
        "PV design engineer",
        "PV system designer",
        "photovoltaic designer",
        "solar permit designer",
        "solar plans designer",

        # Tool-based searches (very targeted)
        "helioscope",
        "aurora solar",
        "PVsyst",

        # Strong signal searches
        "stringing solar",
        "permit set solar",
        "plan set solar",

        # Context-based searches
        "residential solar",
        "commercial solar",
        "utility scale solar",
        "rooftop solar",
    ]

    all_jobs = []
    results_per_term = 1000  # Wide net, filter does the work

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
        df = df[df.apply(lambda row: description_matches(row['description'], row.get('company')), axis=1)]
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
