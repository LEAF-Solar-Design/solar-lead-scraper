"""
Upload scraper results to the ops-dashboard.
Called by GitHub Actions after scraping completes.
"""

import json
import os
import glob
import requests


def get_latest_csv():
    """Find the most recent CSV file in output directory by filename date."""
    csv_files = glob.glob("output/solar_leads_*.csv")
    if not csv_files:
        raise FileNotFoundError("No CSV files found in output/")
    # Sort by filename (which contains timestamp) to get the latest
    return max(csv_files)


def get_search_error_files():
    """Find all search error JSON files in output directory."""
    return glob.glob("output/search_errors_*.json")


def get_run_stats_files():
    """Find all run stats JSON files in output directory."""
    return glob.glob("output/run_stats_*.json")


def upload_to_dashboard(csv_path: str):
    """Upload CSV to the dashboard API."""
    dashboard_url = os.environ.get("DASHBOARD_URL")
    api_key = os.environ.get("DASHBOARD_API_KEY")

    if not dashboard_url:
        raise ValueError("DASHBOARD_URL environment variable not set")
    if not api_key:
        raise ValueError("DASHBOARD_API_KEY environment variable not set")

    # Read CSV content
    with open(csv_path, "r") as f:
        csv_content = f.read()

    # POST to dashboard API
    url = f"{dashboard_url.rstrip('/')}/api/jobs/ingest"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "text/csv",
    }

    print(f"Uploading {csv_path} to {url}")
    response = requests.post(url, data=csv_content, headers=headers)

    if response.status_code == 200:
        result = response.json()
        print(f"Success! Imported {result.get('count', '?')} leads")
        return result
    else:
        print(f"Upload failed: {response.status_code}")
        print(response.text)
        raise Exception(f"Upload failed with status {response.status_code}")


def merge_search_errors(error_files: list[str]) -> dict:
    """Merge multiple search error files into a single payload.

    Args:
        error_files: List of paths to search error JSON files

    Returns:
        Merged error data with combined metadata and errors list
    """
    all_errors = []
    total_by_type = {}

    for filepath in error_files:
        with open(filepath, "r") as f:
            data = json.load(f)

        all_errors.extend(data.get("errors", []))

        # Aggregate error summary
        for error_type, count in data.get("metadata", {}).get("error_summary", {}).items():
            total_by_type[error_type] = total_by_type.get(error_type, 0) + count

    return {
        "metadata": {
            "total_errors": len(all_errors),
            "error_summary": total_by_type,
            "source_files": len(error_files)
        },
        "errors": all_errors
    }


def upload_search_errors(error_data: dict):
    """Upload search errors to the dashboard API.

    Args:
        error_data: Merged error data from merge_search_errors()
    """
    dashboard_url = os.environ.get("DASHBOARD_URL")
    api_key = os.environ.get("DASHBOARD_API_KEY")

    if not dashboard_url or not api_key:
        print("Dashboard credentials not set - skipping search error upload")
        return

    url = f"{dashboard_url.rstrip('/')}/api/scraper/errors"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print(f"Uploading {error_data['metadata']['total_errors']} search errors to {url}")
    response = requests.post(url, json=error_data, headers=headers)

    if response.status_code == 200:
        result = response.json()
        print(f"Search errors uploaded: {result.get('message', 'OK')}")
        return result
    else:
        print(f"Search error upload failed: {response.status_code}")
        print(response.text)
        # Don't raise - search error upload is not critical


