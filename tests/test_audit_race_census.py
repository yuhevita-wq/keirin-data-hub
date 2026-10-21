import unittest

from scripts.audit_race_census import audit_discovery


def row(race_no, source_id=None):
    result = {"race_date": "2023-01-01",
              "venue_key": "SYNTHETIC-VENUE", "race_no": race_no}
    if source_id is not None:
        result["source_race_id"] = source_id
    return result


def example(verified=True):
    return {
        "date": "2023-01-01",
        "calendar_verified": verified,
        "calendar_scope": "all_mens_races",
        "calendar_source": "test fixture, not an actual calendar",
        "calendar_races": [row(1), row(2), row(3)],
        "sources": {
            "winticket": [row(1, "w1"), row(2, "w2"), row(3, "w3")],
            "netkeirin": [row(1, "n1"), row(3, "n3")]
        }
    }


class DiscoveryAuditTests(unittest.TestCase):
    def test_verified_calendar_union_covers_all_but_detects_source_gap(self):
        result = audit_discovery(example())
        self.assertEqual(result["status"], "calendar_covered_by_union")
        self.assertEqual(result["unique_observed_races"], 3)
        self.assertEqual(result["missing_by_source"]["netkeirin"],
                         ["2023-01-01/SYNTHETIC-VENUE/02"])
        self.assertEqual(result["missing_from_calendar_union"], [])
        self.assertNotEqual(result["limitation"], "")

    def test_unverified_calendar_cannot_claim_nationwide_coverage(self):
        result = audit_discovery(example(verified=False))
        self.assertEqual(result["status"], "nationwide_coverage_unverified")
        self.assertFalse(result["calendar_verified_by_input"])

    def test_missing_from_all_sources_requires_review(self):
        payload = example()
        payload["sources"]["winticket"].pop(1)  # remove race 2, absent from netkeirin
        result = audit_discovery(payload)
        self.assertEqual(result["status"], "review_needed")
        self.assertEqual(result["missing_from_calendar_union"],
                         ["2023-01-01/SYNTHETIC-VENUE/02"])

    def test_unexpected_extra_race_requires_review(self):
        payload = example()
        payload["sources"]["winticket"].append(row(4, "w4"))
        self.assertEqual(audit_discovery(payload)["status"], "review_needed")

    def test_duplicate_source_identity_requires_review(self):
        payload = example()
        payload["sources"]["netkeirin"].append(row(2, "n1"))
        self.assertTrue(audit_discovery(payload)["errors"])

    def test_invalid_row_is_rejected(self):
        payload = example()
        payload["sources"]["netkeirin"][0]["race_date"] = "2023-01-02"
        with self.assertRaises(ValueError):
            audit_discovery(payload)


if __name__ == "__main__":
    unittest.main()
