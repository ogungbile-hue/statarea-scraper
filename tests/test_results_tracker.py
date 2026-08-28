"""Unit tests for ResultsTracker and analytics."""

import os
import shutil
import tempfile
import unittest
from statarea_scraper.results_tracker import ResultsTracker


class TestResultsTracker(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.tracker = ResultsTracker(output_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_evaluate_market_result(self):
        # 1. Over 1.5 Goals
        self.assertEqual(self.tracker.evaluate_market_result("Goals", "Over 1.5 Goals", 2, 0, "FT"), "WON")
        self.assertEqual(self.tracker.evaluate_market_result("Goals", "Over 1.5 Goals", 1, 0, "FT"), "LOST")
        self.assertEqual(self.tracker.evaluate_market_result("Goals", "Over 1.5 Goals", 1, 0, "LIVE"), "LIVE")

        # 2. Over 2.5 Goals
        self.assertEqual(self.tracker.evaluate_market_result("Goals", "Over 2.5 Goals", 2, 1, "FT"), "WON")
        self.assertEqual(self.tracker.evaluate_market_result("Goals", "Over 2.5 Goals", 1, 1, "FT"), "LOST")

        # 3. Under 3.5 Goals
        self.assertEqual(self.tracker.evaluate_market_result("Goals", "Under 3.5 Goals", 1, 1, "FT"), "WON")
        self.assertEqual(self.tracker.evaluate_market_result("Goals", "Under 3.5 Goals", 2, 2, "FT"), "LOST")

        # 4. BTTS (Both Teams To Score)
        self.assertEqual(self.tracker.evaluate_market_result("BTS", "Both Teams To Score (Yes)", 1, 1, "FT"), "WON")
        self.assertEqual(self.tracker.evaluate_market_result("BTS", "Both Teams To Score (Yes)", 2, 0, "FT"), "LOST")

        # 5. Double Chance 1X
        self.assertEqual(self.tracker.evaluate_market_result("Double Chance", "Home or Draw (1X)", 2, 1, "FT"), "WON")
        self.assertEqual(self.tracker.evaluate_market_result("Double Chance", "Home or Draw (1X)", 1, 1, "FT"), "WON")
        self.assertEqual(self.tracker.evaluate_market_result("Double Chance", "Home or Draw (1X)", 0, 1, "FT"), "LOST")

        # 6. Double Chance X2
        self.assertEqual(self.tracker.evaluate_market_result("Double Chance", "Draw or Away (X2)", 0, 1, "FT"), "WON")
        self.assertEqual(self.tracker.evaluate_market_result("Double Chance", "Draw or Away (X2)", 1, 1, "FT"), "WON")
        self.assertEqual(self.tracker.evaluate_market_result("Double Chance", "Draw or Away (X2)", 2, 1, "FT"), "LOST")

    def test_settle_today_slips_and_analytics(self):
        # Create a sample daily_5odds_slip.json with all 4 tiers
        slips_payload = {
            "strategy": "Multi-Tier High-Safety Daily Accumulator Slips",
            "generated_at": "2026-08-28 05:00:00",
            "slip_1_5odds": {
                "name": "Onítẹ́tẹ́ 1.5-Odds Ultra Banker Slip",
                "total_odds": 1.55,
                "average_confidence": 92.0,
                "legs_count": 2,
                "legs": [
                    {
                        "match_id": "101",
                        "market": "Goals",
                        "selection": "Over 1.5 Goals",
                        "estimated_odds": 1.25,
                        "confidence_score": 93.0,
                        "status": "PENDING",
                        "home_goals": None,
                        "away_goals": None,
                        "match_status": "SCHEDULED",
                    },
                    {
                        "match_id": "102",
                        "market": "Double Chance",
                        "selection": "Home or Draw (1X)",
                        "estimated_odds": 1.24,
                        "confidence_score": 91.0,
                        "status": "PENDING",
                        "home_goals": None,
                        "away_goals": None,
                        "match_status": "SCHEDULED",
                    },
                ],
            },
            "slip_3odds": {
                "name": "Onítẹ́tẹ́ 3-Odds Banker Slip",
                "total_odds": 3.02,
                "average_confidence": 82.0,
                "legs_count": 3,
                "legs": [
                    {
                        "match_id": "101",
                        "market": "Goals",
                        "selection": "Over 1.5 Goals",
                        "estimated_odds": 1.25,
                        "confidence_score": 93.0,
                        "status": "PENDING",
                        "home_goals": None,
                        "away_goals": None,
                        "match_status": "SCHEDULED",
                    },
                ],
            },
            "slip_5odds": {
                "name": "Onítẹ́tẹ́ 5-Odds Banker Slip",
                "total_odds": 4.95,
                "average_confidence": 76.0,
                "legs_count": 5,
                "legs": [
                    {
                        "match_id": "101",
                        "market": "Goals",
                        "selection": "Over 1.5 Goals",
                        "estimated_odds": 1.25,
                        "confidence_score": 93.0,
                        "status": "PENDING",
                        "home_goals": None,
                        "away_goals": None,
                        "match_status": "SCHEDULED",
                    },
                ],
            },
            "slip_10odds": {
                "name": "Onítẹ́tẹ́ 10-Odds Multiplier Slip",
                "total_odds": 10.20,
                "average_confidence": 71.0,
                "legs_count": 6,
                "legs": [
                    {
                        "match_id": "101",
                        "market": "Goals",
                        "selection": "Over 1.5 Goals",
                        "estimated_odds": 1.25,
                        "confidence_score": 93.0,
                        "status": "PENDING",
                        "home_goals": None,
                        "away_goals": None,
                        "match_status": "SCHEDULED",
                    },
                ],
            },
        }

        slips_path = os.path.join(self.test_dir, "daily_5odds_slip.json")
        import json
        with open(slips_path, "w", encoding="utf-8") as f:
            json.dump(slips_payload, f)

        # Mock fetch_live_scores_from_statarea
        self.tracker.fetch_live_scores_from_statarea = lambda *args, **kwargs: {
            "101": {"match_id": "101", "home_goals": 2, "away_goals": 1, "match_status": "FT", "live_minute": "FT"},
            "102": {"match_id": "102", "home_goals": 1, "away_goals": 0, "match_status": "FT", "live_minute": "FT"},
        }

        res = self.tracker.settle_today_slips()
        self.assertTrue(res["success"])
        self.assertEqual(res["total_records"], 4)

        # Check analytics
        analytics = self.tracker.compute_analytics()
        self.assertIn("summary", analytics)
        summary = analytics["summary"]
        self.assertEqual(summary["total_slips"], 4)
        self.assertEqual(summary["won_count"], 4)
        self.assertEqual(summary["win_rate"], 100.0)
        self.assertGreater(summary["net_profit"], 0.0)


if __name__ == "__main__":
    unittest.main()

