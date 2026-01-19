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


def main():
    # Upload leads CSV
    try:
        csv_path = get_latest_csv()
        print(f"Found latest CSV: {csv_path}")
        upload_to_dashboard(csv_path)
    except FileNotFoundError:
        print("No CSV files found in output/ - scraper may have produced no results")
        print("Skipping leads upload (this is not a fatal error)")

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
