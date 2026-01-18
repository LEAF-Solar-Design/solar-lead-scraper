"""
Solar Job Lead Scraper
Finds companies hiring for solar CAD/design roles to use as sales leads.
"""

import json
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
from jobspy import scrape_jobs


@dataclass
class ScoringResult:
    """Result of scoring a job posting.

    Attributes:
        score: Total numeric score (higher = better match)
        qualified: Whether score meets threshold
        reasons: List of human-readable scoring explanations
        threshold: The threshold used for qualification
    """
    score: float
    qualified: bool
    reasons: list[str] = field(default_factory=list)
    threshold: float = 50.0


# Company blocklist - known false positive industries
# Aerospace/defense companies use "solar" for spacecraft solar panels
# Semiconductor companies use "CAD" for chip design tools
# NOTE: These are now loaded from config/filter-config.json at runtime
# This constant is kept for documentation purposes
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


def load_filter_config(config_path: Path = None) -> dict:
    """Load filter configuration from JSON file.

    Args:
        config_path: Path to config file. Defaults to config/filter-config.json
                     relative to this file's location.

    Returns:
        Configuration dictionary with signals, weights, and threshold.
    """
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "filter-config.json"

    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


# Load config at module level (lazy loading on first use)
_CONFIG = None


def get_config() -> dict:
    """Get filter configuration, loading from file if needed."""
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = load_filter_config()
    return _CONFIG


