import unittest
from scripts.partition_rules import assign_partition, canonical_class, canonical_grade


class PartitionTests(unittest.TestCase):
    def test_grade_normalization(self):
        for src, expected in [("Ｇ３", "G3"), ("GⅢ", "G3"), ("FI", "F1"),
                              ("F2", "F2"), ("グランプリ", "GP"), ("GII", "G2")]:
            self.assertEqual(canonical_grade(src), expected)
        self.assertIsNone(canonical_grade("S級"))

    def test_a_and_s_are_distinct_within_grade(self):
        a = assign_partition({"race_date": "2023-01-01", "meeting_grade": "F1",
                              "race_type": "Ａ級予選"}, registry=[])
        s = assign_partition({"race_date": "2023-01-01", "meeting_grade": "F1",
                              "race_type": "Ｓ級予選"}, registry=[])
        self.assertEqual(a["relative_path"], "grade=F1/class=A1_A2/year=2023")
        self.assertEqual(s["relative_path"], "grade=F1/class=S/year=2023")
        self.assertEqual(a["status"], s["status"])

    def test_a3_challenge_separate_from_a12(self):
        actual = assign_partition({"race_date": "2023-01-01", "meeting_grade": "F2",
                                   "race_type": "チャレンジ予選"}, registry=[])
        self.assertEqual(actual["relative_path"], "grade=F2/class=A3/year=2023")

    def test_girls_excluded_even_when_grade_known(self):
        actual = assign_partition({"race_date": "2023-01-01", "meeting_grade": "F2",
                                   "race_type": "ガールズ決勝"}, registry=[])
        self.assertEqual(actual["status"], "excluded")
        self.assertIsNone(actual["relative_path"])

    def test_verified_tachikawa_event_uses_registry(self):
        actual = assign_partition({
            "race_date": "2023-01-04", "source": "kdreams",
            "source_race_id": "2820230104010001",
            "race_type": "S級一予選"
        })
        self.assertEqual(actual["relative_path"], "grade=G3/class=S/year=2023")

    def test_unverified_s_class_grade_quarantined(self):
        actual = assign_partition({"race_date": "2023-01-04", "race_type": "S級一予選",
                                   "source": "netkeirin", "race_id": "202301040101"}, registry=[])
        self.assertEqual(actual["status"], "quarantine")
        self.assertIsNone(actual["relative_path"])

    def test_unverified_dates_not_called_tachikawa_g3(self):
        actual = assign_partition({
            "race_date": "2023-01-08", "source": "kdreams",
            "source_race_id": "2820230104010001",
            "race_type": "S級一予選"
        })
        self.assertEqual(actual["status"], "quarantine")

    def test_grade_conflict_must_raise(self):
        with self.assertRaisesRegex(ValueError, "conflicting"):
            assign_partition({
                "race_date": "2023-01-04", "source": "kdreams",
                "source_race_id": "2820230104010001",
                "meeting_grade": "F1", "race_type": "S級一予選"
            })

    def test_invalid_grade_must_raise(self):
        with self.assertRaisesRegex(ValueError, "unrecognized"):
            assign_partition({"race_date": "2023-01-01",
                              "meeting_grade": "unverified", "race_type": "S級"}, registry=[])

    def test_missing_class_quarantined(self):
        result = assign_partition({"race_date": "2023-01-01", "meeting_grade": "G3",
                                   "race_type": "特別競輪"}, registry=[])
        self.assertEqual(result["status"], "quarantine")

    def test_date_is_validated(self):
        with self.assertRaises(ValueError):
            assign_partition({"race_date": "20230101", "meeting_grade": "F1",
                              "race_type": "S級"}, registry=[])


if __name__ == "__main__":
    unittest.main()
