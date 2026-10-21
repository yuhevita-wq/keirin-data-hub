import unittest
from scripts.classify_archive_gap import classify, get_label

class ClassificationTests(unittest.TestCase):
    def test_girls_explicit(self):
        self.assertEqual(classify({"race_type": "ガールズ予選"}), "girls")
        self.assertEqual(classify({"race_type": "Ｌ級ガ決勝"}), "girls")
    def test_g3_explicit(self):
        self.assertEqual(classify({"race_type": "Ｓ級一次予選", "meeting_grade": "G3"}), "explicit_g3")
    def test_verified_tachikawa_g3_on_exact_event_dates(self):
        self.assertEqual(classify({"race_date": "2023-01-06", "odds_page_url": "https://keirin.kdreams.jp/tachikawa/racedetail/2820230104030012/?pageType=odds", "race_type": "S級準決勝"}), "verified_tachikawa_g3")
    def test_other_venue_never_inherits_tachikawa_g3(self):
        self.assertEqual(classify({"race_date": "2023-01-06", "odds_page_url": "https://keirin.kdreams.jp/toride/racedetail/example", "race_type": "S級準決勝"}), "s_class_grade_unverified")
    def test_s_class_without_grade_is_not_claimed_g3(self):
        self.assertEqual(classify({"race_type": "Ｓ級一次予選"}), "s_class_grade_unverified")
    def test_a_class(self):
        self.assertEqual(classify({"race_type": "Ａ級予選"}), "a_class_unmatched")
    def test_unknown(self):
        self.assertEqual(classify({"race_type": "特別戦"}), "unknown")
    def test_absent_label(self):
        self.assertEqual(get_label({}), "")

if __name__ == "__main__":
    unittest.main()
