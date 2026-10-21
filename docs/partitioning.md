# Partitioning: one dataset, grade/class-aware storage

The same canonical data hub supplies **nyanta AI** and **haruqube AI**. Physical partitions are **not** separate models and never remove G1/G2/G3/F1/F2 races from either model's potential training set.

## Event grade (separate from rider/race class)
- GP, G1, G2, G3, F1, F2
- Race class: S / A1_A2 / A3
- Girls: excluded from the two male-race training exports
- Unknown or conflicting class/grade: quarantine; do not invent a class

Example storage keys for a future **private** object store:

- \`races/grade=G3/class=S/year=2023/...\`
- \`entries/grade=F1/class=A1_A2/year=2023/...\`
- \`results/grade=F2/class=A3/year=2023/...\`
- \`odds/grade=G3/class=S/year=2023/...\`
- \`payouts/grade=G3/class=S/year=2023/...\`

Examples show potential paths, not currently stored datasets. Each table shares a canonical race key with adapters for source-specific IDs. In live use, grade/class/year should be **partition columns** of compressed Parquet, not assumptions encoded into 3rd-party race IDs.

## Read-only metadata partition smoke test

Run \`python -m unittest discover -s tests -v\`.

The same event may have A and S races: **meeting grade** and **race class** are independent. An S-class label alone never implies G3.

For the 2023-01-04 to 2023-01-07 Tachikawa example, a specifically verified event registry record permits G3 classification even though the historical calendar file omitted a grade field. Outside those exact dates and location, a bare S-grade record is quarantined.

No bulk data collection, normalization of raw records, or per-AI training exports is implemented in this step. Never put raw data or private credentials in the public repository.
