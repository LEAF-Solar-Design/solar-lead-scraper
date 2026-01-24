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


def get_deep_analytics_files():
    """Find all deep analytics JSON files in output directory."""
    return glob.glob("output/deep_analytics_*.json")


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
        try:
            result = response.json()
        except requests.exceptions.JSONDecodeError:
            print("Warning: Success response was not valid JSON")
            return {"count": "unknown"}
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
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Skipping corrupted error file {filepath}: {e}")
            continue

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


def merge_deep_analytics(analytics_files: list[str]) -> dict:
    """Merge multiple deep analytics files into a single comprehensive report.

    Combines analytics from parallel batch runs to provide unified diagnostic data.

    Args:
        analytics_files: List of paths to deep analytics JSON files

    Returns:
        Merged analytics with combined site summaries, error analysis, etc.
    """
    if not analytics_files:
        return {}

    # Collect all raw attempts across batches
    all_raw_attempts = []
    batches_processed = []
    start_times = []

    for filepath in analytics_files:
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Skipping corrupted analytics file {filepath}: {e}")
            continue

        all_raw_attempts.extend(data.get("raw_attempts", []))

        metadata = data.get("metadata", {})
        if metadata.get("batch") is not None:
            batches_processed.append(metadata["batch"])
        if metadata.get("generated_at"):
            start_times.append(metadata["generated_at"])

    # Compute aggregated site summaries
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
                "cloudflare_failed": 0,
                "http_status_codes": {},
                "selectors_used": {},
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
            elif attempt.get("cloudflare_solved") is False:
                s["cloudflare_failed"] += 1
        if attempt.get("http_status"):
            status_str = str(attempt["http_status"])
            s["http_status_codes"][status_str] = s["http_status_codes"].get(status_str, 0) + 1
        if attempt.get("selector_matched"):
            sel = attempt["selector_matched"]
            s["selectors_used"][sel] = s["selectors_used"].get(sel, 0) + 1

    # Calculate derived metrics
    for site, s in site_data.items():
        if s["total_attempts"] > 0:
            s["success_rate"] = round(s["successful_attempts"] / s["total_attempts"] * 100, 1)
            s["avg_duration_ms"] = round(s["total_duration_ms"] / s["total_attempts"])
        else:
            s["success_rate"] = 0
            s["avg_duration_ms"] = 0
        if s["successful_attempts"] > 0:
            s["avg_jobs_per_success"] = round(s["total_jobs"] / s["successful_attempts"], 1)
        else:
            s["avg_jobs_per_success"] = 0

    # Compute search term performance
    term_data = {}
    for attempt in all_raw_attempts:
        term = attempt.get("search_term", "")
        if term not in term_data:
            term_data[term] = {
                "total_attempts": 0,
                "successful_attempts": 0,
                "total_jobs": 0,
                "sites_successful": [],
                "sites_failed": [],
            }
        t = term_data[term]
        t["total_attempts"] += 1
        if attempt.get("success"):
            t["successful_attempts"] += 1
            t["total_jobs"] += attempt.get("jobs_found", 0)
            if attempt.get("site") and attempt["site"] not in t["sites_successful"]:
                t["sites_successful"].append(attempt["site"])
        else:
            if attempt.get("site") and attempt["site"] not in t["sites_failed"]:
                t["sites_failed"].append(attempt["site"])

    for term, t in term_data.items():
        t["success_rate"] = round(t["successful_attempts"] / t["total_attempts"] * 100, 1) if t["total_attempts"] > 0 else 0

    # Timing distribution
    durations = [a.get("duration_ms", 0) for a in all_raw_attempts if a.get("success") and a.get("duration_ms", 0) > 0]
    if durations:
        durations.sort()
        timing_dist = {
            "count": len(durations),
            "min_ms": min(durations),
            "max_ms": max(durations),
            "avg_ms": round(sum(durations) / len(durations)),
            "p50_ms": durations[len(durations) // 2],
            "p90_ms": durations[int(len(durations) * 0.9)] if len(durations) >= 10 else durations[-1],
        }
    else:
        timing_dist = {"count": 0}

    # Error analysis
    errors = [a for a in all_raw_attempts if not a.get("success")]
    error_analysis = {"total_errors": len(errors)}
    if errors:
        by_type = {}
        by_site = {}
        error_messages = {}
        for e in errors:
            err_type = e.get("error_type", "unknown")
            by_type[err_type] = by_type.get(err_type, 0) + 1
            site = e.get("site", "unknown")
            if site not in by_site:
                by_site[site] = {"count": 0, "types": {}}
            by_site[site]["count"] += 1
            by_site[site]["types"][err_type] = by_site[site]["types"].get(err_type, 0) + 1
            if e.get("error_message"):
                msg = e["error_message"][:100]
                error_messages[msg] = error_messages.get(msg, 0) + 1
        error_analysis["by_type"] = by_type
        error_analysis["by_site"] = by_site
        error_analysis["top_error_messages"] = dict(sorted(error_messages.items(), key=lambda x: -x[1])[:10])

    # Cloudflare analysis
    cf_attempts = [a for a in all_raw_attempts if a.get("cloudflare_detected")]
    if cf_attempts:
        cf_analysis = {
            "total_encounters": len(cf_attempts),
            "solved": sum(1 for a in cf_attempts if a.get("cloudflare_solved") is True),
            "failed": sum(1 for a in cf_attempts if a.get("cloudflare_solved") is False),
            "solve_rate": round(sum(1 for a in cf_attempts if a.get("cloudflare_solved") is True) / len(cf_attempts) * 100, 1),
            "by_site": {},
        }
        for site in set(a.get("site") for a in cf_attempts):
            cf_analysis["by_site"][site] = {
                "encounters": sum(1 for a in cf_attempts if a.get("site") == site),
                "solved": sum(1 for a in cf_attempts if a.get("site") == site and a.get("cloudflare_solved") is True),
            }
    else:
        cf_analysis = {"total_encounters": 0}

    return {
        "metadata": {
            "merged_at": json.dumps(start_times[0] if start_times else None).strip('"'),
            "batches_processed": sorted(batches_processed) if batches_processed else None,
            "total_batches": len(analytics_files),
            "total_search_attempts": len(all_raw_attempts),
        },
        "site_summaries": site_data,
        "search_term_performance": term_data,
        "timing_distribution": timing_dist,
        "error_analysis": error_analysis,
        "cloudflare_analysis": cf_analysis,
        "raw_attempts": all_raw_attempts,
    }


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
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Skipping corrupted stats file {filepath}: {e}")
            continue

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


def upload_deep_analytics(analytics_data: dict, run_id: str = None):
    """Upload deep analytics to the dashboard API.

    Args:
        analytics_data: Merged analytics data from merge_deep_analytics()
        run_id: Optional run ID to associate with (uses metadata.run_id if not provided)
    """
    dashboard_url = os.environ.get("DASHBOARD_URL")
    api_key = os.environ.get("DASHBOARD_API_KEY")

    if not dashboard_url or not api_key:
        print("Dashboard credentials not set - skipping deep analytics upload")
        return

    url = f"{dashboard_url.rstrip('/')}/api/scraper/analytics"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Use provided run_id or extract from metadata
    target_run_id = run_id or analytics_data.get("metadata", {}).get("run_id")

    # Prepare payload
    payload = {
        "run_id": target_run_id,
        "metadata": analytics_data.get("metadata", {}),
        "site_summaries": analytics_data.get("site_summaries", {}),
        "search_term_performance": analytics_data.get("search_term_performance", {}),
        "timing_distribution": analytics_data.get("timing_distribution", {}),
        "error_analysis": analytics_data.get("error_analysis", {}),
        "cloudflare_analysis": analytics_data.get("cloudflare_analysis", {}),
        "raw_attempts": analytics_data.get("raw_attempts", []),
    }

    print(f"\nUploading deep analytics to {url}")
    print(f"  Total search attempts: {len(payload.get('raw_attempts', []))}")

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        result = response.json()
        print(f"Deep analytics uploaded: {result.get('analytics_id', 'OK')}")
        return result
    else:
        print(f"Deep analytics upload failed: {response.status_code}")
        print(response.text)
        # Don't raise - analytics upload is not critical


def main():
    # Upload leads CSV
    try:
        csv_path = get_latest_csv()
        print(f"Found latest CSV: {csv_path}")
        upload_to_dashboard(csv_path)
    except FileNotFoundError:
        print("No CSV files found in output/ - scraper may have produced no results")
        print("Skipping leads upload (this is not a fatal error)")
    except Exception as e:
        print(f"CSV upload failed: {e}")
        print("Continuing with stats/errors upload...")

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

    # Merge and save deep analytics (for local diagnostics)
    analytics_files = get_deep_analytics_files()
    if analytics_files:
        print(f"\nFound {len(analytics_files)} deep analytics file(s)")
        merged_analytics = merge_deep_analytics(analytics_files)

        # Print deep analytics summary
        print("\n" + "=" * 50)
        print("DEEP ANALYTICS SUMMARY")
        print("=" * 50)
        print(f"Total search attempts: {merged_analytics['metadata']['total_search_attempts']}")

        print("\nPer-site breakdown:")
        for site_name, site_data in merged_analytics.get("site_summaries", {}).items():
            cf_info = ""
            if site_data.get("cloudflare_encounters", 0) > 0:
                cf_solved = site_data.get("cloudflare_solved", 0)
                cf_total = site_data["cloudflare_encounters"]
                cf_info = f" | CF: {cf_solved}/{cf_total} solved"
            print(f"  {site_name}:")
            print(f"    Attempts: {site_data['total_attempts']} ({site_data['success_rate']}% success)")
            print(f"    Jobs: {site_data['total_jobs']} total, {site_data['avg_jobs_per_success']} avg/success")
            print(f"    Timing: {site_data['avg_duration_ms']}ms avg{cf_info}")
            if site_data.get("errors_by_type"):
                print(f"    Errors: {site_data['errors_by_type']}")

        cf_analysis = merged_analytics.get("cloudflare_analysis", {})
        if cf_analysis.get("total_encounters", 0) > 0:
            print(f"\nCloudflare challenges: {cf_analysis['total_encounters']} encounters, {cf_analysis['solve_rate']}% solved")
            for site, cf_site in cf_analysis.get("by_site", {}).items():
                print(f"  {site}: {cf_site['solved']}/{cf_site['encounters']} solved")

        err_analysis = merged_analytics.get("error_analysis", {})
        if err_analysis.get("total_errors", 0) > 0:
            print(f"\nErrors: {err_analysis['total_errors']} total")
            if err_analysis.get("by_type"):
                print(f"  By type: {err_analysis['by_type']}")

        print("=" * 50)

        # Upload deep analytics to dashboard
        upload_deep_analytics(merged_analytics)

        # Save merged analytics to output
        from datetime import datetime
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        analytics_output = f"{output_dir}/deep_analytics_{timestamp}_merged.json"
        with open(analytics_output, 'w') as f:
            json.dump(merged_analytics, f, indent=2)
        print(f"\nSaved merged deep analytics to: {analytics_output}")
    else:
        print("\nNo deep analytics to merge")


if __name__ == "__main__":
    main()
