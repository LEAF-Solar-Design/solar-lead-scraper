"""
Solar Job Lead Scraper
Finds companies hiring for solar CAD/design roles to use as sales leads.
"""

import json
import os
import random
import re
import time
import urllib.parse
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from jobspy import scrape_jobs


def mask_credentials(text: str) -> str:
    """Mask credentials in URLs and other sensitive strings.

    Replaces patterns like user:password@host with user:****@host to prevent
    credential leakage in logs.

    Args:
        text: String that might contain credentials

    Returns:
        String with credentials masked
    """
    if not isinstance(text, str):
        return text
    # Match credentials in URLs: scheme://user:pass@host or user:pass@host
    # Masks the password portion while keeping username and host visible
    return re.sub(r'(://[^:]+:)[^@]+(@)', r'\1****\2', text)


def sanitize_csv_cell(value) -> str:
    """Sanitize a cell value to prevent CSV injection attacks.

    Excel and other spreadsheet apps can execute formulas if a cell starts
    with certain characters. This function prefixes dangerous values with
    a single quote to prevent execution.

    Args:
        value: The cell value to sanitize

    Returns:
        Sanitized string safe for CSV export
    """
    if not isinstance(value, str):
        return value
    # Characters that trigger formula execution in Excel/LibreOffice
    dangerous_chars = ('=', '+', '-', '@', '\t', '\r')
    if value.startswith(dangerous_chars):
        return "'" + value
    return value


