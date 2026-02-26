"""
Cold Lead Discovery State Manager

Tracks what SAGE has tried and submitted during cold lead discovery sessions,
so work is never repeated across sessions.

State file: data/cold_lead_state.json (gitignored)

Usage:
    from cold_lead_state import ColdLeadState
    state = ColdLeadState()
    if not state.is_submitted("sunpowerco.com"):
        # ... call API ...
        state.record_submission("sunpowerco.com", "SunPower Co", "sl-abc123")
    state.save()

CLI:
    python cold_lead_state.py summary       # print current state summary
    python cold_lead_state.py queries       # list all tried queries
    python cold_lead_state.py submitted     # list all submitted domains
    python cold_lead_state.py reset-source <source>  # clear a source's progress
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path(__file__).parent / "data" / "cold_lead_state.json"
UTC = timezone.utc


class ColdLeadState:
    def __init__(self, path: Path = STATE_FILE):
        self.path = path
        self._data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "version": 1,
            "companies_submitted": {},
            "queries_tried": {},
            "sources_progress": {},
        }

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Companies ────────────────────────────────────────────────────────────

    def is_submitted(self, domain: str) -> bool:
        """Return True if this domain has already been submitted as a cold lead."""
        domain = domain.lower().strip().lstrip("www.")
        return domain in self._data["companies_submitted"]

    def record_submission(
        self,
        domain: str,
        company: str,
        lead_id: str,
        source_url: str = None,
    ):
        """Record a successfully submitted cold lead."""
        domain = domain.lower().strip().lstrip("www.")
        self._data["companies_submitted"][domain] = {
            "company": company,
            "lead_id": lead_id,
            "submitted_at": datetime.now(UTC).isoformat(),
            **({"source_url": source_url} if source_url else {}),
        }

    # ── Queries ──────────────────────────────────────────────────────────────

    def is_query_tried(self, query: str) -> bool:
        """Return True if this exact search query has been tried before."""
        return query.strip() in self._data["queries_tried"]

    def record_query(self, query: str, companies_found: int = 0):
        """Record that a search query was executed."""
        self._data["queries_tried"][query.strip()] = {
            "tried_at": datetime.now(UTC).isoformat(),
            "companies_found": companies_found,
        }

    def get_tried_queries(self) -> list[str]:
        """Return all previously tried queries."""
        return list(self._data["queries_tried"].keys())

    # ── Sources ───────────────────────────────────────────────────────────────

    def update_source_progress(self, source: str, progress: dict):
        """
        Record progress on a structured source (e.g. a paginated directory).

        progress is a free-form dict — whatever is meaningful for that source.
        Example: {"status": "in_progress", "last_page": 4, "companies_submitted": 23}
        """
        existing = self._data["sources_progress"].get(source, {})
        existing.update(progress)
        existing["last_updated"] = datetime.now(UTC).isoformat()
        self._data["sources_progress"][source] = existing

    def get_source_progress(self, source: str) -> dict:
        """Return saved progress for a source, or empty dict if not started."""
        return self._data["sources_progress"].get(source, {})

    # ── Summary ───────────────────────────────────────────────────────────────

    def get_summary(self) -> dict:
        """Return a compact summary suitable for SAGE to read at session start."""
        submitted = self._data["companies_submitted"]
        queries = self._data["queries_tried"]
        sources = self._data["sources_progress"]

        recent_submissions = sorted(
            submitted.items(),
            key=lambda kv: kv[1].get("submitted_at", ""),
            reverse=True,
        )[:10]

        return {
            "total_submitted": len(submitted),
            "total_queries_tried": len(queries),
            "sources": {
                name: {
                    "status": prog.get("status", "unknown"),
                    "companies_submitted": prog.get("companies_submitted", "?"),
                }
                for name, prog in sources.items()
            },
            "recent_submissions": [
                {"domain": d, "company": v["company"], "submitted_at": v["submitted_at"]}
                for d, v in recent_submissions
            ],
            "queries_tried_count_by_day": _count_by_day(
                [v["tried_at"] for v in queries.values()]
            ),
        }


def _count_by_day(timestamps: list[str]) -> dict:
    counts = {}
    for ts in timestamps:
        day = ts[:10]
        counts[day] = counts.get(day, 0) + 1
    return dict(sorted(counts.items(), reverse=True)[:7])


# ── CLI ───────────────────────────────────────────────────────────────────────

def _print_summary(state: ColdLeadState):
    s = state.get_summary()
    print(f"\n=== Cold Lead State Summary ===")
    print(f"Submitted: {s['total_submitted']} companies")
    print(f"Queries tried: {s['total_queries_tried']}")

    if s["sources"]:
        print("\nSources:")
        for name, prog in s["sources"].items():
            print(f"  {name}: {prog['status']} ({prog['companies_submitted']} submitted)")

    if s["recent_submissions"]:
        print("\nRecent submissions (last 10):")
        for item in s["recent_submissions"]:
            print(f"  {item['domain']} — {item['company']} @ {item['submitted_at'][:10]}")

    if s["queries_tried_count_by_day"]:
        print("\nQueries tried by day:")
        for day, count in s["queries_tried_count_by_day"].items():
            print(f"  {day}: {count}")
    print()


def _print_queries(state: ColdLeadState):
    queries = state._data["queries_tried"]
    if not queries:
        print("No queries tried yet.")
        return
    print(f"\n=== {len(queries)} Queries Tried ===")
    for query, meta in sorted(queries.items(), key=lambda kv: kv[1]["tried_at"], reverse=True):
        found = meta.get("companies_found", "?")
        print(f"  [{meta['tried_at'][:10]}] ({found} found) {query}")
    print()


def _print_submitted(state: ColdLeadState):
    submitted = state._data["companies_submitted"]
    if not submitted:
        print("No companies submitted yet.")
        return
    print(f"\n=== {len(submitted)} Companies Submitted ===")
    for domain, meta in sorted(submitted.items(), key=lambda kv: kv[1]["submitted_at"], reverse=True):
        print(f"  {domain} — {meta['company']} [{meta['lead_id']}] @ {meta['submitted_at'][:10]}")
    print()


def main():
    state = ColdLeadState()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"

    if cmd == "summary":
        _print_summary(state)
    elif cmd == "queries":
        _print_queries(state)
    elif cmd == "submitted":
        _print_submitted(state)
    elif cmd == "reset-source":
        if len(sys.argv) < 3:
            print("Usage: cold_lead_state.py reset-source <source_name>")
            sys.exit(1)
        source = sys.argv[2]
        if source in state._data["sources_progress"]:
            del state._data["sources_progress"][source]
            state.save()
            print(f"Cleared progress for source: {source}")
        else:
            print(f"Source not found: {source}")
    else:
        print(f"Unknown command: {cmd}. Use: summary | queries | submitted | reset-source <name>")
        sys.exit(1)


if __name__ == "__main__":
    main()