def merge_run_stats(stats_files: list[str]) -> dict:
    """Merge multiple run stats files into a single payload.

    Combines stats from parallel batch runs into aggregate statistics.

    Args:
        stats_files: List of paths to run stats JSON files

    Returns:
        Merged stats with combined metrics across all batches
    """
    if not stats_files:
        return {}

    # Aggregate site statistics
    combined_sites = {}
    combined_blocked = []
    total_search_terms = 0
    completed_search_terms = 0
    total_jobs_raw = 0
    total_jobs_filtered = 0
    total_unique_companies = 0

    # Filter stats aggregation
    filter_processed = 0
    filter_qualified = 0
    filter_rejected = 0
    filter_company_blocked = 0
    rejection_reasons = {}
    qualification_tiers = {}

    # Track timing
    start_times = []
    end_times = []
    batches_processed = []

    for filepath in stats_files:
        with open(filepath, "r") as f:
            data = json.load(f)

        # Track batch info
        if data.get("metadata", {}).get("batch") is not None:
            batches_processed.append(data["metadata"]["batch"])

        # Timing
        if data.get("metadata", {}).get("start_time"):
            start_times.append(data["metadata"]["start_time"])
        if data.get("metadata", {}).get("end_time"):
            end_times.append(data["metadata"]["end_time"])

        # Search terms
        total_search_terms += data.get("search_terms", {}).get("total", 0)
        completed_search_terms += data.get("search_terms", {}).get("completed", 0)

        # Site stats - merge by site name
        for site_name, site_data in data.get("sites", {}).items():
            if site_name not in combined_sites:
                combined_sites[site_name] = {
                    "site": site_name,
                    "searches_attempted": 0,
                    "searches_successful": 0,
                    "total_jobs_found": 0,
                    "blocked": False,
                    "blocked_at_term": None,
                    "error_count": 0
                }
            combined_sites[site_name]["searches_attempted"] += site_data.get("searches_attempted", 0)
            combined_sites[site_name]["searches_successful"] += site_data.get("searches_successful", 0)
            combined_sites[site_name]["total_jobs_found"] += site_data.get("total_jobs_found", 0)
            combined_sites[site_name]["error_count"] += site_data.get("error_count", 0)
            # If blocked in any batch, mark as blocked
            if site_data.get("blocked"):
                combined_sites[site_name]["blocked"] = True
                if not combined_sites[site_name]["blocked_at_term"]:
                    combined_sites[site_name]["blocked_at_term"] = site_data.get("blocked_at_term")

        # Blocked sites list
        combined_blocked.extend(data.get("blocked_sites", []))

        # Results
        total_jobs_raw += data.get("results", {}).get("total_jobs_raw", 0)
        total_jobs_filtered += data.get("results", {}).get("total_jobs_filtered", 0)
        total_unique_companies += data.get("results", {}).get("unique_companies", 0)

        # Filter stats
        filter_data = data.get("filter", {})
        filter_processed += filter_data.get("total_processed", 0)
        filter_qualified += filter_data.get("qualified", 0)
        filter_rejected += filter_data.get("rejected", 0)
        filter_company_blocked += filter_data.get("company_blocked", 0)

        # Merge rejection reasons
        for reason, count in filter_data.get("rejection_reasons", {}).items():
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + count

        # Merge qualification tiers
        for tier, count in filter_data.get("qualification_tiers", {}).items():
            qualification_tiers[tier] = qualification_tiers.get(tier, 0) + count

    # Calculate success rates for combined sites
    for site_name in combined_sites:
        attempted = combined_sites[site_name]["searches_attempted"]
        successful = combined_sites[site_name]["searches_successful"]
        combined_sites[site_name]["success_rate"] = round(successful / attempted * 100, 1) if attempted > 0 else 0.0

    # Build merged payload
    return {
        "metadata": {
            "run_id": stats_files[0].split("run_stats_")[1].split("_batch")[0].replace(".json", "") if stats_files else None,
            "batches_processed": sorted(batches_processed) if batches_processed else None,
            "total_batches": len(stats_files),
            "start_time": min(start_times) if start_times else None,
            "end_time": max(end_times) if end_times else None,
        },
        "search_terms": {
            "total": total_search_terms,
            "completed": completed_search_terms,
            "completion_rate": round(completed_search_terms / total_search_terms * 100, 1) if total_search_terms > 0 else 0.0
        },
        "sites": combined_sites,
        "blocked_sites": combined_blocked,
        "results": {
            "total_jobs_raw": total_jobs_raw,
            "total_jobs_filtered": total_jobs_filtered,
            "unique_companies": total_unique_companies,
            "filter_rate": round((1 - total_jobs_filtered / total_jobs_raw) * 100, 1) if total_jobs_raw > 0 else 0.0
        },
        "filter": {
            "total_processed": filter_processed,
            "qualified": filter_qualified,
            "rejected": filter_rejected,
            "pass_rate": round(filter_qualified / filter_processed * 100, 2) if filter_processed > 0 else 0.0,
            "company_blocked": filter_company_blocked,
            "rejection_reasons": dict(sorted(rejection_reasons.items(), key=lambda x: -x[1])[:10]),
            "qualification_tiers": qualification_tiers
        }
    }