def score_job(description: str, company_name: str = None, config: dict = None) -> ScoringResult:
    """Score a job posting and return detailed results.

    Args:
        description: Job description text
        company_name: Optional company name for blocklist check
        config: Optional config dict (uses get_config() if not provided)

    Returns:
        ScoringResult with score, qualified flag, and reasons list
    """
    if config is None:
        config = get_config()

    threshold = config.get("threshold", 50.0)
    reasons = []
    score = 0.0

    # Company blocklist check FIRST (immediate disqualification)
    if company_name:
        company_lower = company_name.lower()
        for blocked in config["company_blocklist"]:
            if blocked in company_lower:
                return ScoringResult(
                    score=-100.0,
                    qualified=False,
                    reasons=[f"Company '{company_name}' in blocklist ({blocked})"],
                    threshold=threshold
                )

    # No description = cannot qualify
    if not description or pd.isna(description):
        return ScoringResult(
            score=0.0,
            qualified=False,
            reasons=["No description provided"],
            threshold=threshold
        )

    desc_lower = description.lower()

    # Required context check (solar/PV)
    required = config["required_context"]["patterns"]
    has_required = any(p in desc_lower for p in required)
    if not has_required:
        return ScoringResult(
            score=0.0,
            qualified=False,
            reasons=["Missing required solar/PV context"],
            threshold=threshold
        )
    reasons.append("+0: Has solar/PV context (required)")

    # Check all exclusions (any match = immediate -100)
    for name, excl in config["exclusions"].items():
        for pattern in excl["patterns"]:
            if pattern in desc_lower:
                return ScoringResult(
                    score=-100.0,
                    qualified=False,
                    reasons=[f"Excluded: {excl['description']} (matched '{pattern}')"],
                    threshold=threshold
                )

    # Check design role indicators (used by multiple tiers)
    design_indicators = config["design_role_indicators"]
    has_design_role = any(ind in desc_lower for ind in design_indicators)

    # Score positive signals
    signals = config["positive_signals"]

    # Tier 1: Solar-specific tools (auto-qualify)
    tier1 = signals["tier1_tools"]
    for pattern in tier1["patterns"]:
        if pattern in desc_lower:
            score += tier1["weight"]
            reasons.append(f"+{tier1['weight']}: {tier1['description']} ({pattern})")
            break  # Only count once per tier

    # Tier 2: Strong technical signals (require design role)
    tier2 = signals["tier2_strong"]
    if has_design_role:
        for pattern in tier2["patterns"]:
            if pattern in desc_lower:
                score += tier2["weight"]
                reasons.append(f"+{tier2['weight']}: {tier2['description']} ({pattern})")
                break

    # Tier 3: CAD + project type + design role
    tier3 = signals["tier3_cad_project"]
    if has_design_role:
        has_cad = any(p in desc_lower for p in tier3["patterns_cad"])
        has_project = any(p in desc_lower for p in tier3["patterns_project"])
        if has_cad and has_project:
            score += tier3["weight"]
            reasons.append(f"+{tier3['weight']}: {tier3['description']}")

    # Tier 4: Title signals (check first 200 chars)
    tier4 = signals["tier4_title"]
    title_area = desc_lower[:200]
    for pattern in tier4["patterns"]:
        if pattern in title_area:
            score += tier4["weight"]
            reasons.append(f"+{tier4['weight']}: {tier4['description']} ({pattern})")
            break

    # Tier 5: CAD + design role (simpler)
    tier5 = signals["tier5_cad_design"]
    if has_design_role:
        has_cad = any(p in desc_lower for p in tier5["patterns_cad"])
        if has_cad:
            score += tier5["weight"]
            reasons.append(f"+{tier5['weight']}: {tier5['description']}")

    # Tier 6: Design role titles
    tier6 = signals["tier6_design_titles"]
    for pattern in tier6["patterns"]:
        if pattern in desc_lower:
            score += tier6["weight"]
            reasons.append(f"+{tier6['weight']}: {tier6['description']} ({pattern})")
            break

    # Add design role indicator note
    if has_design_role:
        reasons.append("+0: Has design role indicator")

    return ScoringResult(
        score=score,
        qualified=score >= threshold,
        reasons=reasons,
        threshold=threshold
    )


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
    """Check if job description matches our criteria for solar design roles.

    All filter terms are loaded from config/filter-config.json.
    """
    config = get_config()

    # Company blocklist check FIRST (before any description analysis)
    if company_name:
        company_lower = company_name.lower()
        company_blocklist = config.get("company_blocklist", [])
        for blocked in company_blocklist:
            if blocked in company_lower:
                return False

    if not description or pd.isna(description):
        return False

    desc_lower = description.lower()

    # Must have solar/PV context
    required_context = config.get("required_context", {}).get("patterns", ["solar", "pv", "photovoltaic"])
    has_solar_context = any(ctx in desc_lower for ctx in required_context)

    if not has_solar_context:
        return False

    # Check all exclusion categories
    exclusions = config.get("exclusions", {})
    for category, excl_config in exclusions.items():
        patterns = excl_config.get("patterns", [])
        if any(pattern in desc_lower for pattern in patterns):
            return False

    # Get positive signals config
    positive_signals = config.get("positive_signals", {})
    design_role_indicators = config.get("design_role_indicators", [])

    # TIER 1: Solar-specific design software (auto-qualify)
    tier1 = positive_signals.get("tier1_tools", {})
    tier1_patterns = tier1.get("patterns", [])
    if any(tool in desc_lower for tool in tier1_patterns):
        return True

    # TIER 2: Strong technical signals that are specific to solar CAD work
    tier2 = positive_signals.get("tier2_strong", {})
    tier2_patterns = tier2.get("patterns", [])
    has_strong_signal = any(sig in desc_lower for sig in tier2_patterns)
    has_design_role = any(role in desc_lower for role in design_role_indicators)

    if has_strong_signal and has_design_role:
        return True

    # TIER 3: General CAD tools + design role + solar project type
    tier3 = positive_signals.get("tier3_cad_project", {})
    tier3_cad = tier3.get("patterns_cad", [])
    tier3_project = tier3.get("patterns_project", [])
    has_cad_tool = any(tool in desc_lower for tool in tier3_cad)
    has_solar_project = any(proj in desc_lower for proj in tier3_project)

    if has_cad_tool and has_design_role and has_solar_project:
        return True

    # TIER 4: Job title contains explicit solar design role
    tier4 = positive_signals.get("tier4_title", {})
    tier4_patterns = tier4.get("patterns", [])
    # Check first 200 chars (usually contains title)
    title_area = desc_lower[:200]
    if any(sig in title_area for sig in tier4_patterns):
        return True

    # TIER 5: Design role + CAD tool + solar/PV mentioned
    tier5 = positive_signals.get("tier5_cad_design", {})
    tier5_cad = tier5.get("patterns_cad", [])
    has_cad_tool_tier5 = any(tool in desc_lower for tool in tier5_cad)

    if has_cad_tool_tier5 and has_design_role:
        # Already passed the solar/PV check at the top
        return True

    # TIER 6: Design role titles with solar context
    tier6 = positive_signals.get("tier6_design_titles", {})
    tier6_patterns = tier6.get("patterns", [])
    if any(title in desc_lower for title in tier6_patterns):
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
