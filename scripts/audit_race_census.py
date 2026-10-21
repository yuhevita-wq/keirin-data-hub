#!/usr/bin/env python3
"""Offline audit of race-discovery lists. Does not collect or certify source rights."""
import argparse
import json
from datetime import date
from pathlib import Path


def race_key(row, day):
    if not isinstance(row, dict):
        raise ValueError("race row must be an object")
    if row.get("race_date") != day:
        raise ValueError("race_date must match the audited date")
    venue = row.get("venue_key")
    number = row.get("race_no")
    if not isinstance(venue, str) or not venue.strip() or venue != venue.strip():
        raise ValueError("venue_key must be a canonical nonempty string")
    if type(number) is not int or not 1 <= number <= 20:
        raise ValueError("race_no must be an integer 1..20")
    return f"{day}/{venue}/{number:02d}"


def audit_discovery(payload):
    """Compare each provider with an optional independently verified race calendar.

    Absence of an independent nationwide calendar can never yield a nationwide
    completeness claim. A discovered race has no guarantee of complete fields.
    """
    day = payload["date"]
    if date.fromisoformat(day).isoformat() != day:
        raise ValueError("date must be YYYY-MM-DD")
    expected_rows = payload.get("calendar_races", [])
    sources = payload.get("sources", {})
    if not isinstance(expected_rows, list) or not isinstance(sources, dict):
        raise ValueError("calendar_races must be a list, sources an object")
    calendar = set()
    problems = []
    for row in expected_rows:
        k = race_key(row, day)
        if k in calendar:
            problems.append("duplicate calendar record: " + k)
        calendar.add(k)
    observed = {}
    union = set()
    for source, rows in sorted(sources.items()):
        if not source or not isinstance(rows, list):
            raise ValueError("source name must be nonempty and rows must be a list")
        keys, by_id = set(), {}
        for row in rows:
            k = race_key(row, day)
            source_race_id = row.get("source_race_id")
            if not isinstance(source_race_id, str) or not source_race_id.strip():
                raise ValueError("source_race_id is required for " + source)
            if k in keys:
                problems.append("duplicate source race key: " + source + " " + k)
            if source_race_id in by_id and by_id[source_race_id] != k:
                problems.append("one source ID maps to two races: " + source + " " + source_race_id)
            by_id[source_race_id] = k
            keys.add(k)
        observed[source] = keys
        union.update(keys)

    verified = bool(payload.get("calendar_verified") is True
                    and payload.get("calendar_scope") == "all_mens_races"
                    and isinstance(payload.get("calendar_source"), str)
                    and payload["calendar_source"].strip())
    missing = sorted(calendar - union) if verified else []
    unexpected = sorted(union - calendar) if verified else []
    source_gaps = {}
    for source, rows in observed.items():
        target = calendar if verified else union
        source_gaps[source] = sorted(target - rows)
    status = ("review_needed" if problems or missing or unexpected
              else "calendar_covered_by_union" if verified
              else "nationwide_coverage_unverified")
    return {
        "date": day,
        "status": status,
        "calendar_verified_by_input": verified,
        "calendar_source": payload.get("calendar_source"),
        "calendar_races": len(calendar),
        "unique_observed_races": len(union),
        "source_race_counts": {k: len(v) for k, v in observed.items()},
        "missing_from_calendar_union": missing,
        "observed_not_in_calendar": unexpected,
        "missing_by_source": source_gaps,
        "errors": problems,
        "limitation": "Discovery audit only. Source permission, nationwide calendar "
                      "accuracy, historical availability, entrants, results, odds, "
                      "and payout completeness are NOT proven."
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, help="race discovery JSON")
    p.add_argument("--output", required=True, help="audit JSON")
    args = p.parse_args()
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = audit_discovery(source)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if report["status"] == "review_needed":
        raise SystemExit("Discovery discrepancies require review")


if __name__ == "__main__":
    main()
