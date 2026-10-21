import csv
import gzip
import io
import unittest
from datetime import date

from scripts.audit_real_partitions import evaluate_partitions


def encoded(rows, gzip_output=False):
    fh = io.StringIO()
    writer = csv.DictWriter(fh, fieldnames=[
        "race_id", "race_date", "race_type", "meeting_grade", "class_scope"])
    writer.writeheader()
    writer.writerows(rows)
    raw = fh.getvalue().encode("utf-8-sig")
    return gzip.compress(raw) if gzip_output else raw


def row(rid, day="2023-01-04", race_type="Ｓ級一予選", grade="", scope=""):
    return {"race_id": rid, "race_date": day, "race_type": race_type,
            "meeting_grade": grade, "class_scope": scope}


S_F1_ID = "1320230104010006"
A_F2_ID = "2720230104010001"
TACHIKAWA_G3_ID = "2820230104010001"
GIRLS_ID = "2320230104010006"


def fixtures():
    cal = [
        row(S_F1_ID, race_type="Ｓ級予選"),
        row(A_F2_ID, race_type="チャレンジ予選"),
        row(TACHIKAWA_G3_ID, race_type="Ｓ級一予選"),
        row(GIRLS_ID, race_type="ガールズ予選1")
    ]
    return {
        "calendar_links": encoded(cal, True),
        "a1_a2": encoded([]),
        "a3": encoded([row(A_F2_ID, race_type="チャレンジ予選", grade="F2", scope="A3 challenge")]),
        "s_f1": encoded([row(S_F1_ID, race_type="Ｓ級予選", grade="F1")])
    }


class RealPartitionTests(unittest.TestCase):
    def test_real_archive_schema_and_grade_partition(self):
        audit, manifest = evaluate_partitions(fixtures(), date(2023, 1, 4), date(2023, 1, 4))
        self.assertEqual(audit["stats"]["calendar_observed"], 4)
        self.assertEqual(audit["stats"]["included"], 3)
        self.assertEqual(audit["stats"]["excluded_girls"], 1)
        self.assertEqual(audit["stats"]["classified_without_entry_archive"], 1)
        by_id = {x["race_id"]: x for x in manifest}
        self.assertEqual(by_id[S_F1_ID]["partition_key"], "grade=F1/class=S/year=2023")
        self.assertEqual(by_id[A_F2_ID]["partition_key"], "grade=F2/class=A3/year=2023")
        self.assertEqual(by_id[TACHIKAWA_G3_ID]["partition_key"], "grade=G3/class=S/year=2023")
        self.assertFalse(by_id[TACHIKAWA_G3_ID]["race_record_available"])
        self.assertEqual(by_id[GIRLS_ID]["partition_status"], "excluded")
        self.assertEqual(audit["status"], "classified_not_training_ready")

    def test_unverified_race_class_stays_quarantined(self):
        f = fixtures()
        missing = row("3020230104010003", race_type="男子特別競走")
        cal = [row(S_F1_ID, race_type="Ｓ級予選"), missing]
        f["calendar_links"] = encoded(cal, True)
        f["a3"] = encoded([])
        audit, manifest = evaluate_partitions(f, date(2023, 1, 4), date(2023, 1, 4))
        self.assertEqual(audit["stats"]["quarantined"], 1)
        self.assertEqual(audit["status"], "requires_review")

    def test_conflicting_calendar_class_rejected(self):
        f = fixtures()
        cal = [row(S_F1_ID, race_type="チャレンジ予選")]
        f["calendar_links"] = encoded(cal, True)
        f["a3"] = encoded([])
        with self.assertRaisesRegex(ValueError, "Calendar/class-archive conflict"):
            evaluate_partitions(f, date(2023, 1, 4), date(2023, 1, 4))

    def test_duplicate_cross_archive_raises(self):
        f = fixtures()
        f["a1_a2"] = encoded([row(S_F1_ID, race_type="Ｓ級予選", grade="F1")])
        with self.assertRaisesRegex(ValueError, "Same race in two"):
            evaluate_partitions(f, date(2023, 1, 4), date(2023, 1, 4))


if __name__ == "__main__":
    unittest.main()
