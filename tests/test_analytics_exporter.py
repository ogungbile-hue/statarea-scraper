"""Unit tests for AnalyticsExporter."""

import os
import shutil
import tempfile
import unittest
from statarea_scraper.analytics_exporter import AnalyticsExporter

SAMPLE_RAW_DATA = [
    {
        "fixture": {
            "match_id": "1001",
            "date": "2026-08-26",
            "time": "20:00",
            "competition": "LALIGA",
            "country": "Spain",
            "home_team": "Real Madrid",
            "away_team": "Real Sociedad",
            "tip": "1",
            "comparison_url": "https://www.statarea.com/compare/teams/Real+Madrid/Real+Sociedad",
            "odds": {
                "coef_1": 68,
                "coef_x": 24,
                "coef_2": 8,
                "coef_ht1": 49,
                "coef_htx": 35,
                "coef_ht2": 16,
                "coef_o15": 92,
                "coef_o25": 67,
                "coef_o35": 45,
                "coef_bts": 63,
                "coef_ots": 37,
            },
            "user_votes": {
                "vote_1": 39,
                "vote_x": 3,
                "vote_2": 5,
                "likes": 25,
                "dislikes": 3,
            },
        },
        "home_team_info": {
            "name": "Real Madrid",
            "official_name": "Real Madrid Club de Fútbol",
            "found": "1902",
            "country": "Spain",
            "website": "http://realmadrid.com",
            "world_rank": 7,
        },
        "away_team_info": {
            "name": "Real Sociedad",
            "official_name": "Real Sociedad de Fútbol",
            "found": "1909",
            "country": "Spain",
            "website": "http://realsociedad.com",
            "world_rank": 93,
        },
        "h2h_matches": [
            {
                "date": "2026-02-14",
                "competition": "Spain - Laliga",
                "home_team": "Real Madrid",
                "away_team": "Real Sociedad",
                "home_goals": "4",
                "away_goals": "1",
                "half_time_score": "1-3",
                "events": ["[goal] 5' Player A"],
            },
            {
                "date": "2025-09-13",
                "competition": "Spain - Laliga",
                "home_team": "Real Sociedad",
                "away_team": "Real Madrid",
                "home_goals": "1",
                "away_goals": "2",
                "half_time_score": "0-0",
                "events": ["[goal] 12' Player B"],
            },
        ],
        "recent_form_home": [{"score": "2-0"}, {"score": "3-1"}],
        "recent_form_away": [{"score": "1-1"}, {"score": "0-2"}],
        "match_facts": [],
    }
]


class TestAnalyticsExporter(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.exporter = AnalyticsExporter(output_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_process_data(self):
        files = self.exporter.process_data(SAMPLE_RAW_DATA)
        self.assertTrue(os.path.exists(files["fixtures_today"]))
        self.assertTrue(os.path.exists(files["h2h_records"]))
        self.assertTrue(os.path.exists(files["team_metrics"]))

        # Verify H2H records count
        with open(files["h2h_records"], "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 3)  # header + 2 matches

        # Verify Team Metrics
        with open(files["team_metrics"], "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)  # header + 1 fixture row
            self.assertIn("Real Madrid", lines[1])
            self.assertIn("100.0", lines[1])  # 2 wins out of 2 for Real Madrid


if __name__ == "__main__":
    unittest.main()
