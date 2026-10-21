#!/usr/bin/env python3
"""Plan small, resumable historical-date batches; this script does NOT scrape."""
import argparse
import json
from datetime import date, timedelta
from pathlib import Path

COMPLETED = {"complete", "verified_unavailable"}
RETRYABLE = {"pending", "partial", "failed"}
MAX_ATTEMPTS = 3


def select_dates(start, end, limit, ledger):
    """Return next date candidates without changing or inventing progress."""
    if start > end:
        raise ValueError("start must be on or before end")
    if not 1 <= limit <= 14:
        raise ValueError("days per batch must be between 1 and 14")
    if ledger.get("schema_version") != 1 or not isinstance(ledger.get("days"), dict):
        raise ValueError("unsupported ledger schema")
    selected = []
    skipped_complete = 0
    blocked = []
    d = start
    while d <= end:
        day = d.isoformat()
        meta = ledger["days"].get(day, {})
        status = meta.get("status", "pending")
        attempts = meta.get("attempts", 0)
        if status in COMPLETED:
            skipped_complete += 1
        elif status == "blocked" or (status in RETRYABLE and attempts >= MAX_ATTEMPTS):
            blocked.append(day)
        elif status in RETRYABLE:
            if len(selected) < limit:
                selected.append(day)
        else:
            raise ValueError("unknown status for " + day + ": " + str(status))
        d += timedelta(days=1)
    return {"planned_dates": selected, "planned_count": len(selected),
            "completed_days_skipped": skipped_complete, "blocked_days": blocked,
            "exhausted": not selected and not blocked,
            "note": "Planning only. Collection, completeness verification, and durable checkpoint updates are not yet implemented."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--ledger", default="state/progress.json")
    p.add_argument("--output", default="out/batch_plan.json")
    args = p.parse_args()
    ledger_path = Path(args.ledger)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    plan = select_dates(date.fromisoformat(args.start), date.fromisoformat(args.end),
                        args.days, ledger)
    plan["range"] = [args.start, args.end]
    plan["batch_limit_days"] = args.days
    dest = Path(args.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False))


if __name__ == "__main__":
    main()