def sanitize_dataframe_for_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitize all string columns in a DataFrame for safe CSV export.

    Args:
        df: DataFrame to sanitize

    Returns:
        New DataFrame with sanitized string values
    """
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == 'object':  # String columns
            df[col] = df[col].apply(sanitize_csv_cell)
    return df


def extract_error_context(error: Exception) -> tuple[str, int | None]:
    """Extract useful context from an exception before truncating the message.

    Extracts the exception class name and HTTP status code (if present) from
    the full error before the message gets truncated to 500 chars.

    Args:
        error: The exception to extract context from

    Returns:
        Tuple of (exception_class_name, status_code_or_None)
    """
    exception_class = type(error).__name__
    status_code = None

    # Try to extract HTTP status code from common patterns
    error_str = str(error)

    # Check for requests.HTTPError which has response attribute
    if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
        status_code = error.response.status_code
    else:
        # Try to extract from error message: "403", "429", "500" etc
        import re as re_local
        status_match = re_local.search(r'\b([3-5]\d{2})\b', error_str)
        if status_match:
            status_code = int(status_match.group(1))

    return exception_class, status_code


def get_batch_slice(items: list, batch: int, total_batches: int) -> list:
    """Get the slice of items for a specific batch.

    Distributes items across batches as evenly as possible. When items don't
    divide evenly, earlier batches get one extra item each.

    Example with 10 items and 4 batches:
        - batch 0: items 0-2 (3 items) - gets extra item
        - batch 1: items 3-5 (3 items) - gets extra item
        - batch 2: items 6-7 (2 items)
        - batch 3: items 8-9 (2 items)

    Args:
        items: List of items to split
        batch: Batch index (0-based)
        total_batches: Total number of batches

    Returns:
        List of items for this batch

    Raises:
        ValueError: If batch >= total_batches, batch < 0, or total_batches < 1
    """
    if total_batches < 1:
        raise ValueError(f"total_batches must be >= 1, got {total_batches}")
    if batch < 0:
        raise ValueError(f"batch must be >= 0, got {batch}")
    if batch >= total_batches:
        raise ValueError(f"batch ({batch}) must be < total_batches ({total_batches})")

    # Divide items into roughly equal batches
    batch_size = len(items) // total_batches
    remainder = len(items) % total_batches

    # Calculate start and end indices for this batch
    # Earlier batches get one extra item if there's a remainder
    start_idx = batch * batch_size + min(batch, remainder)
    end_idx = start_idx + batch_size + (1 if batch < remainder else 0)

    return items[start_idx:end_idx]

# Increase default timeout for requests library (jobspy uses 10s which times out on Indeed)
# This patches the requests.Session to use a longer timeout by default
_original_request = requests.Session.request


def _patched_request(self, method, url, **kwargs):
    """Wrapper that sets a longer default timeout for all requests."""
    if kwargs.get("timeout") is None:
        kwargs["timeout"] = (10, 30)  # (connect_timeout, read_timeout) in seconds
    return _original_request(self, method, url, **kwargs)


requests.Session.request = _patched_request


@dataclass
class SearchError:
    """Record of a failed search attempt.

    Attributes:
        search_term: The search term that failed
        site: Which job site(s) were being queried
        error_type: Category of error (rate_limit, blocked, timeout, unknown)
        error_message: Truncated error message (first 500 chars)
        attempts: Number of retry attempts made
        timestamp: When the error occurred
        exception_class: The exception class name (e.g., 'HTTPError', 'Timeout')
        status_code: HTTP status code if available (extracted before truncation)
    """
    search_term: str
    site: str
    error_type: str
    error_message: str
    attempts: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    exception_class: str = ""
    status_code: int | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        result = {
            "search_term": self.search_term,
            "site": self.site,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "attempts": self.attempts,
            "timestamp": self.timestamp
        }
        # Include additional context if available
        if self.exception_class:
            result["exception_class"] = self.exception_class
        if self.status_code is not None:
            result["status_code"] = self.status_code
        return result


@dataclass
class SiteStats:
    """Statistics for a single job site during a scrape run.

    Attributes:
        site: Name of the job site (indeed, linkedin, etc.)
        searches_attempted: Number of search terms attempted
        searches_successful: Number of searches that returned results
        total_jobs_found: Total jobs returned across all searches
        blocked: Whether site was blocked during this run
        blocked_at_term: Search term when site was first blocked (if blocked)
        error_count: Number of non-blocking errors encountered
    """
    site: str
    searches_attempted: int = 0
    searches_successful: int = 0
    total_jobs_found: int = 0
    blocked: bool = False
    blocked_at_term: str | None = None
    error_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            "site": self.site,
            "searches_attempted": self.searches_attempted,
            "searches_successful": self.searches_successful,
            "total_jobs_found": self.total_jobs_found,
            "blocked": self.blocked,
            "blocked_at_term": self.blocked_at_term,
            "error_count": self.error_count,
            "success_rate": round(self.searches_successful / self.searches_attempted * 100, 1) if self.searches_attempted > 0 else 0.0
        }


@dataclass
class ScrapeStats:
    """Overall statistics for a scrape run.

    Attributes:
        run_id: Unique identifier for this run (timestamp)
        batch: Batch number if running in parallel mode
        total_batches: Total number of batches
        start_time: When the scrape started
        end_time: When the scrape finished
        search_terms_total: Total search terms to process
        search_terms_completed: Search terms actually processed
        site_stats: Per-site statistics
        blocked_sites: List of sites that got blocked with details
        total_jobs_raw: Total jobs before filtering
        total_jobs_filtered: Jobs after filtering
        unique_companies: Number of unique companies in results
    """
    run_id: str
    batch: int | None = None
    total_batches: int = 1
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: str | None = None
    search_terms_total: int = 0
    search_terms_completed: int = 0
    site_stats: dict[str, SiteStats] = field(default_factory=dict)
    blocked_sites: list[dict] = field(default_factory=list)
    total_jobs_raw: int = 0
    total_jobs_filtered: int = 0
    unique_companies: int = 0

    def record_site_attempt(self, site: str) -> None:
        """Record that a search was attempted on a site."""
        if site not in self.site_stats:
            self.site_stats[site] = SiteStats(site=site)
        self.site_stats[site].searches_attempted += 1

    def record_site_success(self, site: str, jobs_found: int) -> None:
        """Record a successful search on a site."""
        if site not in self.site_stats:
            self.site_stats[site] = SiteStats(site=site)
        self.site_stats[site].searches_successful += 1
        self.site_stats[site].total_jobs_found += jobs_found

    def record_site_blocked(self, site: str, search_term: str, error_message: str) -> None:
        """Record that a site was blocked."""
        if site not in self.site_stats:
            self.site_stats[site] = SiteStats(site=site)
        self.site_stats[site].blocked = True
        self.site_stats[site].blocked_at_term = search_term
        self.blocked_sites.append({
            "site": site,
            "search_term": search_term,
            "error_message": error_message[:500],
            "timestamp": datetime.now().isoformat()
        })

    def record_site_error(self, site: str) -> None:
        """Record a non-blocking error on a site."""
        if site not in self.site_stats:
            self.site_stats[site] = SiteStats(site=site)
        self.site_stats[site].error_count += 1

    def finish(self) -> None:
        """Mark the run as complete."""
        self.end_time = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            "metadata": {
                "run_id": self.run_id,
                "batch": self.batch,
                "total_batches": self.total_batches,
                "start_time": self.start_time,
                "end_time": self.end_time,
            },
            "search_terms": {
                "total": self.search_terms_total,
                "completed": self.search_terms_completed,
                "completion_rate": round(self.search_terms_completed / self.search_terms_total * 100, 1) if self.search_terms_total > 0 else 0.0
            },
            "sites": {name: stats.to_dict() for name, stats in self.site_stats.items()},
            "blocked_sites": self.blocked_sites,
            "results": {
                "total_jobs_raw": self.total_jobs_raw,
                "total_jobs_filtered": self.total_jobs_filtered,
                "unique_companies": self.unique_companies,
                "filter_rate": round((1 - self.total_jobs_filtered / self.total_jobs_raw) * 100, 1) if self.total_jobs_raw > 0 else 0.0
            }
        }


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
class SearchAttempt:
    """Record of a single search attempt with detailed diagnostics.

    Attributes:
        search_term: The search term used
        site: Which site was queried
        timestamp: When the attempt was made
        success: Whether it succeeded
        jobs_found: Number of jobs returned
        duration_ms: How long the request took
        http_status: HTTP status code (if available)
        error_type: Type of error (if failed)
        error_message: Error details (if failed)
        retry_count: Which retry attempt this was
        selectors_tried: For browser scraping - which selectors were tried
        selector_matched: Which selector found results
        cloudflare_detected: Whether Cloudflare challenge was present
        cloudflare_solved: Whether challenge was solved
        page_title: Page title (useful for diagnosing blocks)
        response_size_bytes: Size of response
    """
    search_term: str
    site: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    success: bool = False
    jobs_found: int = 0
    duration_ms: int = 0
    http_status: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    selectors_tried: list[str] = field(default_factory=list)
    selector_matched: str | None = None
    cloudflare_detected: bool = False
    cloudflare_solved: bool | None = None
    page_title: str | None = None
    response_size_bytes: int | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            "search_term": self.search_term,
            "site": self.site,
            "timestamp": self.timestamp,
            "success": self.success,
            "jobs_found": self.jobs_found,
            "duration_ms": self.duration_ms,
            "http_status": self.http_status,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "selectors_tried": self.selectors_tried if self.selectors_tried else None,
            "selector_matched": self.selector_matched,
            "cloudflare_detected": self.cloudflare_detected,
            "cloudflare_solved": self.cloudflare_solved,
            "page_title": self.page_title,
            "response_size_bytes": self.response_size_bytes,
        }


@dataclass
class DeepAnalytics:
    """Deep diagnostic analytics for debugging scraper issues.

    Tracks detailed per-search-term, per-site metrics to help diagnose
    issues with LinkedIn, Indeed, ZipRecruiter, and Glassdoor scraping.

    Attributes:
        run_id: Unique identifier for this run
        batch: Batch number if running in parallel
        search_attempts: List of all search attempts with full details
        site_summaries: Aggregated stats per site
        search_term_performance: Success rate per search term
        timing_stats: Request timing distribution
        cloudflare_stats: Cloudflare challenge encounter/solve rates
        selector_stats: Which selectors are working for browser scraping
        browser_sessions: List of browser session diagnostics from camoufox
    """
    run_id: str
    batch: int | None = None
    search_attempts: list[SearchAttempt] = field(default_factory=list)
    browser_sessions: list[dict] = field(default_factory=list)

    def record_attempt(self, attempt: SearchAttempt) -> None:
        """Record a search attempt."""
        self.search_attempts.append(attempt)

    def record_browser_session(self, diagnostics: dict) -> None:
        """Record browser session diagnostics from camoufox scraper."""
        self.browser_sessions.append(diagnostics)

    def get_site_summary(self) -> dict[str, dict]:
        """Get aggregated statistics per site."""
        site_data = {}
        for attempt in self.search_attempts:
            site = attempt.site
            if site not in site_data:
                site_data[site] = {
                    "total_attempts": 0,
                    "successful_attempts": 0,
                    "total_jobs": 0,
                    "total_duration_ms": 0,
                    "errors_by_type": {},
                    "cloudflare_encounters": 0,
                    "cloudflare_solved": 0,
                    "cloudflare_failed": 0,
                    "http_status_codes": {},
                    "selectors_used": {},
                    "avg_jobs_per_success": 0,
                    "avg_duration_ms": 0,
                    "success_rate": 0,
                }
            s = site_data[site]
            s["total_attempts"] += 1
            s["total_duration_ms"] += attempt.duration_ms
            if attempt.success:
                s["successful_attempts"] += 1
                s["total_jobs"] += attempt.jobs_found
            if attempt.error_type:
                s["errors_by_type"][attempt.error_type] = s["errors_by_type"].get(attempt.error_type, 0) + 1
            if attempt.cloudflare_detected:
                s["cloudflare_encounters"] += 1
                if attempt.cloudflare_solved is True:
                    s["cloudflare_solved"] += 1
                elif attempt.cloudflare_solved is False:
                    s["cloudflare_failed"] += 1
            if attempt.http_status:
                status_str = str(attempt.http_status)
                s["http_status_codes"][status_str] = s["http_status_codes"].get(status_str, 0) + 1
            if attempt.selector_matched:
                s["selectors_used"][attempt.selector_matched] = s["selectors_used"].get(attempt.selector_matched, 0) + 1

        # Calculate derived metrics
        for site, s in site_data.items():
            if s["total_attempts"] > 0:
                s["success_rate"] = round(s["successful_attempts"] / s["total_attempts"] * 100, 1)
                s["avg_duration_ms"] = round(s["total_duration_ms"] / s["total_attempts"])
            if s["successful_attempts"] > 0:
                s["avg_jobs_per_success"] = round(s["total_jobs"] / s["successful_attempts"], 1)

        return site_data

    def get_search_term_performance(self) -> dict[str, dict]:
        """Get success rate breakdown per search term."""
        term_data = {}
        for attempt in self.search_attempts:
            term = attempt.search_term
            if term not in term_data:
                term_data[term] = {
                    "total_attempts": 0,
                    "successful_attempts": 0,
                    "total_jobs": 0,
                    "sites_tried": set(),
                    "sites_successful": set(),
                    "sites_failed": set(),
                }
            t = term_data[term]
            t["total_attempts"] += 1
            t["sites_tried"].add(attempt.site)
            if attempt.success:
                t["successful_attempts"] += 1
                t["total_jobs"] += attempt.jobs_found
                t["sites_successful"].add(attempt.site)
            else:
                t["sites_failed"].add(attempt.site)

        # Convert sets to lists and add derived metrics
        for term, t in term_data.items():
            t["sites_tried"] = sorted(t["sites_tried"])
            t["sites_successful"] = sorted(t["sites_successful"])
            t["sites_failed"] = sorted(t["sites_failed"])
            t["success_rate"] = round(t["successful_attempts"] / t["total_attempts"] * 100, 1) if t["total_attempts"] > 0 else 0

        return term_data

    def get_timing_distribution(self) -> dict:
        """Get timing statistics for successful requests."""
        durations = [a.duration_ms for a in self.search_attempts if a.success and a.duration_ms > 0]
        if not durations:
            return {"count": 0}

        durations.sort()
        return {
            "count": len(durations),
            "min_ms": min(durations),
            "max_ms": max(durations),
            "avg_ms": round(sum(durations) / len(durations)),
            "p50_ms": durations[len(durations) // 2],
            "p90_ms": durations[int(len(durations) * 0.9)] if len(durations) >= 10 else durations[-1],
            "p99_ms": durations[int(len(durations) * 0.99)] if len(durations) >= 100 else durations[-1],
        }

    def get_error_analysis(self) -> dict:
        """Analyze error patterns."""
        errors = [a for a in self.search_attempts if not a.success]
        if not errors:
            return {"total_errors": 0}

        by_type = {}
        by_site = {}
        error_messages = {}

        for e in errors:
            # By type
            err_type = e.error_type or "unknown"
            by_type[err_type] = by_type.get(err_type, 0) + 1

            # By site
            site = e.site
            if site not in by_site:
                by_site[site] = {"count": 0, "types": {}}
            by_site[site]["count"] += 1
            by_site[site]["types"][err_type] = by_site[site]["types"].get(err_type, 0) + 1

            # Collect unique error messages (truncated)
            if e.error_message:
                msg = e.error_message[:100]
                error_messages[msg] = error_messages.get(msg, 0) + 1

        return {
            "total_errors": len(errors),
            "by_type": by_type,
            "by_site": by_site,
            "top_error_messages": dict(sorted(error_messages.items(), key=lambda x: -x[1])[:10]),
        }

    def get_cloudflare_analysis(self) -> dict:
        """Analyze Cloudflare challenge handling."""
        cf_attempts = [a for a in self.search_attempts if a.cloudflare_detected]
        if not cf_attempts:
            return {"total_encounters": 0}

        return {
            "total_encounters": len(cf_attempts),
            "solved": sum(1 for a in cf_attempts if a.cloudflare_solved is True),
            "failed": sum(1 for a in cf_attempts if a.cloudflare_solved is False),
            "solve_rate": round(sum(1 for a in cf_attempts if a.cloudflare_solved is True) / len(cf_attempts) * 100, 1),
            "by_site": {
                site: {
                    "encounters": sum(1 for a in cf_attempts if a.site == site),
                    "solved": sum(1 for a in cf_attempts if a.site == site and a.cloudflare_solved is True),
                }
                for site in set(a.site for a in cf_attempts)
            },
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            "metadata": {
                "run_id": self.run_id,
                "batch": self.batch,
                "generated_at": datetime.now().isoformat(),
                "total_search_attempts": len(self.search_attempts),
                "browser_sessions_count": len(self.browser_sessions),
            },
            "site_summaries": self.get_site_summary(),
            "search_term_performance": self.get_search_term_performance(),
            "timing_distribution": self.get_timing_distribution(),
            "error_analysis": self.get_error_analysis(),
            "cloudflare_analysis": self.get_cloudflare_analysis(),
            "browser_sessions": self.browser_sessions,
            "raw_attempts": [a.to_dict() for a in self.search_attempts],
        }


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

    Raises:
        ValueError: If required keys are missing from the config.
    """
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "filter-config.json"

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    # Validate required keys
    required_keys = ["company_blocklist", "required_context", "exclusions", "positive_signals"]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise ValueError(f"Filter config missing required keys: {missing}")

    # Validate required_context structure
    if "patterns" not in config.get("required_context", {}):
        raise ValueError("Filter config required_context missing 'patterns' key")

    return config


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


