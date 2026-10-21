import csv
import gzip
import io
import unittest
from datetime import date

from scripts.audit_archive_pilot import csv_rows, evaluate


def encode(rows, zipped=False):
    file = io.StringIO()
    writer = csv.DictWriter(file, fieldnames=["race_id", "race_date", "race_type"])
    writer.writeheader()
    writer.writerows(rows)
    blob = file.getvalue().encode("utf-8-sig")
    return gzip.compress(blob) if zipped else blob


def race(n, kind="Ａ級予選"):
    return {"race_id": "1320230101" + str(n).zfill(6), "race_date": "2023-01-01", "race_type": kind}


def archive():
    return {
        "calendar_links": encode([race(1), race(2), race(3, "ガールズ予選"), race(6, "Ｓ級予選")], True),
        "a1_a2": encode([race(1)]),
        "a3": encode([race(2)]),
        "s_f1": encode([race(6, "Ｓ級予選")]),
    }


class HistoricalPilotTests(unittest.TestCase):
    def test_reads_gzip_and_counts_exact_ids(self):
        result = evaluate(archive(), date(2023, 1, 1), date(2023, 1, 2))
        sample = result["daily"][0]
        self.assertEqual(sample["calendar_observed_link_count"], 4)
        self.assertEqual(sample["calendar_explicit_girls_labels"], 1)
        self.assertEqual(sample["matched_in_calendar_links"], 3)
        self.assertEqual(sample["calendar_not_in_these_three_archives"], 1)
        self.assertEqual(result["status"], "observed_archive_id_audit_only")
        self.assertIn("not an independent nationwide", result["limitations"][1])

    def test_unmatched_saved_race_requires_review(self):
        data = archive()
        data["calendar_links"] = encode([race(1), race(2)], True)
        report = evaluate(data, date(2023, 1, 1), date(2023, 1, 1))
        self.assertEqual(report["status"], "needs_review")
        self.assertEqual(report["daily"][0]["three_class_archives_not_in_calendar"], 1)

    def test_cross_class_duplicate_requires_review(self):
        data = archive()
        data["a3"] = encode([race(1), race(2)])
        report = evaluate(data, date(2023, 1, 1), date(2023, 1, 1))
        self.assertEqual(report["daily"][0]["cross_class_id_overlap_count"], 1)
        self.assertEqual(report["status"], "needs_review")

    def test_rejects_missing_race_id_column(self):
        with self.assertRaises(ValueError):
            csv_rows(b"notraceid,date\nx,2023-01-01", "bad.csv")

    def test_caps_audit_date_range(self):
        with self.assertRaises(ValueError):
            evaluate(archive(), date(2023, 1, 1), date(2023, 1, 31))


if __name__ == "__main__":
    unittest.main()
