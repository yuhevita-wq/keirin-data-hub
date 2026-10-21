import unittest
from datetime import date
from scripts.plan_batch import select_dates


class TestBatchPlanner(unittest.TestCase):
    def test_first_seven_days(self):
        plan = select_dates(date(2023, 1, 1), date(2023, 1, 31), 7,
                            {"schema_version": 1, "days": {}})
        self.assertEqual(plan["planned_dates"],
                         [f"2023-01-{day:02d}" for day in range(1, 8)])

    def test_skip_verified_and_retry_incomplete(self):
        plan = select_dates(date(2023, 1, 1), date(2023, 1, 5), 3,
                            {"schema_version": 1, "days": {
                                "2023-01-01": {"status": "complete", "attempts": 1},
                                "2023-01-02": {"status": "partial", "attempts": 2},
                                "2023-01-03": {"status": "failed", "attempts": 3},
                                "2023-01-04": {"status": "verified_unavailable", "attempts": 1}
                            }})
        self.assertEqual(plan["planned_dates"], ["2023-01-02", "2023-01-05"])
        self.assertEqual(plan["blocked_days"], ["2023-01-03"])
        self.assertEqual(plan["completed_days_skipped"], 2)

    def test_reject_invalid_limits_and_schema(self):
        with self.assertRaises(ValueError):
            select_dates(date(2023, 1, 1), date(2023, 1, 2), 15,
                         {"schema_version": 1, "days": {}})
        with self.assertRaises(ValueError):
            select_dates(date(2023, 1, 1), date(2023, 1, 2), 7,
                         {"schema_version": 2, "days": {}})


if __name__ == "__main__":
    unittest.main()