def score_role(description: str, config: dict, title: str = None) -> tuple[float, list[str]]:
    """Score based on role/description signals only.

    Args:
        description: Job description text
        config: Configuration dictionary
        title: Optional job title for context checking

    Returns:
        Tuple of (score, reasons_list)
        Score is sum of matched positive signals, -100 if exclusion matched
    """
    # Handle None, NaN, pd.NA, or empty string
    try:
        if pd.isna(description) or not description:
            return (0.0, ["No description provided"])
    except (ValueError, TypeError):
        # pd.isna can raise for some types; treat as no description
        if not description:
            return (0.0, ["No description provided"])

    desc_lower = description.lower()
    title_lower = title.lower() if title and isinstance(title, str) else ""
    reasons = []
    score = 0.0

    # Required context check (solar/PV/Helioscope/PVSyst)
    # Must appear in EITHER the title OR the description
    required = config["required_context"]["patterns"]
    has_required_in_title = any(p in title_lower for p in required)
    has_required_in_desc = any(p in desc_lower for p in required)

    if not has_required_in_title and not has_required_in_desc:
        return (0.0, ["Missing required solar/PV context in title or description"])

    if has_required_in_title:
        reasons.append("+0: Has solar/PV context in title (required)")
    else:
        reasons.append("+0: Has solar/PV context in description (required)")

    # Check all exclusions (any match = immediate -100)
    # Some exclusions only check the title area (first 200 chars) to avoid false positives
    title_area = desc_lower[:200]
    for name, excl in config["exclusions"].items():
        check_area = excl.get("check_area", "description")
        text_to_check = title_area if check_area == "title" else desc_lower
        for pattern in excl["patterns"]:
            if pattern in text_to_check:
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


