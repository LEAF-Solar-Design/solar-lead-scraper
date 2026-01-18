"""
Solar Job Lead Scraper
Finds companies hiring for solar CAD/design roles to use as sales leads.
"""

import json
import re
import urllib.parse
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
from jobspy import scrape_jobs


@dataclass
class ScoringResult:
    """Result of scoring a job posting.

    Attributes:
        score: Total numeric score (company_score + role_score)
        qualified: Whether score meets threshold
        reasons: List of human-readable scoring explanations
        company_score: Points from company-level signals (blocklist, known companies)
        role_score: Points from role/description signals (tools, titles, etc.)
        threshold: The threshold used for qualification
    """
    score: float
    qualified: bool
    reasons: list[str] = field(default_factory=list)
    company_score: float = 0.0
    role_score: float = 0.0
    threshold: float = 50.0


@dataclass
class FilterStats:
    """Statistics collected during a filter run.

    Attributes:
        total_processed: Total leads processed
        total_qualified: Leads that passed filter
        total_rejected: Leads that failed filter
        rejection_categories: Counter of rejection reason categories
        qualification_tiers: Counter of highest tier matched for qualifications
        company_blocked: Count of company blocklist rejections
    """
    total_processed: int = 0
    total_qualified: int = 0
    total_rejected: int = 0
    rejection_categories: Counter = field(default_factory=Counter)
    qualification_tiers: Counter = field(default_factory=Counter)
    company_blocked: int = 0

    def add_qualified(self, tier: str) -> None:
        """Record a qualified lead."""
        self.total_processed += 1
        self.total_qualified += 1
        self.qualification_tiers[tier] += 1

    def add_rejected(self, category: str, is_company_blocked: bool = False) -> None:
        """Record a rejected lead."""
        self.total_processed += 1
        self.total_rejected += 1
        self.rejection_categories[category] += 1
        if is_company_blocked:
            self.company_blocked += 1

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        if self.total_processed == 0:
            return 0.0
        return self.total_qualified / self.total_processed * 100


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


def score_company(company_name: str, config: dict) -> tuple[float, list[str]]:
    """Score based on company signals only.

    Args:
        company_name: Company name to check
        config: Configuration dictionary

    Returns:
        Tuple of (score, reasons_list)
        Score is -100 if blocklisted, 0 otherwise (future: positive signals for known solar companies)
    """
    # Handle None, NaN, or non-string company names
    if not company_name or not isinstance(company_name, str):
        return (0.0, [])

    company_lower = company_name.lower()

    # Blocklist check
    for blocked in config["company_blocklist"]:
        if blocked in company_lower:
            return (-100.0, [f"Company '{company_name}' in blocklist ({blocked})"])

    # Future: Add positive company signals here (known solar companies)
    # e.g., config.get("company_positive_signals", [])

    return (0.0, [])


def score_role(description: str, config: dict) -> tuple[float, list[str]]:
    """Score based on role/description signals only.

    Args:
        description: Job description text
        config: Configuration dictionary

    Returns:
        Tuple of (score, reasons_list)
        Score is sum of matched positive signals, -100 if exclusion matched
    """
    if not description or pd.isna(description):
        return (0.0, ["No description provided"])

    desc_lower = description.lower()
    reasons = []
    score = 0.0

    # Required context check (solar/PV)
    required = config["required_context"]["patterns"]
    has_required = any(p in desc_lower for p in required)
    if not has_required:
        return (0.0, ["Missing required solar/PV context"])
    reasons.append("+0: Has solar/PV context (required)")

    # Check all exclusions (any match = immediate -100)
    for name, excl in config["exclusions"].items():
        for pattern in excl["patterns"]:
            if pattern in desc_lower:
                return (-100.0, [f"Excluded: {excl['description']} (matched '{pattern}')"])

    # Check design role indicators (used by multiple tiers)
    design_indicators = config["design_role_indicators"]
    has_design_role = any(ind in desc_lower for ind in design_indicators)

    # Score positive signals
    signals = config["positive_signals"]

    # Tier 1: Solar-specific tools
    tier1 = signals["tier1_tools"]
    for pattern in tier1["patterns"]:
        if pattern in desc_lower:
            score += tier1["weight"]
            reasons.append(f"+{tier1['weight']}: {tier1['description']} ({pattern})")
            break

    # Tier 2: Strong technical signals
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

    # Tier 4: Title signals
    tier4 = signals["tier4_title"]
    title_area = desc_lower[:200]
    for pattern in tier4["patterns"]:
        if pattern in title_area:
            score += tier4["weight"]
            reasons.append(f"+{tier4['weight']}: {tier4['description']} ({pattern})")
            break

    # Tier 5: CAD + design role
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

    if has_design_role:
        reasons.append("+0: Has design role indicator")

    return (score, reasons)


