#!/usr/bin/env python3
"""Read-only 7-day race-ID audit of the user's existing public GitHub archive.

Does not scrape racing sites, certify nationwide coverage, or store raw archives.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

ARCHIVE_REPO = "yuhevita-wq/keirin-market-analysis-"
SOURCES = {
    "calendar_links": "data/nationwide_calendar/2023-01-01__2023-01-31/race_index.csv.gz",
    "a1_a2": "data/a_class_12/2023_01_02/races.csv",
    "a3": "data/a3_challenge/2023_01_02/races.csv",
    "s_f1": "data/2023/s_class_f1_all_parts/2023_q1/races.csv",
}
MAX_BYTES = 3_000_000
ID_RE = re.compile(r"^\d{16}$")


def read_archive(path):
    url = f"https://raw.githubusercontent.com/{ARCHIVE_REPO}/main/{path}"
    request = Request(url, headers={"User-Agent": "keirin-data-hub-readonly-audit/1.0"})
    with urlopen(request, timeout=25) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError(f"oversized source: {path}")
    return raw


def csv_rows(raw, path):
    decoded = gzip.decompress(raw) if path.endswith(".gz") else raw
    reader = csv.DictReader(io.StringIO(decoded.decode("utf-8-sig")))
    if not reader.fieldnames or "race_id" not in reader.fieldnames:
        raise ValueError(f"missing race_id column in {path}: {reader.fieldnames}")
    return list(reader)


def row_date(row, rid):
    for key in ("race_date", "date", "day"):
        value = (row.get(key) or "").strip()
        if value:
            return date.fromisoformat(value if "-" in value else f"{value[:4]}-{value[4:6]}-{value[6:8]}")
    # KDreams ID: two-digit track code + YYYYMMDD + additional digits.
    return date.fromisoformat(f"{rid[2:6]}-{rid[6:8]}-{rid[8:10]}")


def is_girls(row):
    label = str(row.get("race_type") or row.get("race_title") or row.get("race_name") or "")
    return any(word in label for word in ("ガールズ", "Ｌ級", "L級", "女子"))


def evaluate(blobs, start=date(2023, 1, 1), end=date(2023, 1, 7)):
    if start > end or (end - start).days > 13:
        raise ValueError("select 1–14 days")
    days = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
    records = {day: {name: {} for name in SOURCES} for day in days}
    provenance = {}
    errors = []
    for name, path in SOURCES.items():
        raw = blobs[name]
        rows = csv_rows(raw, path)
        provenance[name] = {
            "source_repository": ARCHIVE_REPO, "path": path,
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "total_rows_in_source_file": len(rows)
        }
        for row in rows:
            rid = (row.get("race_id") or "").strip()
            if not ID_RE.fullmatch(rid):
                errors.append(f"{name}: invalid race_id {rid[:24]}")
                continue
            try:
                day = row_date(row, rid).isoformat()
            except (ValueError, TypeError):
                errors.append(f"{name}: invalid date for {rid}")
                continue
            if day not in records:
                continue
            if rid in records[day][name]:
                errors.append(f"{name}: duplicate record {rid}")
            records[day][name][rid] = row

    reports = []
    summary = Counter()
    for day in days:
        current = records[day]
        calendar_ids = set(current["calendar_links"])
        named_classes = [set(current[n]) for n in ("a1_a2", "a3", "s_f1")]
        three_classes = set().union(*named_classes)
        cross_class = (named_classes[0] & named_classes[1]) | (named_classes[0] & named_classes[2]) | (named_classes[1] & named_classes[2])
        entry = {
            "date": day,
            "calendar_observed_link_count": len(calendar_ids),
            "calendar_explicit_girls_labels": sum(is_girls(r) for r in current["calendar_links"].values()),
            "a1_a2_races": len(current["a1_a2"]),
            "a3_races": len(current["a3"]),
            "s_f1_races": len(current["s_f1"]),
            "unique_races_in_three_class_archives": len(three_classes),
            "matched_in_calendar_links": len(calendar_ids & three_classes),
            "three_class_archives_not_in_calendar": len(three_classes - calendar_ids),
            "calendar_not_in_these_three_archives": len(calendar_ids - three_classes),
            "cross_class_id_overlap_count": len(cross_class),
        }
        reports.append(entry)
        for key, value in entry.items():
            if isinstance(value, int):
                summary[key] += value
    if not any(r["calendar_observed_link_count"] for r in reports):
        errors.append("calendar contains zero race links for requested days")
    if not any(r["unique_races_in_three_class_archives"] for r in reports):
        errors.append("three entry archives contain zero races for requested days")
    return {
        "scope": {"start": start.isoformat(), "end": end.isoformat(), "days": len(days)},
        "status": ("needs_review" if errors or summary["three_class_archives_not_in_calendar"] or summary["cross_class_id_overlap_count"]
                   else "observed_archive_id_audit_only"),
        "aggregate": dict(summary), "daily": reports, "sources": provenance,
        "errors": errors[:40],
        "limitations": [
            "Historical archive ID comparison only: not new source collection.",
            "Calendar consists of KDreams observed links, not an independent nationwide certified universe.",
            "Only A1/A2, A3, and S-class F1 archives are compared; other grades/classes are out of scope.",
            "Calendar-minus-archive counts are NOT proven missing races; other classes/grades or girls may explain them.",
            "Race-ID matching does not validate entrants, results, payouts, odds, or point-in-time availability."
        ]
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2023-01-01")
    p.add_argument("--end", default="2023-01-07")
    p.add_argument("--out", default="out/historical_archive_audit.json")
    args = p.parse_args()
    blobs = {name: read_archive(path) for name, path in SOURCES.items()}
    report = evaluate(blobs, date.fromisoformat(args.start), date.fromisoformat(args.end))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("scope", "status", "aggregate", "errors")}, ensure_ascii=False))
    if report["status"] == "needs_review":
        print("NOTICE: discrepancies are recorded for review, not silently discarded.")


if __name__ == "__main__":
    main()
