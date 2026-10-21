# keirin-data-hub

Public **code-only** hub for preparing one common historical keirin dataset for nyanta AI and haruqube AI.

## Current status — Step 3: offline source-discovery audit

**No real racing data collection has started.**

Implemented:
- A date planner supporting batches of 1–14 days and placeholder retry statuses: scripts/plan_batch.py
- Offline comparison of two source race lists against an independently supplied nationwide calendar: scripts/audit_race_census.py
- Unit tests and an explicitly **synthetic demonstration**: examples/SYNTHETIC_discovery.json
- Git exclusions for sensitive data, keys, local databases and archives

## Test from GitHub Actions
Actions → **Verify planning and race census audit** → Run workflow.

Expected output:
- Unit tests pass
- Seven planned dates: 2023-01-01 through 2023-01-07
- Synthetic sample: netkeirin is missing one fabricated race relative to WINTICKET
- Sample status: **nationwide_coverage_unverified**, because there is no independently verified nationwide calendar. This does NOT mean actual racing data is missing.
- Artifact contains planning/audit JSON only and expires after 7 days.

## Audit limits
- Two site listings alone do not establish nationwide completeness.
- Canonical venue identifiers need real verified mapping before comparing provider data.
- Race discovery does not prove entries, full finishing order, payout or all odds markets.
- Historical final odds and post-race values are not prematch timepoint snapshots.
- Permissions/terms to bulk-access source data must be verified separately.
- Durable storage, source adapters, checkpoint updates and historical ingestion are **not yet implemented**.
- Never commit passwords, decryption keys or source datasets to this Public repository.

## Planned next stages
1. Check authorized providers and an independent comprehensive nationwide calendar.
2. Configure restricted durable storage for data allowed to be retained.
3. Implement source connectors with missing-field audit, deduplicated upsert, rate limits, and persistent progress.
4. Validate seven real days before attempting large-scale backfill.
5. Export point-in-time-safe training features for both AI models.

The state/progress.json file is currently a placeholder. The GitHub Action does not modify it.