def score_job(description: str, company_name: str = None, config: dict = None, title: str = None) -> ScoringResult:
    """Score a job posting and return detailed results.

    Combines company-level and role-level scoring into a single result.

    Args:
        description: Job description text
        company_name: Optional company name for blocklist check
        config: Optional config dict (uses get_config() if not provided)
        title: Optional job title for context checking

    Returns:
        ScoringResult with total score, company_score, role_score, and reasons
    """
    if config is None:
        config = get_config()

    # Default threshold of 50.0 requires strong signals from both company (solar-focused)
    # and role (CAD/design work). This filters ~96% of raw jobs to ~4% qualified leads.
    # Breakdown: company_score (25-35 for solar keywords) + role_score (25-40 for CAD/design)
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

    # Score role/description (pass title for required context check)
    role_score, role_reasons = score_role(description, config, title=title)

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
        # Installer roles
        if any(x in reason for x in ["installer", "stringer", "roofer", "foreman", "crew", "technician", "lineman", "lineworker"]):
            return "exclusions.installer"
        # Sales and marketing
        if any(x in reason for x in ["sales", "marketing", "account executive", "business development"]):
            return "exclusions.sales"
        # Management roles (use word boundaries to avoid matching "semiconductor" -> "cto")
        if any(x in reason for x in ["manager", "director", "vp ", "vice president", "chief "]) or \
           any(f" {x}" in reason or reason.startswith(x) for x in ["ceo", "cto", "cfo"]):
            return "exclusions.management"
        # Other engineering (non-design)
        if any(x in reason for x in ["application engineer", "field engineer", "commissioning", "systems engineer",
                                      "interconnection", "grid", "protection", "metering", "estimator", "preconstruction"]):
            return "exclusions.other_engineering"
        # Structural/civil/mechanical engineering
        if any(x in reason for x in ["structural engineer", "civil engineer", "mechanical engineer", "geotechnical"]):
            return "exclusions.other_engineering_strict"
        # EDA tools (chip design)
        if any(x in reason for x in ["cadence", "synopsys", "mentor", "eda", "asic", "verilog", "virtuoso", "spectre"]):
            return "exclusions.eda_tools"
        # Semiconductor
        if any(x in reason for x in ["semiconductor", "rtl design", "fpga", "vlsi", "chip design", "wafer", "foundry"]):
            return "exclusions.semiconductor"
        # Space/aerospace
        if any(x in reason for x in ["satellite", "spacecraft", "orbit", "rocket", "aerospace", "starlink", "avionics"]):
            return "exclusions.space"
        # Tennis (false positives)
        if any(x in reason for x in ["tennis", "racquet", "badminton", "pickleball"]):
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


