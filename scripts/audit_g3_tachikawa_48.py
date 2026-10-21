#!/usr/bin/env python3
"""Audit the 48 specific Tachikawa G3 races (Jan 4–7 2023) in archived Q1 ZIP.

Read-only GitHub archive; output only aggregate audit and anomalous race IDs.
Does NOT turn historical final odds into pre-race snapshots.
"""
import collections
import csv
import io
import json
import zipfile
from pathlib import Path

from scripts.inspect_g3_zip import download
from scripts.audit_archive_pilot import read_archive, csv_rows, SOURCES

PREFIX = "archive/g3-all-2023-q1-non-girls/"
DAYS = {"2023-01-04", "2023-01-05", "2023-01-06", "2023-01-07"}
FILES = {
    "races": "races.csv",
    "entries": "entries.csv",
    "results": "results.csv",
    "payouts": "payouts.csv",
    "trifecta_odds": "trifecta_final_odds.csv",
    "trio_odds": "trio_final_odds.csv",
}


def first_week_ids():
    calendar = csv_rows(read_archive(SOURCES["calendar_links"]), SOURCES["calendar_links"])
    target = {}
    for r in calendar:
        rid = r.get("race_id", "").strip()
        if r.get("race_date") in DAYS and rid[:2] == "28" and "S級" in str(r.get("race_type", "")):
            if rid in target:
                raise ValueError("duplicate historical calendar G3 race ID: " + rid)
            target[rid] = r
    if len(target) != 48:
        raise ValueError(f"Expected 48 Tachikawa G3 races in calendar, got {len(target)}")
    return target


def subset(z, file_name, target_ids):
    with z.open(PREFIX + file_name) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
        rows = collections.defaultdict(list)
        for row in reader:
            if row.get("race_id") in target_ids:
                rows[row["race_id"]].append(row)
    return rows


def nonempty(r, name):
    return str(r.get(name) or "").strip() != ""


def audit():
    expected = first_week_ids()
    with zipfile.ZipFile(io.BytesIO(download())) as z:
        if z.testzip() is not None:
            raise ValueError("G3 ZIP CRC check failed")
        data = {name: subset(z, fn, expected) for name, fn in FILES.items()}
        odds_failures = subset(z, "odds_failures.csv", expected)

    individual = []
    totals = collections.Counter()
    payouts_by_bet = collections.Counter()
    odds_phase = collections.Counter()
    odds_status = collections.Counter()
    for rid, cal in sorted(expected.items()):
        race_list = data["races"].get(rid, [])
        entries = data["entries"].get(rid, [])
        results = data["results"].get(rid, [])
        payouts = data["payouts"].get(rid, [])
        tri = data["trifecta_odds"].get(rid, [])
        trio = data["trio_odds"].get(rid, [])
        problems = []
        if len(race_list) != 1:
            problems.append("race_header_count_not_one")
            row = {}
        else:
            row = race_list[0]
        if row.get("meeting_grade") != "G3":
            problems.append("grade_not_G3")
        if row.get("race_date") != cal.get("race_date"):
            problems.append("archive_calendar_date_mismatch")
        target = int(row["entry_count"]) if str(row.get("entry_count") or "").isdigit() else None
        if not target:
            problems.append("invalid_expected_entrants")
        if target is not None and len(entries) != target:
            problems.append("entry_count_mismatch")
        if target is not None and len(results) != target:
            problems.append("result_count_mismatch")
        car_e = [e.get("car_no") for e in entries]
        car_r = [e.get("car_no") for e in results]
        if len(car_e) != len(set(car_e)) or len(car_r) != len(set(car_r)):
            problems.append("duplicate_car_number")
        if set(car_e) != set(car_r):
            problems.append("entrant_result_car_mismatch")
        if any(not nonempty(e, "player_name") for e in entries):
            problems.append("empty_entry_player_name")
        if any(not nonempty(r, "finish_text") and not nonempty(r, "finish_position") for r in results):
            problems.append("missing_finish_order_and_status")
        if not payouts:
            problems.append("missing_payouts")
        if not row.get("predicted_line_formation") or row.get("line_status") != "published":
            problems.append("line_not_published")
        if not tri:
            problems.append("no_trifecta_quote_rows")
        if not trio:
            problems.append("no_trio_quote_rows")
        if any(o.get("odds_phase") != "final" for o in tri + trio):
            problems.append("nonfinal_odds_mixed_into_archive")
        if target:
            expected_tri = target * (target-1) * (target-2)
            expected_trio = target * (target-1) * (target-2) // 6
            if len(tri) != expected_tri:
                problems.append("trifecta_quote_count_not_full_theoretical")
            if len(trio) != expected_trio:
                problems.append("trio_quote_count_not_full_theoretical")
        types = sorted(set(p.get("ticket_type", "") for p in payouts))
        for kind in types:
            payouts_by_bet[kind] += 1
        for o in tri + trio:
            odds_phase[o.get("odds_phase") or "(empty)"] += 1
            odds_status[o.get("odds_status") or "(empty)"] += 1
        status = "complete_on_basic_field_checks" if not problems else "requires_field_review"
        if problems:
            totals["races_with_problems"] += 1
        else:
            totals["races_basic_fields_complete"] += 1
        totals["races"] += 1
        for n, arr in [("races_rows", race_list), ("entries_rows", entries), ("results_rows", results),
                       ("payouts_rows", payouts), ("trifecta_rows", tri), ("trio_rows", trio)]:
            totals[n] += len(arr)
        individual.append({"race_id": rid, "race_date": cal["race_date"], "entry_count": target,
                           "entries": len(entries), "results": len(results),
                           "payouts": len(payouts), "ticket_types": types,
                           "trifecta_final_quote_rows": len(tri), "trio_final_quote_rows": len(trio),
                           "status": status, "problems": problems})

    summary = {
        "scope": {"dates": sorted(DAYS), "track": "立川", "grade": "G3",
                  "calendar_expected_races": len(expected)},
        "totals": dict(totals),
        "payout_market_coverage_races": dict(sorted(payouts_by_bet.items())),
        "odds_phase_quote_counts": dict(sorted(odds_phase.items())),
        "odds_status_quote_counts": dict(sorted(odds_status.items())),
        "per_day": {
            day: {"races": sum(r["race_date"] == day for r in individual),
                  "basic_fields_complete": sum(r["race_date"] == day and
                        r["status"] == "complete_on_basic_field_checks" for r in individual)}
            for day in sorted(DAYS)
        },
        "anomalies": [r for r in individual if r["problems"]],
        "archive_odds_failure_logs": [
            {"race_id": rid, "reason": (row.get("error") or "")[:350]}
            for rid, records in odds_failures.items() for row in records
        ],
        "limitations": [
            "Only structural and basic per-race row checks: not an expert reconstruction of all finishing statuses.",
            "Stored final odds are post-event/final; never assume they are 15-minute-before-close quotes.",
            "Observed KDreams calendar is not an independently certified nationwide race census.",
            "Player statistics captured retrospectively may carry training-feature leakage; independently validate feature vintage.",
            "Odds market files are trifecta and trio only, not proof of completeness for the other five ticket types.",
            "No raw race dataset is uploaded to this public code repository."
        ]
    }
    return summary


def main():
    report = audit()
    dst = Path("out/g3_tachikawa_2023_48_audit.json")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("scope", "totals", "payout_market_coverage_races",
                                             "odds_phase_quote_counts", "odds_status_quote_counts",
                                             "per_day", "anomalies", "archive_odds_failure_logs")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
