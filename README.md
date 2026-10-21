# keirin-data-hub

Public **code-only** hub for building a common historical keirin dataset for nyanta AI and haruqube AI.

## Status
**Step 2: date-batch planner only.** The repository does **not** scrape any website, does not hold training race data, and does not yet have durable progress persistence or object-storage integration. Collection is intentionally disabled until source permissions, completeness checks, and private storage are configured.

## First manual smoke test
Actions > **Verify historical batch planner** > Run workflow.

The workflow:
- tests date-batch selection;
- plans up to seven dates beginning 2023-01-01;
- uploads a short-lived planning-only JSON report;
- makes no network requests to racing websites.

Run locally:
```bash
python -m unittest discover -s tests -v
python scripts/plan_batch.py --start 2023-01-01 --end 2023-01-31 --days 7
```

## Future collection data contract (not implemented yet)
- canonical internal race ID, date, velodrome, race number, source IDs
- races, entries, predicted lines, all-finishing-order results, payouts, market odds and timestamped snapshots
- strict point-in-time separation: published final prices and post-race data are never treated as pre-start prediction features
- a date is `complete` only after an independent race-calendar census and per-race source/field validation
- canceled/non-offered/unavailable races get auditable statuses, not fabricated values
- use an approved source and comply with its automated-access and data-storage rules
- store permitted datasets and encryption credentials privately; **never** in this Public repository

The `state/progress.json` file is a placeholder for nonsensitive date status only. Updating it from collectors will be implemented after the durable store is chosen.
