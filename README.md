# keirin-data-hub

Public **code-only** hub for preparing one common historical keirin dataset for nyanta AI and haruqube AI.

## Current status — Step 4: opt-in audit of one real archived week

**No new racing-site scraping has started.** An opt-in pilot now READS existing records from the owner's public GitHub archive, compares race IDs, and publishes aggregate findings only.

Implemented:
- A date planner supporting batches of 1–14 days and placeholder retry statuses: scripts/plan_batch.py
- Offline comparison of two source race lists against an independently supplied nationwide calendar: scripts/audit_race_census.py
- Unit tests and an explicitly **synthetic demonstration**: examples/SYNTHETIC_discovery.json
- Git exclusions for sensitive data, keys, local databases and archives

## First historical archive audit (manual only)

Actions → **Pilot audit of existing historical archive** → Run workflow.

This reads only these already archived GitHub files: Jan 2023 observed-link calendar index, Jan–Feb 2023 A1/A2 and A3 race metadata, and Q1 2023 S-class F1 race metadata. It audits Jan 1–7, 2023 only. It saves aggregate daily counts plus file SHA256 checksums, never the copied datasets.

The calendar is an observed KDreams link list, **not independently certified nationwide coverage**. Discrepancies are review indicators, and other race categories may explain calendar-only rows. A race ID match is not evidence that full entries, results or seven-bet odds are ready for training.

## Previous offline-only test


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

## Planned next stages (not yet implemented)
1. Check authorized providers and an independent comprehensive nationwide calendar.
2. Configure restricted durable storage for data allowed to be retained.
3. Implement source connectors with missing-field audit, deduplicated upsert, rate limits, and persistent progress.
4. Validate seven real days before attempting large-scale backfill.
5. Export point-in-time-safe training features for both AI models.

The state/progress.json file is currently a placeholder. The GitHub Action does not modify it.