def classify_error(error: Exception) -> str:
    """Classify an exception into an error type category.

    Args:
        error: The exception that occurred

    Returns:
        Error type string: rate_limit, blocked, timeout, connection, or unknown
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    # Rate limiting indicators
    if any(x in error_str for x in ["429", "too many requests", "rate limit", "throttl"]):
        return "rate_limit"

    # Blocked/forbidden indicators
    if any(x in error_str for x in ["403", "forbidden", "blocked", "captcha", "cloudflare", "access denied"]):
        return "blocked"

    # Timeout indicators
    if any(x in error_str for x in ["timeout", "timed out"]) or "timeout" in error_type:
        return "timeout"

    # Connection errors
    if any(x in error_str for x in ["connection", "network", "dns", "refused"]) or "connection" in error_type:
        return "connection"

    return "unknown"


def scrape_solar_jobs(batch: int | None = None, total_batches: int = 4, run_id: str | None = None) -> tuple[pd.DataFrame, FilterStats, list[dict], dict, list[SearchError], ScrapeStats, DeepAnalytics]:
    """Scrape solar design/CAD jobs from multiple sources.

    Args:
        batch: If set, only run search terms for this batch (0-indexed).
               Used for parallel execution across multiple runners.
        total_batches: Number of batches to split search terms into.
        run_id: Unique identifier for this run (defaults to timestamp).

    Returns:
        Tuple of:
        - DataFrame of qualified jobs
        - FilterStats with run statistics
        - list of rejected lead dicts for labeling export
        - dict mapping row indices to ScoringResult for confidence calculation
        - list of SearchError objects for failed searches
        - ScrapeStats with scraping statistics
        - DeepAnalytics with detailed per-search diagnostic data
    """

    # Wide net search - generic role names that our filter will narrow down
    # The filter is strict, so we can afford to search broadly here
    all_search_terms = [
        # Core drafter/designer roles
        "electrical designer",
        "electrical drafter",
        "electrical design technician",
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
        "solar engineer",
        "solar design engineer",
        "PV designer",
        "PV engineer",
        "PV design engineer",
        "PV system designer",
        "photovoltaic designer",
        "photovoltaic engineer",
        "solar permit designer",
        "solar plans designer",

        # Tool-based searches (searches job descriptions, very targeted)
        "helioscope",
        "aurora solar",
        "PVsyst",
        "PV production modeling",
        "solar production modeling",
        "solaredge designer",

        # Task-based searches (finds jobs by description content)
        "string sizing solar",
        "stringing diagram",
        "module layout solar",
        "panel layout solar",
        "array layout solar",
        "single line diagram solar",
        "one-line diagram solar",
        "permit set solar",
        "plan set solar",
        "construction drawings solar",
        "wire schedule solar",
        "conduit schedule solar",

        # Context-based searches
        "residential solar",
        "commercial solar",
        "utility scale solar",
        "rooftop solar",

        # Energy storage (often paired with solar)
        "battery storage engineer",
        "energy storage engineer",
        "battery storage designer",
        "BESS engineer",
        "BESS designer",

        # Renewables general (catches solar+storage hybrid roles)
        "renewables engineer",
        "renewables designer",
        "renewable energy engineer",
        "renewable energy designer",
    ]

    # Split search terms into batches if batch mode is enabled
    if batch is not None:
        search_terms = get_batch_slice(all_search_terms, batch, total_batches)
        print(f"Batch {batch + 1}/{total_batches}: processing {len(search_terms)} search terms")
    else:
        search_terms = all_search_terms

    # Initialize scrape stats tracking
    if run_id is None:
        run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    scrape_stats = ScrapeStats(
        run_id=run_id,
        batch=batch,
        total_batches=total_batches,
        search_terms_total=len(search_terms)
    )

    # Initialize deep analytics tracking
    deep_analytics = DeepAnalytics(run_id=run_id, batch=batch)

    all_jobs = []
    search_errors = []  # Track all search failures
    results_per_term = 1000  # Wide net, filter does the work

    # Job sites to scrape - only use reliably working sources
    # Indeed: Most reliable, rarely blocks
    # LinkedIn: Works but rate limits quickly without proxies
    #
    # NOT SUPPORTED (as of Jan 2026):
    # - Google: Requires manual query syntax calibration (Issue #302)
    # - Glassdoor: Cloudflare blocked (Issue #272)
    #
    # RECENTLY FIXED (Jan 22, 2026):
    # - ZipRecruiter: Fixed selectors + multi-page scraping enabled (5 pages)
    all_sites = ["indeed", "linkedin", "zip_recruiter"]

    # Realistic browser user agents - rotate to avoid fingerprint detection
    # These should match what tls-client uses internally for consistency
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]

    # Optional proxy support - set SCRAPER_PROXIES env var with comma-separated proxies
    # Format: "user:pass@host:port,user:pass@host:port" or "host:port,host:port"
    proxy_env = os.environ.get("SCRAPER_PROXIES", "")
    proxies = [p.strip() for p in proxy_env.split(",") if p.strip()] if proxy_env else None
    if proxies:
        print(f"Using {len(proxies)} proxy server(s)")

    # Track which sites are blocked so we can skip them
    blocked_sites = set()

    consecutive_failures = 0
    max_consecutive_failures = 3  # Stop if 3 in a row fail (likely IP blocked)

    for i, term in enumerate(search_terms):
        print(f"Searching for: {term} ({i + 1}/{len(search_terms)})")

        # Get sites to try (exclude any that have been blocked this run)
        sites_to_try = [s for s in all_sites if s not in blocked_sites]
        if not sites_to_try:
            print("  All sites blocked! Stopping.")
            break

        # Rotate user agent for each search
        current_ua = random.choice(user_agents)

        term_jobs = []
        term_errors = []

        # Try each site individually so one failure doesn't block others
        for site in sites_to_try:
            site_success = False
            site_error = None
            scrape_stats.record_site_attempt(site)

            for attempt in range(2):  # 2 retries per site (less aggressive)
                # Track timing for deep analytics
                attempt_start = time.time()
                search_attempt = SearchAttempt(
                    search_term=term,
                    site=site,
                    retry_count=attempt,
                )

                try:
                    scrape_kwargs = {
                        "site_name": [site],
                        "search_term": term,
                        "location": "USA",
                        "results_wanted": results_per_term,
                        "country_indeed": "USA",
                        "user_agent": current_ua,
                        # Fetch full job descriptions for LinkedIn (required for filtering)
                        "linkedin_fetch_description": True,
                    }
                    if proxies:
                        scrape_kwargs["proxies"] = proxies

                    jobs = scrape_jobs(**scrape_kwargs)

                    # Record success in deep analytics
                    search_attempt.duration_ms = int((time.time() - attempt_start) * 1000)
                    search_attempt.success = True
                    search_attempt.jobs_found = len(jobs) if not jobs.empty else 0
                    deep_analytics.record_attempt(search_attempt)

                    if not jobs.empty:
                        jobs['search_term'] = term
                        jobs['source_site'] = site
                        term_jobs.append(jobs)
                        scrape_stats.record_site_success(site, len(jobs))
                        print(f"  [{site}] Found {len(jobs)} jobs")
                    else:
                        # No results but no error - still counts as successful search
                        scrape_stats.record_site_success(site, 0)
                        print(f"  [{site}] No results")
                    site_success = True
                    break
                except Exception as e:
                    site_error = e
                    error_type = classify_error(e)

                    # Record failure in deep analytics
                    search_attempt.duration_ms = int((time.time() - attempt_start) * 1000)
                    search_attempt.success = False
                    search_attempt.error_type = error_type
                    search_attempt.error_message = mask_credentials(str(e)[:500])
                    # Check for cloudflare indicators in error
                    error_lower = str(e).lower()
                    if "cloudflare" in error_lower or "403" in error_lower or "captcha" in error_lower:
                        search_attempt.cloudflare_detected = True
                        search_attempt.cloudflare_solved = False
                    deep_analytics.record_attempt(search_attempt)

                    print(f"  [{site}] Attempt {attempt + 1} failed ({error_type}): {mask_credentials(str(e)[:100])}")

                    # If blocked/403, mark site as blocked for this run
                    if error_type == "blocked":
                        print(f"  [{site}] Site appears blocked, skipping for rest of run")
                        blocked_sites.add(site)
                        scrape_stats.record_site_blocked(site, term, mask_credentials(str(e)))
                        break

                    # Brief delay before retry
                    if attempt < 1:
                        time.sleep(15)

            if not site_success and site not in blocked_sites:
                term_errors.append((site, site_error))
                scrape_stats.record_site_error(site)

            # Small delay between sites to be polite
            if site != sites_to_try[-1]:
                time.sleep(random.uniform(2, 5))

        # Track that we completed this search term
        scrape_stats.search_terms_completed += 1

        # Aggregate results for this term
        if term_jobs:
            combined = pd.concat(term_jobs, ignore_index=True)
            all_jobs.append(combined)
            print(f"  Total for '{term}': {len(combined)} jobs from {len(term_jobs)} site(s)")
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            print(f"  No results from any site for '{term}' ({consecutive_failures} consecutive failures)")

        # Record errors for sites that failed (but weren't just blocked)
        for site, error in term_errors:
            error_type = classify_error(error) if error else "unknown"
            # Extract context BEFORE truncating the message
            exception_class, status_code = extract_error_context(error) if error else ("", None)
            search_errors.append(SearchError(
                search_term=term,
                site=site,
                error_type=error_type,
                error_message=mask_credentials(str(error)[:500]) if error else "Unknown error",
                attempts=2,
                exception_class=exception_class,
                status_code=status_code
            ))

        if consecutive_failures >= max_consecutive_failures:
            print(f"\n  {max_consecutive_failures} consecutive failures - likely rate limited. Stopping early.")
            print(f"  Completed {i + 1 - max_consecutive_failures}/{len(search_terms)} terms before stopping.")
            break

        # Delay between searches to avoid rate limiting (skip after last term)
        if i < len(search_terms) - 1:
            delay = random.uniform(10, 20)  # 10-20 seconds between searches
            print(f"  Waiting {delay:.1f}s before next search...")
            time.sleep(delay)

    # Try browser-based scraping for Cloudflare-protected sites (ZipRecruiter, Glassdoor)
    # Uses Camoufox (Firefox-based anti-detect browser) for better CI compatibility
    # Only runs if ENABLE_BROWSER_SCRAPING=1 and camoufox is available
    if os.environ.get("ENABLE_BROWSER_SCRAPING") == "1":
        try:
            from camoufox_scraper import run_camoufox_scraper, CAMOUFOX_AVAILABLE, CAMOUFOX_IMPORT_ERROR
            print("\n--- Camoufox Browser Scraping (ZipRecruiter, Glassdoor) ---")
            print(f"  CAMOUFOX_AVAILABLE: {CAMOUFOX_AVAILABLE}")
            if not CAMOUFOX_AVAILABLE:
                print(f"  WARNING: Camoufox module loaded but browser not available!")
                print(f"  Import error: {CAMOUFOX_IMPORT_ERROR}")
            browser_jobs, browser_errors, browser_attempts, browser_diagnostics = run_camoufox_scraper(search_terms)
            print(f"  Camoufox returned: {len(browser_jobs)} jobs, {len(browser_errors)} errors, {len(browser_attempts)} attempts")
            print(f"  Browser diagnostics: started={browser_diagnostics.get('browser_started')}, error={browser_diagnostics.get('browser_start_error', 'none')[:100] if browser_diagnostics.get('browser_start_error') else 'none'}")
            if not browser_jobs.empty:
                all_jobs.append(browser_jobs)
                # Update scrape stats for browser-scraped sites
                for attempt in browser_attempts:
                    site = attempt.get("site", "browser")
                    scrape_stats.record_site_attempt(site)
                    if attempt.get("success"):
                        scrape_stats.record_site_success(site, attempt.get("jobs_found", 0))
                    else:
                        scrape_stats.record_site_error(site)
            # Convert browser errors to SearchError format
            for err in browser_errors:
                search_errors.append(SearchError(
                    search_term=err.get("search_term", ""),
                    site=err.get("site", "browser"),
                    error_type=err.get("error_type", "unknown"),
                    error_message=mask_credentials(err.get("error_message", "")),
                    attempts=1
                ))
            # Add browser search attempts to deep analytics
            for attempt_dict in browser_attempts:
                deep_analytics.record_attempt(SearchAttempt(
                    search_term=attempt_dict.get("search_term", ""),
                    site=attempt_dict.get("site", "browser"),
                    timestamp=attempt_dict.get("timestamp", ""),
                    success=attempt_dict.get("success", False),
                    jobs_found=attempt_dict.get("jobs_found", 0),
                    duration_ms=attempt_dict.get("duration_ms", 0),
                    error_type=attempt_dict.get("error_type"),
                    error_message=mask_credentials(attempt_dict.get("error_message") or ""),
                    selectors_tried=attempt_dict.get("selectors_tried", []),
                    selector_matched=attempt_dict.get("selector_matched"),
                    cloudflare_detected=attempt_dict.get("cloudflare_detected", False),
                    cloudflare_solved=attempt_dict.get("cloudflare_solved"),
                    page_title=attempt_dict.get("page_title"),
                ))
            # Record browser diagnostics in deep analytics
            if browser_diagnostics:
                deep_analytics.record_browser_session(browser_diagnostics)
                print(f"  Recorded browser session diagnostics in deep_analytics")
        except ImportError as e:
            print("\nCamoufox scraper not available (camoufox not installed)")
            print(f"Import error: {e}")
            print("Install with: pip install camoufox[geoip] && camoufox fetch")
        except Exception as e:
            import traceback
            print(f"\nCamoufox browser scraping failed: {str(e)[:200]}")
            print("Full traceback:")
            traceback.print_exc()
    else:
        print("\nENABLE_BROWSER_SCRAPING not set - skipping ZipRecruiter/Glassdoor")

    if not all_jobs:
        print("No jobs found!")
        scrape_stats.finish()
        return pd.DataFrame(), FilterStats(), [], {}, search_errors, scrape_stats, deep_analytics

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
            result = score_job(row['description'], row.get('company'), title=row.get('title'))

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
        # Update scrape stats with results
        scrape_stats.total_jobs_raw = before_filter
        scrape_stats.total_jobs_filtered = len(df)
    else:
        print("Warning: No description column available for filtering")
        scrape_stats.total_jobs_raw = len(df)
        scrape_stats.total_jobs_filtered = len(df)

    scrape_stats.finish()
    return df, stats, rejected_leads, scoring_results, search_errors, scrape_stats, deep_analytics


def export_search_errors(
    search_errors: list[SearchError],
    output_dir: Path,
    run_id: str,
    batch: int | None = None
) -> Path | None:
    """Export search errors to JSON for dashboard review.

    Args:
        search_errors: List of SearchError objects
        output_dir: Directory to write JSON file
        run_id: Timestamp or identifier for this run
        batch: Optional batch number if running in parallel mode

    Returns:
        Path to the created file, or None if no errors
    """
    if not search_errors:
        return None

    # Group errors by type for summary
    error_summary = {}
    for err in search_errors:
        error_summary[err.error_type] = error_summary.get(err.error_type, 0) + 1

    export_data = {
        "metadata": {
            "created": datetime.now().isoformat(),
            "run_id": run_id,
            "batch": batch,
            "total_errors": len(search_errors),
            "error_summary": error_summary
        },
        "errors": [err.to_dict() for err in search_errors]
    }

    filename = f"search_errors_{run_id}.json" if batch is None else f"search_errors_{run_id}_batch{batch}.json"
    filepath = output_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2)

    return filepath


def export_run_stats(
    scrape_stats: ScrapeStats,
    filter_stats: FilterStats,
    output_dir: Path,
    unique_companies: int = 0
) -> Path:
    """Export comprehensive run statistics to JSON for dashboard.

    Args:
        scrape_stats: Scraping statistics (sites, jobs found, blocked, etc.)
        filter_stats: Filtering statistics (qualified, rejected, reasons)
        output_dir: Directory to write JSON file
        unique_companies: Number of unique companies in final results

    Returns:
        Path to the created file
    """
    # Update unique companies count
    scrape_stats.unique_companies = unique_companies

    # Combine scrape stats with filter stats
    export_data = scrape_stats.to_dict()

    # Add filter statistics
    export_data["filter"] = {
        "total_processed": filter_stats.total_processed,
        "qualified": filter_stats.total_qualified,
        "rejected": filter_stats.total_rejected,
        "pass_rate": round(filter_stats.pass_rate, 2),
        "company_blocked": filter_stats.company_blocked,
        "rejection_reasons": dict(filter_stats.rejection_categories.most_common(10)),
        "qualification_tiers": dict(filter_stats.qualification_tiers)
    }

    filename = f"run_stats_{scrape_stats.run_id}.json"
    if scrape_stats.batch is not None:
        filename = f"run_stats_{scrape_stats.run_id}_batch{scrape_stats.batch}.json"

    filepath = output_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2)

    return filepath


def export_deep_analytics(
    deep_analytics: DeepAnalytics,
    output_dir: Path,
) -> Path:
    """Export deep analytics to JSON for debugging and diagnostics.

    This export provides detailed per-search-attempt data to help diagnose
    issues with LinkedIn, Indeed, ZipRecruiter, and Glassdoor scraping.

    Args:
        deep_analytics: DeepAnalytics object with all search attempts
        output_dir: Directory to write JSON file

    Returns:
        Path to the created file
    """
    export_data = deep_analytics.to_dict()

    filename = f"deep_analytics_{deep_analytics.run_id}.json"
    if deep_analytics.batch is not None:
        filename = f"deep_analytics_{deep_analytics.run_id}_batch{deep_analytics.batch}.json"

    filepath = output_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2)

    return filepath


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

    # Check for batch mode (set by GitHub Actions matrix)
    batch_env = os.environ.get("SCRAPER_BATCH")
    total_batches_env = os.environ.get("SCRAPER_TOTAL_BATCHES", "4")

    batch = int(batch_env) if batch_env is not None else None
    total_batches = int(total_batches_env)

    # Validate batch parameters to fail fast on misconfiguration
    if batch is not None:
        if batch < 0:
            raise ValueError(f"SCRAPER_BATCH must be >= 0, got {batch}")
        if total_batches < 1:
            raise ValueError(f"SCRAPER_TOTAL_BATCHES must be >= 1, got {total_batches}")
        if batch >= total_batches:
            raise ValueError(f"SCRAPER_BATCH ({batch}) must be < SCRAPER_TOTAL_BATCHES ({total_batches})")

    # Ensure output directory exists (needed for exports even if no jobs)
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Scrape jobs
    raw_jobs, stats, rejected_leads, scoring_results, search_errors, scrape_stats, deep_analytics = scrape_solar_jobs(
        batch=batch, total_batches=total_batches, run_id=timestamp
    )

    # Always export search errors if any occurred
    if search_errors:
        errors_path = export_search_errors(search_errors, output_dir, timestamp, batch)
        print(f"\nExported {len(search_errors)} search errors to: {errors_path}")

    # Always export deep analytics for diagnostics
    analytics_path = export_deep_analytics(deep_analytics, output_dir)
    print(f"Exported deep analytics to: {analytics_path}")

    if raw_jobs.empty:
        print("No jobs to process. Exiting.")
        # Still print stats even if empty
        print_filter_stats(stats)
        # Export run stats even with no results
        stats_path = export_run_stats(scrape_stats, stats, output_dir, unique_companies=0)
        print(f"\nExported run stats to: {stats_path}")
        return

    # Process and dedupe
    leads = process_jobs(raw_jobs, scoring_results)

    if leads.empty:
        print("No leads after processing. Exiting.")
        print_filter_stats(stats)
        # Export run stats even with no results
        stats_path = export_run_stats(scrape_stats, stats, output_dir, unique_companies=0)
        print(f"\nExported run stats to: {stats_path}")
        return

    # Print filter statistics
    print_filter_stats(stats)

    # Export rejected leads for labeling review
    if rejected_leads:
        rejected_path = export_rejected_leads(rejected_leads, output_dir, timestamp)
        print(f"\nExported {min(100, len(rejected_leads))} rejected leads to: {rejected_path}")

    # Save qualified leads to CSV (include batch number if in batch mode to avoid collisions)
    batch_suffix = f"_batch{batch}" if batch is not None else ""
    output_file = output_dir / f"solar_leads_{timestamp}{batch_suffix}.csv"
    # Sanitize to prevent CSV injection from malicious job descriptions
    sanitized_leads = sanitize_dataframe_for_csv(leads)
    sanitized_leads.to_csv(output_file, index=False)

    # Export comprehensive run stats
    stats_path = export_run_stats(scrape_stats, stats, output_dir, unique_companies=len(leads))
    print(f"\nExported run stats to: {stats_path}")

    print()
    print("=" * 50)
    print(f"Saved {len(leads)} leads to: {output_file}")
    print("=" * 50)

    # Preview first few
    print("\nPreview of leads:")
    print(leads.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
