#!/usr/bin/env python3
"""Classify the 86 calendar-only races in the 2023-01-01..07 archive pilot.

Read-only GitHub archive access. Does not scrape an external racing site.
Classifications rely on actual calendar labels; unknowns stay unknown.
"""
import collections
import json
import re
from datetime import date
from pathlib import Path

from scripts.audit_archive_pilot import SOURCES, read_archive, csv_rows, row_date

START, END = date(2023, 1, 1), date(2023, 1, 7)
TEXT_FIELDS = (
    "race_type", "race_title", "race_name", "race_label", "race_kind",
    "class_scope", "meeting_grade", "grade", "event_grade", "event_name"
)
GIRLS_PATTERN = re.compile(r"ガールズ|女子|Ｌ級|L級|L1(?:\W|$)", flags=re.IGNORECASE)


def get_label(row):
    return " ".join(str(row.get(k) or "").strip() for k in TEXT_FIELDS if row.get(k))


def classify(row):
    label = get_label(row)
    if GIRLS_PATTERN.search(label):
        return "girls"
    if re.search(r"(?:G3|Ｇ３|GIII|GⅢ|記念競輪)", label, flags=re.IGNORECASE):
        return "explicit_g3"
    if re.search(r"(?:G2|Ｇ２|GII|GⅡ)", label, flags=re.IGNORECASE):
        return "explicit_g2"
    if re.search(r"(?:G1|Ｇ１|GI|GⅠ)", label, flags=re.IGNORECASE):
        return "explicit_g1"
    if "Ｓ級" in label or "S級" in label:
        return "s_class_grade_unverified"
    if "Ａ級" in label or "A級" in label or "チャレンジ" in label:
        return "a_class_unmatched"
    return "unknown"


def first(row, keys):
    for k in keys:
        if row.get(k):
            return str(row[k])
    return None


def make_report():
    rows = {name: csv_rows(read_archive(path), path) for name, path in SOURCES.items()}
    by_source = {name: set() for name in SOURCES if name != "calendar_links"}
    cal = {}
    for name, data in rows.items():
        for row in data:
            rid = str(row.get("race_id") or "").strip()
            if not re.fullmatch(r"\d{16}", rid):
                continue
            try:
                rd = row_date(row, rid)
            except (ValueError, TypeError):
                continue
            if not START <= rd <= END:
                continue
            if name == "calendar_links":
                if rid in cal:
                    raise ValueError("duplicate calendar race ID: " + rid)
                cal[rid] = row
            else:
                by_source[name].add(rid)
    present = set().union(*by_source.values())
    unmatched = {rid: row for rid, row in cal.items() if rid not in present}
    counter = collections.Counter()
    by_race_type = collections.Counter()
    by_grade = collections.Counter()
    by_track = collections.Counter()
    items = []
    for rid, row in sorted(unmatched.items()):
        label = get_label(row)
        cat = classify(row)
        counter[cat] += 1
        race_type = first(row, ["race_type", "race_title", "race_name", "race_label", "race_kind"]) or "(missing)"
        grade = first(row, ["meeting_grade", "grade", "event_grade"]) or "(missing)"
        venue = first(row, ["track", "venue", "venue_name", "stadium", "jyo"]) or "(missing)"
        by_race_type[race_type] += 1
        by_grade[grade] += 1
        by_track[venue] += 1
        items.append({"race_id": rid, "date": row_date(row, rid).isoformat(),
                      "race_type": race_type, "grade": grade, "venue": venue,
                      "category": cat, "original_label": label})
    if len(unmatched) != 86:
        raise ValueError(f"expected pilot 86, observed {len(unmatched)}: source changed; review input")
    return {
        "scope": [START.isoformat(), END.isoformat()],
        "reference_counts": {"calendar": len(cal), "matched_in_3_archives": len(present & set(cal)),
                             "calendar_only": len(unmatched)},
        "classification": dict(sorted(counter.items())),
        "race_type_counts": dict(sorted(by_race_type.items())),
        "grade_field_counts": dict(sorted(by_grade.items())),
        "venue_counts": dict(sorted(by_track.items())),
        "calendar_header_fields": list(rows["calendar_links"][0]) if rows["calendar_links"] else [],
        "limits": [
            "All labels come from a historical KDreams calendar-link archive.",
            "G3 is confirmed only when explicit grade or racing event label is available; S-class alone does NOT prove G3.",
            "The three compared entry archives omit many categories, so calendar-only is not necessarily missing data.",
            "The calendar is an observed-link census, not certified nationwide completeness."
        ],
        "calendar_only_races": items
    }


def main():
    report = make_report()
    out = Path("out/2023-01-01_to_07_gap_classification.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {k: report[k] for k in ("reference_counts", "classification", "race_type_counts",
                                       "grade_field_counts", "venue_counts", "calendar_header_fields")}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
