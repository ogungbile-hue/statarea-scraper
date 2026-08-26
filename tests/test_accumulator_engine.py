"""Unit tests for AccumulatorEngine."""

import os
import shutil
import tempfile
import unittest
import pandas as pd
from statarea_scraper.accumulator_engine import AccumulatorEngine, MarketCandidate


class TestAccumulatorEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.engine = AccumulatorEngine(output_dir=self.test_dir)

        # Create dummy fixtures and metrics CSV
        fixtures_data = [
            {
                "match_id": "1", "date": "2026-08-26", "time": "20:00", "competition": "LALIGA", "country": "Spain",
                "home_team": "Real Madrid", "away_team": "Real Sociedad", "tip": "1",
                "coef_1": 68, "coef_x": 24, "coef_2": 8, "coef_o15": 92, "coef_o25": 67, "coef_o35": 45, "coef_bts": 68,
                "vote_1": 39, "vote_x": 3, "vote_2": 5, "home_world_rank": 7, "away_world_rank": 93,
            },
            {
                "match_id": "2", "date": "2026-08-26", "time": "19:45", "competition": "PREMIERSHIP", "country": "England",
                "home_team": "Newcastle", "away_team": "West Brom", "tip": "1",
                "coef_1": 63, "coef_x": 27, "coef_2": 10, "coef_o15": 90, "coef_o25": 71, "coef_o35": 38, "coef_bts": 66,
                "vote_1": 28, "vote_x": 2, "vote_2": 1, "home_world_rank": 22, "away_world_rank": 362,
            },
            {
                "match_id": "3", "date": "2026-08-26", "time": "19:45", "competition": "PREMIER LEAGUE", "country": "England",
                "home_team": "Tottenham", "away_team": "Charlton", "tip": "1",
                "coef_1": 58, "coef_x": 28, "coef_2": 14, "coef_o15": 91, "coef_o25": 57, "coef_o35": 37, "coef_bts": 67,
                "vote_1": 16, "vote_x": 0, "vote_2": 2, "home_world_rank": 53, "away_world_rank": None,
            },
            {
                "match_id": "4", "date": "2026-08-26", "time": "18:30", "competition": "PREMIERSHIP", "country": "South Africa",
                "home_team": "Mamelodi Sundowns", "away_team": "AmaZulu", "tip": "1",
                "coef_1": 67, "coef_x": 21, "coef_2": 12, "coef_o15": 89, "coef_o25": 54, "coef_o35": 33, "coef_bts": 68,
                "vote_1": 6, "vote_x": 0, "vote_2": 2, "home_world_rank": 99, "away_world_rank": 400,
            },
            {
                "match_id": "5", "date": "2026-08-26", "time": "18:30", "competition": "PREMIERSHIP", "country": "South Africa",
                "home_team": "Golden Arrows", "away_team": "Stellenbosch FC", "tip": "X",
                "coef_1": 40, "coef_x": 41, "coef_2": 19, "coef_o15": 89, "coef_o25": 62, "coef_o35": 25, "coef_bts": 69,
                "vote_1": 1, "vote_x": 4, "vote_2": 1, "home_world_rank": None, "away_world_rank": 634,
            },
            {
                "match_id": "6", "date": "2026-08-26", "time": "15:00", "competition": "SUPERLIGA", "country": "Uzbekistan",
                "home_team": "Lokomotiv Tashkent", "away_team": "FC Bunyodkor", "tip": "1",
                "coef_1": 58, "coef_x": 28, "coef_2": 14, "coef_o15": 89, "coef_o25": 64, "coef_o35": 30, "coef_bts": 66,
                "vote_1": 4, "vote_x": 0, "vote_2": 0, "home_world_rank": None, "away_world_rank": None,
            },
        ]

        metrics_data = [
            {"match_id": "1", "home_recent_form_scores": "3-1 | 2-2 | 4-1 | 2-1", "away_recent_form_scores": "2-1 | 3-1 | 1-2", "h2h_avg_goals": 3.39},
            {"match_id": "2", "home_recent_form_scores": "3-1 | 2-2 | 2-1 | 3-0", "away_recent_form_scores": "1-2 | 1-3 | 0-3", "h2h_avg_goals": 3.00},
            {"match_id": "3", "home_recent_form_scores": "3-1 | 4-0 | 2-2", "away_recent_form_scores": "1-2 | 0-3", "h2h_avg_goals": 3.33},
            {"match_id": "4", "home_recent_form_scores": "3-0 | 3-1 | 2-1", "away_recent_form_scores": "0-2 | 1-3", "h2h_avg_goals": 2.89},
            {"match_id": "5", "home_recent_form_scores": "2-2 | 3-1", "away_recent_form_scores": "2-1 | 2-2", "h2h_avg_goals": 2.53},
            {"match_id": "6", "home_recent_form_scores": "3-1 | 3-1", "away_recent_form_scores": "2-1 | 1-2", "h2h_avg_goals": 2.67},
        ]

        h2h_data = [
            {"fixture_id": "1", "h2h_date": "2026-02-10", "outcome": "1", "total_goals": 3, "bts_result": 1},
            {"fixture_id": "1", "h2h_date": "2025-10-15", "outcome": "1", "total_goals": 2, "bts_result": 0},
            {"fixture_id": "2", "h2h_date": "2024-03-20", "outcome": "1", "total_goals": 3, "bts_result": 1},
            {"fixture_id": "2", "h2h_date": "2023-11-05", "outcome": "X", "total_goals": 2, "bts_result": 1},
            {"fixture_id": "4", "h2h_date": "2025-05-12", "outcome": "1", "total_goals": 2, "bts_result": 0},
            {"fixture_id": "4", "h2h_date": "2024-09-18", "outcome": "1", "total_goals": 3, "bts_result": 1},
        ]

        self.f_path = os.path.join(self.test_dir, "analysis_fixtures_today.csv")
        self.m_path = os.path.join(self.test_dir, "analysis_team_metrics.csv")
        self.h_path = os.path.join(self.test_dir, "analysis_h2h_records.csv")

        pd.DataFrame(fixtures_data).to_csv(self.f_path, index=False)
        pd.DataFrame(metrics_data).to_csv(self.m_path, index=False)
        pd.DataFrame(h2h_data).to_csv(self.h_path, index=False)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_evaluate_and_build_slips(self):
        res = self.engine.generate_and_save(self.f_path, self.m_path, self.h_path)
        self.assertTrue(os.path.exists(res["json_file"]))
        self.assertTrue(os.path.exists(res["txt_file"]))
        self.assertIsNotNone(res["banker_ticket"])
        self.assertGreater(res["banker_ticket"].total_odds, 1.2)
        self.assertGreaterEqual(res["banker_ticket"].legs_count, 2)


if __name__ == "__main__":
    unittest.main()
