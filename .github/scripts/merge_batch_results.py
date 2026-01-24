#!/usr/bin/env python3
"""Merge batch results from parallel scraper runs.

This script is called by the GitHub Actions workflow to combine results
from multiple parallel scraper batches into single merged output files.

Merges:
- CSV files (leads) - deduped by company, sorted by confidence score
- Search error JSON files
- Run stats JSON files
- Deep analytics JSON files

Usage:
    python .github/scripts/merge_batch_results.py

Environment:
    Expects batch artifacts in batches/ directory (downloaded by workflow)
    Outputs merged files to output/ directory
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd


def merge_csv_files(csv_files: list[Path], output_dir: Path, timestamp: str) -> Path | None:
    """Merge lead CSV files, deduping by company.

    Args:
        csv_files: List of CSV file paths to merge
        output_dir: Directory to write merged output
        timestamp: Timestamp string for output filename

    Returns:
        Path to merged CSV file, or None if no files to merge
    """
    if not csv_files:
        print("No CSV files found")
        return None

    print(f"Found {len(csv_files)} batch CSV files")

    # Read and combine all CSVs
    dfs = [pd.read_csv(f) for f in csv_files]
    combined = pd.concat(dfs, ignore_index=True)
    print(f"Combined: {len(combined)} total rows")

    # Sort by confidence score (descending) for deterministic deduplication
    # This ensures we keep the highest-confidence occurrence of each company
    if "confidence_score" in combined.columns:
        combined = combined.sort_values(
            "confidence_score", ascending=False, na_position="last"
        )

    # Dedupe by company (keep first = highest confidence after sort)
    combined = combined.drop_duplicates(subset=["company"], keep="first")
    print(f"After deduping: {len(combined)} unique companies")

    # Save merged output
    output_file = output_dir / f"solar_leads_{timestamp}.csv"
    combined.to_csv(output_file, index=False)
    print(f"Saved merged leads to: {output_file}")

    return output_file


def merge_search_errors(error_files: list[Path], output_dir: Path, timestamp: str) -> Path | None:
    """Merge search error JSON files.

    Args:
        error_files: List of error JSON file paths to merge
        output_dir: Directory to write merged output
        timestamp: Timestamp string for output filename

    Returns:
        Path to merged JSON file, or None if no files to merge
    """
    if not error_files:
        return None

    print(f"Found {len(error_files)} search error files")

    all_errors = []
    total_by_type = {}

    for filepath in error_files:
        with open(filepath) as f:
            data = json.load(f)
        all_errors.extend(data.get("errors", []))
        for error_type, count in data.get("metadata", {}).get("error_summary", {}).items():
            total_by_type[error_type] = total_by_type.get(error_type, 0) + count

    merged_errors = {
        "metadata": {
            "created": datetime.now().isoformat(),
            "run_id": timestamp,
            "total_errors": len(all_errors),
            "error_summary": total_by_type,
            "source_files": len(error_files),
        },
        "errors": all_errors,
    }

    error_output = output_dir / f"search_errors_{timestamp}.json"
    with open(error_output, "w") as f:
        json.dump(merged_errors, f, indent=2)
    print(f"Saved merged search errors to: {error_output}")
    print(f"Error summary: {total_by_type}")

    return error_output


def merge_run_stats(stats_files: list[Path], output_dir: Path, timestamp: str) -> Path | None:
    """Merge run stats JSON files.

    Args:
        stats_files: List of stats JSON file paths to merge
        output_dir: Directory to write merged output
        timestamp: Timestamp string for output filename

    Returns:
        Path to merged JSON file, or None if no files to merge
    """
    if not stats_files:
        return None

    print(f"Found {len(stats_files)} run stats files")

    # Initialize accumulators
    combined_sites = {}
    combined_blocked = []
    total_search_terms = 0
    completed_search_terms = 0
    total_jobs_raw = 0
    total_jobs_filtered = 0
    total_unique_companies = 0
    filter_processed = 0
    filter_qualified = 0
    filter_rejected = 0
    filter_company_blocked = 0
    rejection_reasons = {}
    qualification_tiers = {}
    start_times = []
    end_times = []
    batches_processed = []

    for filepath in stats_files:
        with open(filepath) as f:
            data = json.load(f)

        # Track batch info
        if data.get("metadata", {}).get("batch") is not None:
            batches_processed.append(data["metadata"]["batch"])
        if data.get("metadata", {}).get("start_time"):
            start_times.append(data["metadata"]["start_time"])
        if data.get("metadata", {}).get("end_time"):
            end_times.append(data["metadata"]["end_time"])

        # Accumulate search term counts
        total_search_terms += data.get("search_terms", {}).get("total", 0)
        completed_search_terms += data.get("search_terms", {}).get("completed", 0)

        # Merge site-level stats
        for site_name, site_data in data.get("sites", {}).items():
            if site_name not in combined_sites:
                combined_sites[site_name] = {
                    "site": site_name,
                    "searches_attempted": 0,
                    "searches_successful": 0,
                    "total_jobs_found": 0,
                    "blocked": False,
                    "blocked_at_term": None,
                    "error_count": 0,
                }
            combined_sites[site_name]["searches_attempted"] += site_data.get("searches_attempted", 0)
            combined_sites[site_name]["searches_successful"] += site_data.get("searches_successful", 0)
            combined_sites[site_name]["total_jobs_found"] += site_data.get("total_jobs_found", 0)
            combined_sites[site_name]["error_count"] += site_data.get("error_count", 0)
            if site_data.get("blocked"):
                combined_sites[site_name]["blocked"] = True
                if not combined_sites[site_name]["blocked_at_term"]:
                    combined_sites[site_name]["blocked_at_term"] = site_data.get("blocked_at_term")

        # Accumulate blocked sites and result counts
        combined_blocked.extend(data.get("blocked_sites", []))
        total_jobs_raw += data.get("results", {}).get("total_jobs_raw", 0)
        total_jobs_filtered += data.get("results", {}).get("total_jobs_filtered", 0)
        total_unique_companies += data.get("results", {}).get("unique_companies", 0)

        # Accumulate filter stats
        filter_data = data.get("filter", {})
        filter_processed += filter_data.get("total_processed", 0)
        filter_qualified += filter_data.get("qualified", 0)
        filter_rejected += filter_data.get("rejected", 0)
        filter_company_blocked += filter_data.get("company_blocked", 0)
        for reason, count in filter_data.get("rejection_reasons", {}).items():
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + count
        for tier, count in filter_data.get("qualification_tiers", {}).items():
            qualification_tiers[tier] = qualification_tiers.get(tier, 0) + count

    # Calculate success rates for each site
    for site_name in combined_sites:
        attempted = combined_sites[site_name]["searches_attempted"]
        successful = combined_sites[site_name]["searches_successful"]
        combined_sites[site_name]["success_rate"] = (
            round(successful / attempted * 100, 1) if attempted > 0 else 0.0
        )

    # Build merged stats object
    merged_stats = {
        "metadata": {
            "created": datetime.now().isoformat(),
            "run_id": timestamp,
            "batches_processed": sorted(batches_processed) if batches_processed else None,
            "total_batches": len(stats_files),
            "start_time": min(start_times) if start_times else None,
            "end_time": max(end_times) if end_times else None,
        },
        "search_terms": {
            "total": total_search_terms,
            "completed": completed_search_terms,
            "completion_rate": (
                round(completed_search_terms / total_search_terms * 100, 1)
                if total_search_terms > 0
                else 0.0
            ),
        },
        "sites": combined_sites,
        "blocked_sites": combined_blocked,
        "results": {
            "total_jobs_raw": total_jobs_raw,
            "total_jobs_filtered": total_jobs_filtered,
            "unique_companies": total_unique_companies,
            "filter_rate": (
                round((1 - total_jobs_filtered / total_jobs_raw) * 100, 1)
                if total_jobs_raw > 0
                else 0.0
            ),
        },
        "filter": {
            "total_processed": filter_processed,
            "qualified": filter_qualified,
            "rejected": filter_rejected,
            "pass_rate": (
                round(filter_qualified / filter_processed * 100, 2)
                if filter_processed > 0
                else 0.0
            ),
            "company_blocked": filter_company_blocked,
            "rejection_reasons": dict(sorted(rejection_reasons.items(), key=lambda x: -x[1])[:10]),
            "qualification_tiers": qualification_tiers,
        },
    }

    stats_output = output_dir / f"run_stats_{timestamp}.json"
    with open(stats_output, "w") as f:
        json.dump(merged_stats, f, indent=2)
    print(f"Saved merged run stats to: {stats_output}")
    print(f"Search terms: {completed_search_terms}/{total_search_terms}")
    print(f"Jobs: {total_jobs_raw} raw -> {total_jobs_filtered} filtered")

    return stats_output


def merge_deep_analytics(analytics_files: list[Path], output_dir: Path, timestamp: str) -> Path | None:
    """Merge deep analytics JSON files.

    Args:
        analytics_files: List of analytics JSON file paths to merge
        output_dir: Directory to write merged output
        timestamp: Timestamp string for output filename

    Returns:
        Path to merged JSON file, or None if no files to merge
    """
    if not analytics_files:
        return None

    print(f"Found {len(analytics_files)} deep analytics files")

    all_raw_attempts = []
    batches_processed = []

    for filepath in analytics_files:
        with open(filepath) as f:
            data = json.load(f)
        all_raw_attempts.extend(data.get("raw_attempts", []))
        if data.get("metadata", {}).get("batch") is not None:
            batches_processed.append(data["metadata"]["batch"])

    # Compute site summaries
    site_data = {}
    for attempt in all_raw_attempts:
        site = attempt.get("site", "unknown")
        if site not in site_data:
            site_data[site] = {
                "total_attempts": 0,
                "successful_attempts": 0,
                "total_jobs": 0,
                "total_duration_ms": 0,
                "errors_by_type": {},
                "cloudflare_encounters": 0,
                "cloudflare_solved": 0,
            }
        s = site_data[site]
        s["total_attempts"] += 1
        s["total_duration_ms"] += attempt.get("duration_ms", 0)
        if attempt.get("success"):
            s["successful_attempts"] += 1
            s["total_jobs"] += attempt.get("jobs_found", 0)
        if attempt.get("error_type"):
            err_type = attempt["error_type"]
            s["errors_by_type"][err_type] = s["errors_by_type"].get(err_type, 0) + 1
        if attempt.get("cloudflare_detected"):
            s["cloudflare_encounters"] += 1
            if attempt.get("cloudflare_solved") is True:
                s["cloudflare_solved"] += 1

    # Calculate derived metrics for each site
    for site, s in site_data.items():
        s["success_rate"] = (
            round(s["successful_attempts"] / s["total_attempts"] * 100, 1)
            if s["total_attempts"] > 0
            else 0
        )
        s["avg_duration_ms"] = (
            round(s["total_duration_ms"] / s["total_attempts"])
            if s["total_attempts"] > 0
            else 0
        )
        s["avg_jobs_per_success"] = (
            round(s["total_jobs"] / s["successful_attempts"], 1)
            if s["successful_attempts"] > 0
            else 0
        )

    # Error analysis
    errors = [a for a in all_raw_attempts if not a.get("success")]
    error_by_type = {}
    for e in errors:
        err_type = e.get("error_type", "unknown")
        error_by_type[err_type] = error_by_type.get(err_type, 0) + 1

    # Cloudflare analysis
    cf_attempts = [a for a in all_raw_attempts if a.get("cloudflare_detected")]
    cf_analysis = {
        "total_encounters": len(cf_attempts),
        "solved": sum(1 for a in cf_attempts if a.get("cloudflare_solved") is True),
        "failed": sum(1 for a in cf_attempts if a.get("cloudflare_solved") is False),
    }
    if cf_attempts:
        cf_analysis["solve_rate"] = round(cf_analysis["solved"] / len(cf_attempts) * 100, 1)

    merged_analytics = {
        "metadata": {
            "merged_at": datetime.now().isoformat(),
            "batches_processed": sorted(batches_processed) if batches_processed else None,
            "total_search_attempts": len(all_raw_attempts),
        },
        "site_summaries": site_data,
        "error_analysis": {"total_errors": len(errors), "by_type": error_by_type},
        "cloudflare_analysis": cf_analysis,
        "raw_attempts": all_raw_attempts,
    }

    analytics_output = output_dir / f"deep_analytics_{timestamp}.json"
    with open(analytics_output, "w") as f:
        json.dump(merged_analytics, f, indent=2)
    print(f"Saved merged deep analytics to: {analytics_output}")
    print(f"Total search attempts: {len(all_raw_attempts)}")
    for site, s in site_data.items():
        print(f"  {site}: {s['success_rate']}% success, {s['total_jobs']} jobs, {s['avg_duration_ms']}ms avg")
    if cf_analysis["total_encounters"] > 0:
        print(f"Cloudflare: {cf_analysis['solved']}/{cf_analysis['total_encounters']} solved")

    return analytics_output


def main():
    """Main entry point for batch result merging."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    batches_dir = Path("batches")

    # Merge CSV files
    csv_files = list(batches_dir.glob("**/solar_leads_*.csv"))
    merge_csv_files(csv_files, output_dir, timestamp)

    # Merge search error files
    error_files = list(batches_dir.glob("**/search_errors_*.json"))
    merge_search_errors(error_files, output_dir, timestamp)

    # Merge run stats files
    stats_files = list(batches_dir.glob("**/run_stats_*.json"))
    merge_run_stats(stats_files, output_dir, timestamp)

    # Merge deep analytics files
    analytics_files = list(batches_dir.glob("**/deep_analytics_*.json"))
    merge_deep_analytics(analytics_files, output_dir, timestamp)


if __name__ == "__main__":
    main()