def upload_run_stats(stats_data: dict):
    """Upload run statistics to the dashboard API.

    Args:
        stats_data: Merged stats data from merge_run_stats()
    """
    dashboard_url = os.environ.get("DASHBOARD_URL")
    api_key = os.environ.get("DASHBOARD_API_KEY")

    if not dashboard_url or not api_key:
        print("Dashboard credentials not set - skipping run stats upload")
        return

    url = f"{dashboard_url.rstrip('/')}/api/scraper/stats"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Print summary before upload
    print("\n" + "=" * 50)
    print("RUN STATISTICS SUMMARY")
    print("=" * 50)
    print(f"Search terms: {stats_data['search_terms']['completed']}/{stats_data['search_terms']['total']} ({stats_data['search_terms']['completion_rate']}%)")
    print(f"Jobs found: {stats_data['results']['total_jobs_raw']} raw -> {stats_data['results']['total_jobs_filtered']} filtered")
    print(f"Unique companies: {stats_data['results']['unique_companies']}")

    print("\nSite performance:")
    for site_name, site_data in stats_data.get("sites", {}).items():
        status = "BLOCKED" if site_data.get("blocked") else "OK"
        print(f"  {site_name}: {site_data['total_jobs_found']} jobs, {site_data['success_rate']}% success [{status}]")

    if stats_data.get("blocked_sites"):
        print(f"\nBlocked sites: {len(stats_data['blocked_sites'])}")
        for blocked in stats_data["blocked_sites"][:3]:  # Show first 3
            print(f"  - {blocked['site']} at '{blocked['search_term'][:30]}...'")

    print("=" * 50)

    print(f"\nUploading run stats to {url}")
    response = requests.post(url, json=stats_data, headers=headers)

    if response.status_code == 200:
        result = response.json()
        print(f"Run stats uploaded: {result.get('message', 'OK')}")
        return result
    else:
        print(f"Run stats upload failed: {response.status_code}")
        print(response.text)
        # Don't raise - stats upload is not critical


def main():
    # Upload leads CSV
    try:
        csv_path = get_latest_csv()
        print(f"Found latest CSV: {csv_path}")
        upload_to_dashboard(csv_path)
    except FileNotFoundError:
        print("No CSV files found in output/ - scraper may have produced no results")
        print("Skipping leads upload (this is not a fatal error)")

    # Upload run stats (always - even if no leads)
    stats_files = get_run_stats_files()
    if stats_files:
        print(f"\nFound {len(stats_files)} run stats file(s)")
        merged_stats = merge_run_stats(stats_files)
        upload_run_stats(merged_stats)
    else:
        print("\nNo run stats to upload")

    # Upload search errors (if any)
    error_files = get_search_error_files()
    if error_files:
        print(f"\nFound {len(error_files)} search error file(s)")
        merged_errors = merge_search_errors(error_files)
        upload_search_errors(merged_errors)
    else:
        print("\nNo search errors to upload")


if __name__ == "__main__":
    main()
