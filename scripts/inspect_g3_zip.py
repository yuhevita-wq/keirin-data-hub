#!/usr/bin/env python3
"""Read-only integrity/structure inspection of the archived 2023 G3 Q1 ZIP.

Downloads only from the owner's already-public GitHub repository, verifies SHA256,
and emits file shapes and aggregate counts. Never uploads/extracts raw data.
"""
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_REPO = "yuhevita-wq/keirin-market-analysis-"
SOURCE_PATH = "data/grade_races/g3/2023/g3-all-2023-q1-non-girls.zip"
EXPECTED_SHA256 = "c478dbdc21a0f4515109e66143fce667df9e45af48ceb7c9e9a22ba15203b0b4"
MAX_BYTES = 12_000_000


def download():
    url = f"https://raw.githubusercontent.com/{SOURCE_REPO}/main/{SOURCE_PATH}"
    req = Request(url, headers={"User-Agent": "keirin-data-hub-archived-audit/1.0"})
    with urlopen(req, timeout=45) as res:
        data = res.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("ZIP exceeds fixed audit size limit")
    actual_sha256 = hashlib.sha256(data).hexdigest()
    if actual_sha256 != EXPECTED_SHA256:
        raise ValueError("G3 source ZIP failed SHA256 integrity check")
    return data


def describe(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if z.testzip() is not None:
            raise ValueError("ZIP failed CRC integrity check")
        members = []
        for f in z.infolist():
            if f.is_dir():
                continue
            if f.file_size > 200_000_000:
                raise ValueError("Archive member exceeds 200 MB decompressed")
            detail = {"name": f.filename, "uncompressed_bytes": f.file_size}
            if f.filename.endswith(".csv"):
                with z.open(f) as src:
                    txt = io.TextIOWrapper(src, encoding="utf-8-sig", newline="")
                    reader = csv.DictReader(txt)
                    detail["columns"] = reader.fieldnames
                    detail["rows"] = sum(1 for _ in reader)
            elif f.filename.endswith(".json"):
                data = json.loads(z.read(f))
                detail["json_type"] = type(data).__name__
                if isinstance(data, dict):
                    detail["keys"] = list(data)[:35]
                    detail["counts"] = {k: v for k, v in data.items()
                                        if isinstance(v, (int, float)) and not isinstance(v, bool)}
                elif isinstance(data, list):
                    detail["length"] = len(data)
                    if data and isinstance(data[0], dict):
                        detail["sample_record_keys"] = list(data[0])
            members.append(detail)
    return {"source_path": SOURCE_PATH, "source_sha256_verified": EXPECTED_SHA256,
            "zip_bytes": len(raw), "member_count": len(members), "members": members,
            "disclaimer": "Structural archive inspection only; no per-race content or learning readiness attested."}


def main():
    report = describe(download())
    dest = Path("out/g3_2023_q1_zip_structure.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
