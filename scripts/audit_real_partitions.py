#!/usr/bin/env python3
"""Read-only first-week real-data classification to reusable partition manifest.

Inputs are the owner's *already public* GitHub archive. Does not collect data
from racing websites or copy raw racecards/results/odds into this public repo.
"""
import argparse
import collections
import hashlib
import json
import re
from datetime import date
from pathlib import Path

from scripts.audit_archive_pilot import SOURCES, csv_rows, read_archive, row_date
from scripts.partition_rules import assign_partition, canonical_class

START = date(2023, 1, 1)
END = date(2023, 1, 7)
SOURCE_NAMES = ("a1_a2", "a3", "s_f1")
RACE_ID = re.compile(r"^\d{16}$")


def week_rows(raw, path, start=START, end=END):
    output = {}
    for row in csv_rows(raw, path):
        rid = (row.get("race_id") or "").strip()
        if not RACE_ID.fullmatch(rid):
            raise ValueError(f"Invalid race ID in {path}: {rid!r}")
        day = row_date(row, rid)
        if not start <= day <= end:
            continue
        if rid in output:
            raise ValueError(f"Duplicate race ID {rid} in {path}")
        if row.get("race_date") and row["race_date"] != day.isoformat():
            raise ValueError(f"Race ID/date mismatch in {path}: {rid}")
        output[rid] = row
    return output


def evaluate_partitions(blobs, start=START, end=END):
    if start > end or (end - start).days > 13:
        raise ValueError("One pilot batch must be 1–14 days")
    rows = {name: week_rows(blobs[name], SOURCES[name], start, end) for name in SOURCES}
    calendar = rows["calendar_links"]
    archives = {}
    for name in SOURCE_NAMES:
        for rid, row in rows[name].items():
            if rid in archives:
                raise ValueError(f"Same race in two class archives: {rid}")
            archives[rid] = (name, row)

    counter = collections.Counter()
    per_day = {}
    manifest = []
    warnings = []
    missing_calendar_ids = sorted(set(archives) - set(calendar))
    if missing_calendar_ids:
        raise ValueError(f"{len(missing_calendar_ids)} class-archive races absent from calendar")

    for rid, cal in sorted(calendar.items(), key=lambda item: (row_date(item[1], item[0]), item[0])):
        day = row_date(cal, rid).isoformat()
        in_archive = rid in archives
        if in_archive:
            source, archived = archives[rid]
            grade = archived.get("meeting_grade") or archived.get("grade")
            if not grade:
                raise ValueError(f"Missing grade in historical entry archive: {rid}")
            partition_input = {
                "source": "kdreams", "source_race_id": rid, "race_date": day,
                "meeting_grade": grade,
                "race_type": archived.get("race_type") or cal.get("race_type") or "",
                "class_scope": archived.get("class_scope", "")
            }
        else:
            source = "calendar_only"
            partition_input = {
                "source": "kdreams", "source_race_id": rid, "race_date": day,
                "race_type": cal.get("race_type") or ""
            }
        expected_class = canonical_class({"race_type": cal.get("race_type", "")})
        decision = assign_partition(partition_input)
        if expected_class and decision["race_class"] != expected_class:
            raise ValueError(f"Calendar/class-archive conflict for {rid}: {expected_class} != {decision['race_class']}")
        if in_archive and decision["status"] != "included":
            raise ValueError(f"Class archive race was not assignable: {rid}, {decision}")
        label = decision["relative_path"] if decision["status"] == "included" else decision["status"]
        counter[label] += 1
        day_counts = per_day.setdefault(day, collections.Counter())
        day_counts[label] += 1
        if not in_archive and decision["status"] == "included":
            warnings.append(f"{rid} classified by verified event only; entry archive not joined")
        manifest.append({
            "race_id": rid, "race_date": day,
            "partition_status": decision["status"],
            "grade": decision["grade"], "race_class": decision["race_class"],
            "partition_key": decision["relative_path"],
            "race_record_available": in_archive,
            "provenance": source
        })

    stats = {
        "calendar_observed": len(calendar),
        "racecards_in_three_archives": len(archives),
        "matched_archived_races": sum(x["race_record_available"] for x in manifest),
        "included": sum(x["partition_status"] == "included" for x in manifest),
        "excluded_girls": sum(x["partition_status"] == "excluded" for x in manifest),
        "quarantined": sum(x["partition_status"] == "quarantine" for x in manifest),
        "classified_without_entry_archive": sum(x["partition_status"] == "included" and not x["race_record_available"] for x in manifest)
    }
    report = {
        "scope": {"start": start.isoformat(), "end": end.isoformat()},
        "status": "classified_not_training_ready" if not stats["quarantined"] else "requires_review",
        "stats": stats,
        "partition_counts": dict(sorted(counter.items())),
        "per_day": {day: dict(sorted(d.items())) for day, d in sorted(per_day.items())},
        "classification_without_entry_archive": warnings,
        "provenance": {
            name: {"path": SOURCES[name], "sha256": hashlib.sha256(blobs[name]).hexdigest()}
            for name in SOURCES
        },
        "limitations": [
            "The event calendar is observed KDreams links, not independently certified nationwide coverage.",
            "The three class archives provide some racecard metadata; the G3 races here were classified via a verified event registry, but their racecards have NOT been materialized.",
            "This manifest stores race IDs and storage partition decisions only; it does NOT contain actual training rows, rider data, results, odds, or payouts.",
            "Historical post-race data may be unavailable as valid pre-race snapshots.",
            "No new collection or upload to a durable private store has been performed."
        ]
    }
    return report, manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", default="out")
    p.add_argument("--expected-calendar", type=int, default=597)
    args = p.parse_args()
    blobs = {name: read_archive(path) for name, path in SOURCES.items()}
    report, manifest = evaluate_partitions(blobs)
    if report["stats"]["calendar_observed"] != args.expected_calendar:
        raise SystemExit("Census changed: review before trusting partition summary")
    if report["stats"]["excluded_girls"] != 38:
        raise SystemExit("Expected 38 girls races in historical pilot; review the labels")
    if report["stats"]["classified_without_entry_archive"] != 48:
        raise SystemExit("Expected 48 confirmed G3 races in historical pilot; review the registry")
    if report["stats"]["quarantined"] or report["status"] != "classified_not_training_ready":
        raise SystemExit("Unverified race classification exists; review before continuing")

    dest = Path(args.out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "partition_2023_01_01_07_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (dest / "partition_2023_01_01_07_manifest.jsonl").open("w", encoding="utf-8") as out:
        for record in manifest:
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps({"status": report["status"], "stats": report["stats"],
                      "partition_counts": report["partition_counts"]},
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
