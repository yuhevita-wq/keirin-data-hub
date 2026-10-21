#!/usr/bin/env python3
"""Grade and race-class partitions for a *single* common training data hub.

This module only generates paths and metadata; it never fetches or uploads data.
Unverified grade/class inputs are quarantined rather than guessed.
"""
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

GRADES = frozenset({"GP", "G1", "G2", "G3", "F1", "F2"})
CLASSES = frozenset({"S", "A1_A2", "A3", "GIRLS"})
KNOWN_EVENTS = Path(__file__).resolve().parent.parent / "config" / "verified_events.json"


def canonical_grade(value):
    """Normalize written event grades without confusing the letter S with G3."""
    if value is None or not str(value).strip():
        return None
    raw = str(value).upper().translate(str.maketrans("ＧＦＰ１２３", "GFP123"))
    raw = re.sub(r"[\s\-_・]", "", raw)
    mapping = {
        "GⅠ": "G1", "GI": "G1", "G1": "G1",
        "GⅡ": "G2", "GII": "G2", "G2": "G2",
        "GⅢ": "G3", "GIII": "G3", "G3": "G3",
        "F1": "F1", "FI": "F1",
        "F2": "F2", "FII": "F2",
        "GP": "GP", "グランプリ": "GP"
    }
    return mapping.get(raw)


def canonical_class(row):
    text = " ".join(str(row.get(k) or "") for k in ("race_type", "class_scope", "race_name", "race_label"))
    text = text.translate(str.maketrans("ＳＡＬ１２３", "SAL123")).upper()
    if re.search(r"ガールズ|女子|L級|L1", text):
        return "GIRLS"
    if re.search(r"チャレンジ|A3", text):
        return "A3"
    if "S級" in text or re.search(r"\bS[12]\b", text):
        return "S"
    if "A級" in text or "A1/A2" in text or "A1A2" in text:
        return "A1_A2"
    return None


def event_registry():
    obj = json.loads(KNOWN_EVENTS.read_text(encoding="utf-8"))
    if obj.get("schema_version") != 1 or not isinstance(obj.get("events"), list):
        raise ValueError("invalid verified event registry")
    return obj["events"]


def registry_grade(row, registry):
    if row.get("source") != "kdreams":
        return None
    rid = str(row.get("source_race_id") or row.get("race_id") or "")
    if not re.fullmatch(r"\d{16}", rid):
        return None
    day = row["race_date"]
    matched = set()
    for event in registry:
        if not all(event.get(k) for k in ("source", "start_date", "end_date", "kdreams_track_code", "grade", "verification_url")):
            raise ValueError("verified event is missing required provenance")
        if (event["source"] == "kdreams" and event["start_date"] <= day <= event["end_date"]
                and rid[:2] == event["kdreams_track_code"]):
            grade = canonical_grade(event["grade"])
            if not grade:
                raise ValueError("invalid registry grade")
            matched.add(grade)
    if len(matched) > 1:
        raise ValueError("ambiguous event grade")
    return next(iter(matched)) if matched else None


def assign_partition(row, registry=None):
    """Return structured partition decision; never treat unknown as complete."""
    try:
        day = date.fromisoformat(str(row["race_date"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("race_date must be YYYY-MM-DD") from exc
    if str(row["race_date"]) != day.isoformat():
        raise ValueError("race_date must use ISO format")

    rclass = canonical_class(row)
    grade_in = row.get("meeting_grade") or row.get("event_grade") or row.get("grade")
    grade = canonical_grade(grade_in)
    if grade_in and not grade:
        raise ValueError("unrecognized explicit event grade: " + str(grade_in))
    verified = registry_grade(row, registry if registry is not None else event_registry())
    if grade and verified and grade != verified:
        raise ValueError("conflicting explicit vs verified event grade")
    grade = grade or verified

    if rclass == "GIRLS":
        return {"status": "excluded", "grade": grade, "race_class": rclass,
                "relative_path": None, "reason": "girls_excluded_from_training"}
    if not grade or not rclass:
        return {"status": "quarantine", "grade": grade, "race_class": rclass,
                "relative_path": None, "reason": "unverified_grade_or_class"}

    return {"status": "included", "grade": grade, "race_class": rclass,
            "relative_path": f"grade={grade}/class={rclass}/year={day.year}",
            "reason": "verified_partition_only_not_data_completeness"}


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, help="single normalized race metadata JSON")
    args = p.parse_args()
    row = json.loads(Path(args.input).read_text(encoding="utf-8"))
    print(json.dumps(assign_partition(row), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