def score_job(description: str, company_name: str = None, config: dict = None) -> ScoringResult:
    """Score a job posting and return detailed results.

    Combines company-level and role-level scoring into a single result.

    Args:
        description: Job description text
        company_name: Optional company name for blocklist check
        config: Optional config dict (uses get_config() if not provided)

    Returns:
        ScoringResult with total score, company_score, role_score, and reasons
    """
    if config is None:
        config = get_config()

    threshold = config.get("threshold", 50.0)

    # Score company separately
    company_score, company_reasons = score_company(company_name, config)

    # If company is blocklisted, short-circuit
    if company_score < 0:
        return ScoringResult(
            score=company_score,
            qualified=False,
            reasons=company_reasons,
            company_score=company_score,
            role_score=0.0,
            threshold=threshold
        )

    # Score role/description
    role_score, role_reasons = score_role(description, config)

    # If role is excluded, short-circuit
    if role_score < 0:
        return ScoringResult(
            score=role_score,
            qualified=False,
            reasons=role_reasons,
            company_score=company_score,
            role_score=role_score,
            threshold=threshold
        )

    # Combine scores
    total_score = company_score + role_score
    all_reasons = company_reasons + role_reasons

    return ScoringResult(
        score=total_score,
        qualified=total_score >= threshold,
        reasons=all_reasons,
        company_score=company_score,
        role_score=role_score,
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
    """Check if job description matches solar design criteria.

    DEPRECATED: Use score_job() for detailed scoring information.
    This wrapper maintains backward compatibility with evaluate.py.

    Args:
        description: Job description text
        company_name: Optional company name for blocklist check

    Returns:
        True if job qualifies, False otherwise
    """
    result = score_job(description, company_name)
    return result.qualified


def export_rejected_leads(
    rejected_leads: list[dict],
    output_dir: Path,
    run_id: str,
    max_export: int = 100
) -> Path:
    """Export rejected leads for labeling review.

    Exports rejected leads in the same schema as golden-test-set.json
    for easy import into labeling workflow after human review.

    Args:
        rejected_leads: List of dicts with keys: id, description, company, title, rejection_reason, score
        output_dir: Directory to write JSON file
        run_id: Timestamp or identifier for this run
        max_export: Maximum leads to export (default 100 to avoid huge files)

    Returns:
        Path to the created file
    """
    # Limit export size
    to_export = rejected_leads[:max_export]

    # Convert to labeled data schema
    items = []
    for lead in to_export:
        item = {
            "id": lead.get("id", f"rejected_{len(items)+1:03d}"),
            "description": lead.get("description", "")[:2000],  # Truncate long descriptions
            "label": False,  # Presumed false, reviewer confirms or changes to true
            "company": lead.get("company"),
            "title": lead.get("title"),
            "notes": f"Rejected: {lead.get('rejection_reason', 'unknown')} (score: {lead.get('score', 0)})"
        }
        items.append(item)

    export_data = {
        "metadata": {
            "created": datetime.now().isoformat(),
            "purpose": "labeling_review",
            "run_id": run_id,
            "count": len(items),
            "total_rejected": len(rejected_leads),
            "notes": "Review and change label to true for any false negatives"
        },
        "items": items
    }

    filepath = output_dir / f"rejected_leads_{run_id}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2)

    return filepath


def categorize_rejection(result: ScoringResult) -> str:
    """Categorize a rejection reason for statistics.

    Maps detailed rejection reasons to config section names for aggregation.

    Args:
        result: ScoringResult from score_job()

    Returns:
        Category string matching config structure
    """
    if result.company_score < 0:
        return "company_blocklist"

    if not result.reasons:
        return "unknown"

    reason = result.reasons[0].lower()

    if "missing required" in reason or "no description" in reason:
        return "no_solar_context"

    if "excluded" in reason:
        if any(x in reason for x in ["installer", "stringer", "roofer", "foreman", "crew"]):
            return "exclusions.installer"
        if any(x in reason for x in ["interconnection", "grid", "protection", "metering"]):
            return "exclusions.utility"
        if any(x in reason for x in ["cadence", "synopsys", "mentor", "eda", "asic", "verilog"]):
            return "exclusions.eda_tools"
        if any(x in reason for x in ["satellite", "spacecraft", "orbit", "rocket"]):
            return "exclusions.aerospace"
        if any(x in reason for x in ["tennis", "racquet", "badminton"]):
            return "exclusions.tennis"
        return "exclusions.other"

    return "below_threshold"


def extract_tier_from_reasons(reasons: list[str]) -> str:
    """Extract the highest tier matched from scoring reasons.

    Args:
        reasons: List of scoring reasons from ScoringResult

    Returns:
        Tier string like "tier1", "tier2", etc. or "unknown"
    """
    for reason in reasons:
        if reason.startswith("+") and "tier" not in reason.lower():
            # Parse tier from reason like "+100: Tier 1 solar tool"
            if "Tier 1" in reason or "tier1" in reason.lower():
                return "tier1"
            elif "Tier 2" in reason or "tier2" in reason.lower():
                return "tier2"
            elif "Tier 3" in reason or "tier3" in reason.lower():
                return "tier3"
            elif "Tier 4" in reason or "tier4" in reason.lower():
                return "tier4"
            elif "Tier 5" in reason or "tier5" in reason.lower():
                return "tier5"
            elif "Tier 6" in reason or "tier6" in reason.lower():
                return "tier6"
    return "unknown"


def scrape_solar_jobs() -> tuple[pd.DataFrame, FilterStats, list[dict], dict]:
    """Scrape solar design/CAD jobs from multiple sources.

    Returns:
        Tuple of:
        - DataFrame of qualified jobs
        - FilterStats with run statistics
        - list of rejected lead dicts for labeling export
        - dict mapping row indices to ScoringResult for confidence calculation
    """

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
        return pd.DataFrame(), FilterStats(), [], {}

    # Combine all results
    df = pd.concat(all_jobs, ignore_index=True)
    print(f"\nTotal jobs found: {len(df)}")

    # Collect filter statistics
    stats = FilterStats()
    rejected_leads = []
    scoring_results = {}  # Map row index to ScoringResult for confidence calculation

    # Filter by description content
    if 'description' in df.columns:
        before_filter = len(df)
        qualified_mask = []

        for idx, row in df.iterrows():
            result = score_job(row['description'], row.get('company'))

            if result.qualified:
                tier = extract_tier_from_reasons(result.reasons)
                stats.add_qualified(tier)
                qualified_mask.append(True)
                # Store scoring result for confidence calculation later
                scoring_results[idx] = result
            else:
                category = categorize_rejection(result)
                is_blocked = result.company_score < 0
                stats.add_rejected(category, is_blocked)
                qualified_mask.append(False)
                # Collect rejected lead for export
                rejected_lead = {
                    "id": f"rejected_{len(rejected_leads)+1:03d}_{str(row.get('company', 'unknown'))[:20]}",
                    "description": row['description'] if pd.notna(row.get('description')) else "",
                    "company": row.get('company'),
                    "title": row.get('title'),
                    "rejection_reason": category,
                    "score": result.score
                }
                rejected_leads.append(rejected_lead)

        df = df[qualified_mask]
        print(f"After filtering: {len(df)} qualified leads (filtered out {before_filter - len(df)})")
    else:
        print("Warning: No description column available for filtering")

    return df, stats, rejected_leads, scoring_results


def process_jobs(df: pd.DataFrame, scoring_results: dict = None) -> pd.DataFrame:
    """Process and dedupe jobs, extract company info.

    Args:
        df: DataFrame of job listings
        scoring_results: Optional dict mapping row indices to ScoringResult for confidence
    """
    if df.empty:
        return df

    # Keep relevant columns
    columns_to_keep = ['company', 'title', 'location', 'job_url']
    available_cols = [c for c in columns_to_keep if c in df.columns]
    df = df[available_cols].copy()

    # Add confidence score before deduplication (while we still have original indices)
    if scoring_results:
        def get_confidence(idx):
            result = scoring_results.get(idx)
            if result and result.qualified:
                # Score 50 = threshold (50% confidence), 100+ = 100% confidence
                return min(100.0, result.score)
            return None
        df['confidence_score'] = df.index.map(get_confidence)
    else:
        df['confidence_score'] = None

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
    final_columns = ['company', 'domain', 'job_title', 'location', 'confidence_score', 'posting_url', 'linkedin_managers', 'linkedin_hiring', 'linkedin_role', 'google_enduser', 'date_scraped']
    df = df[[c for c in final_columns if c in df.columns]]

    return df


def print_filter_stats(stats: FilterStats) -> None:
    """Print human-readable filter statistics."""
    print()
    print("=" * 50)
    print("FILTER STATISTICS")
    print("=" * 50)
    print(f"Total processed:  {stats.total_processed}")
    if stats.total_processed > 0:
        print(f"Qualified:        {stats.total_qualified} ({stats.pass_rate:.1f}%)")
        print(f"Rejected:         {stats.total_rejected} ({100 - stats.pass_rate:.1f}%)")
    else:
        print("Qualified:        0")
        print("Rejected:         0")

    if stats.company_blocked > 0:
        print(f"\nCompany blocklist: {stats.company_blocked}")

    if stats.rejection_categories:
        print("\nTop rejection reasons:")
        for category, count in stats.rejection_categories.most_common(5):
            print(f"  {count:4d} | {category}")

    if stats.qualification_tiers:
        print("\nQualification by tier:")
        for tier, count in sorted(stats.qualification_tiers.items()):
            print(f"  {tier}: {count}")
    print("=" * 50)


def main():
    print("=" * 50)
    print("Solar Job Lead Scraper")
    print("=" * 50)
    print()

    # Scrape jobs
    raw_jobs, stats, rejected_leads, scoring_results = scrape_solar_jobs()

    if raw_jobs.empty:
        print("No jobs to process. Exiting.")
        # Still print stats even if empty
        print_filter_stats(stats)
        return

    # Process and dedupe
    leads = process_jobs(raw_jobs, scoring_results)

    if leads.empty:
        print("No leads after processing. Exiting.")
        print_filter_stats(stats)
        return

    # Print filter statistics
    print_filter_stats(stats)

    # Ensure output directory exists
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Export rejected leads for labeling review
    if rejected_leads:
        rejected_path = export_rejected_leads(rejected_leads, output_dir, timestamp)
        print(f"\nExported {min(100, len(rejected_leads))} rejected leads to: {rejected_path}")

    # Save qualified leads to CSV
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
