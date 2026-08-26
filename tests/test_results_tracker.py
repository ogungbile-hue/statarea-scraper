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

    def test_compute_analytics(self):
        analytics = self.tracker.compute_analytics()
        self.assertIn("summary", analytics)
        self.assertIn("daily", analytics)
        self.assertIn("weekly", analytics)
        self.assertIn("monthly", analytics)
        self.assertIn("market_accuracy", analytics)

        summary = analytics["summary"]
        self.assertGreater(summary["total_slips"], 0)
        self.assertGreaterEqual(summary["win_rate"], 0.0)
        self.assertIn("net_profit", summary)


if __name__ == "__main__":
    unittest.main()
