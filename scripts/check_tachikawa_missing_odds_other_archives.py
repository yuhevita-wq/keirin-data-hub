#!/usr/bin/env python3
"""Read-only verification of two 2023 Tachikawa G3 odds gaps in other owned archives.

Read only existing, published repository records. Source raw odds are never
uploaded or printed. Encrypted CMS files are not assumed to contain any race.
"""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

OWNER_REPO = "yuhevita-wq/keirin-market-analysis-"
TARGET = {
    "2820230104010006": "2023-01-04 Tachikawa 6R",
    "2820230104040007": "2023-01-07 Tachikawa 7R",
}
SOURCES = {
    "annual_complete_odds": "data/odds_only/odds_2023.jsonl.gz",
    "grade_repair_summary": ("data/odds_universe_v1/grade_archive_repairs/"
                             "g3-all-2023-q1-non-girls/batch_b5a4bd79e66848/summary.json"),
    "grade_repair_failures": ("data/odds_universe_v1/grade_archive_repairs/"
                              "g3-all-2023-q1-non-girls/batch_b5a4bd79e66848/failures.csv"),
}
ANNUAL_SHA256 = "b46cc6399df97edffbecfe2d4f0ab22035a17da523f04feda20af3a9bda7db7b"
LIMIT = 35_000_000


def read(path):
    url = f"https://raw.githubusercontent.com/{OWNER_REPO}/main/{path}"
    req = Request(url, headers={"User-Agent": "keirin-data-hub-existing-archive-audit/1.0"})
    with urlopen(req, timeout=75) as response:
        body = response.read(LIMIT + 1)
    if len(body) > LIMIT:
        raise ValueError("source exceeds safe download limit: " + path)
    return body


def inspect(blobs):
    annual = blobs["annual_complete_odds"]
    digest = hashlib.sha256(annual).hexdigest()
    if digest != ANNUAL_SHA256:
        raise ValueError("annual complete odds export SHA256 mismatch")
    rows = 0
    found = {rid: [] for rid in TARGET}
    distinct = set()
    with gzip.open(io.BytesIO(annual), mode="rt", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            obj = json.loads(line)
            rows += 1
            rid = str(obj.get("race_id", "")).strip()
            if rid in distinct:
                raise ValueError("duplicate race_id in annual complete-odds file: " + rid)
            distinct.add(rid)
            if rid in found:
                found[rid].append({
                    "race_type": obj.get("race_type"),
                    "odds_value_type": type(obj.get("odds")).__name__,
                    "odds_keys": sorted(obj["odds"]) if isinstance(obj.get("odds"), dict) else []
                })
    repair = json.loads(blobs["grade_repair_summary"].decode("utf-8-sig"))
    reader = csv.DictReader(io.StringIO(blobs["grade_repair_failures"].decode("utf-8-sig")))
    failures = {r["race_id"]: r.get("error", "") for r in reader if r["race_id"] in TARGET}
    results = {}
    for rid, description in TARGET.items():
        results[rid] = {
            "race": description,
            "in_annual_complete_final_odds_export": len(found[rid]) == 1,
            "annual_export_record_count": len(found[rid]),
            "annual_export_record_metadata_only": found[rid],
            "in_grade_archive_repair_failed_ids": rid in set(repair.get("failed_race_ids", [])),
            "grade_archive_repair_failure_message": failures.get(rid),
            "in_grade_archive_repair_complete_ids": rid in set(repair.get("complete_race_ids", [])),
        }
    return {
        "annual_complete_final_odds": {
            "source_path": SOURCES["annual_complete_odds"],
            "sha256_verified": digest,
            "race_records": rows,
            "unique_races": len(distinct),
            "phase": "final",
            "ticket_types": ["3連単", "3連複"],
        },
        "grade_repair": {
            "source_path": SOURCES["grade_repair_summary"],
            "attempted_races": repair.get("attempted"),
            "complete_races": repair.get("complete"),
            "failed_races": repair.get("failed"),
        },
        "targets": results,
        "limits": [
            "A negative annual export lookup proves noninclusion in that exact annual complete-only export, not absence from all source data.",
            "The two encrypted CMS ciphertext files visible on these days were NOT decrypted; file existence does not prove inclusion of target race IDs.",
            "No genuine pre-race (T-minus-15-minute) snapshots have been verified.",
            "No re-scraping, odds imputation or model training was performed."
        ]
    }


def main():
    raw = {name: read(path) for name, path in SOURCES.items()}
    report = inspect(raw)
    path = Path("out/tachikawa_two_odds_cross_archive_audit.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "annual_archive_count": report["annual_complete_final_odds"]["race_records"],
        "annual_sha256_verified": report["annual_complete_final_odds"]["sha256_verified"],
        "grade_repair": report["grade_repair"],
        "targets": report["targets"]
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
