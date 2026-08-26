"""Analytics and ML-ready relational dataset exporter for Statarea data."""

import csv
import json
import logging
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class AnalyticsExporter:
    """Transforms raw scraped fixtures JSON into clean, normalized relational CSV tables."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def process_json_file(self, json_path: str) -> Dict[str, str]:
        """Load JSON file and generate all 3 analytical CSV files."""
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"JSON input file not found: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        return self.process_data(raw_data)

    def process_data(self, data: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Transform raw data dictionaries into 3 normalized datasets:
        1. analysis_fixtures_today.csv
        2. analysis_h2h_records.csv
        3. analysis_team_metrics.csv
        """
        fixtures_csv = self._export_fixtures_today(data)
        h2h_csv = self._export_h2h_records(data)
        team_metrics_csv = self._export_team_metrics(data)

        return {
            "fixtures_today": fixtures_csv,
            "h2h_records": h2h_csv,
            "team_metrics": team_metrics_csv,
        }

    def _export_fixtures_today(self, data: List[Dict[str, Any]]) -> str:
        """Export match-level metadata, odds, predictions, and world rankings."""
        filepath = os.path.join(self.output_dir, "analysis_fixtures_today.csv")

        fieldnames = [
            "match_id",
            "date",
            "time",
            "country",
            "competition",
            "home_team",
            "away_team",
            "tip",
            "coef_1",
            "coef_x",
            "coef_2",
            "coef_ht1",
            "coef_htx",
            "coef_ht2",
            "coef_o15",
            "coef_o25",
            "coef_o35",
            "coef_bts",
            "coef_ots",
            "vote_1",
            "vote_x",
            "vote_2",
            "likes",
            "dislikes",
            "home_official_name",
            "home_founded",
            "home_country",
            "home_website",
            "home_world_rank",
            "away_official_name",
            "away_founded",
            "away_country",
            "away_website",
            "away_world_rank",
            "comparison_url",
        ]

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item in data:
                fix = item.get("fixture", {})
                odds = fix.get("odds", {})
                votes = fix.get("user_votes", {})
                h_info = item.get("home_team_info") or {}
                a_info = item.get("away_team_info") or {}

                row = {
                    "match_id": fix.get("match_id", ""),
                    "date": fix.get("date", ""),
                    "time": fix.get("time", ""),
                    "country": fix.get("country", ""),
                    "competition": fix.get("competition", ""),
                    "home_team": fix.get("home_team", ""),
                    "away_team": fix.get("away_team", ""),
                    "tip": fix.get("tip", ""),
                    "coef_1": odds.get("coef_1", "") if odds.get("coef_1") is not None else "",
                    "coef_x": odds.get("coef_x", "") if odds.get("coef_x") is not None else "",
                    "coef_2": odds.get("coef_2", "") if odds.get("coef_2") is not None else "",
                    "coef_ht1": odds.get("coef_ht1", "") if odds.get("coef_ht1") is not None else "",
                    "coef_htx": odds.get("coef_htx", "") if odds.get("coef_htx") is not None else "",
                    "coef_ht2": odds.get("coef_ht2", "") if odds.get("coef_ht2") is not None else "",
                    "coef_o15": odds.get("coef_o15", "") if odds.get("coef_o15") is not None else "",
                    "coef_o25": odds.get("coef_o25", "") if odds.get("coef_o25") is not None else "",
                    "coef_o35": odds.get("coef_o35", "") if odds.get("coef_o35") is not None else "",
                    "coef_bts": odds.get("coef_bts", "") if odds.get("coef_bts") is not None else "",
                    "coef_ots": odds.get("coef_ots", "") if odds.get("coef_ots") is not None else "",
                    "vote_1": votes.get("vote_1", "") if votes.get("vote_1") is not None else "",
                    "vote_x": votes.get("vote_x", "") if votes.get("vote_x") is not None else "",
                    "vote_2": votes.get("vote_2", "") if votes.get("vote_2") is not None else "",
                    "likes": votes.get("likes", "") if votes.get("likes") is not None else "",
                    "dislikes": votes.get("dislikes", "") if votes.get("dislikes") is not None else "",
                    "home_official_name": h_info.get("official_name", ""),
                    "home_founded": h_info.get("found", ""),
                    "home_country": h_info.get("country", ""),
                    "home_website": h_info.get("website", ""),
                    "home_world_rank": h_info.get("world_rank", "") if h_info.get("world_rank") is not None else "",
                    "away_official_name": a_info.get("official_name", ""),
                    "away_founded": a_info.get("found", ""),
                    "away_country": a_info.get("country", ""),
                    "away_website": a_info.get("website", ""),
                    "away_world_rank": a_info.get("world_rank", "") if a_info.get("world_rank") is not None else "",
                    "comparison_url": fix.get("comparison_url", ""),
                }
                writer.writerow(row)

        logger.info(f"Saved fixtures table: {filepath}")
        return filepath

    def _export_h2h_records(self, data: List[Dict[str, Any]]) -> str:
        """Export normalized historical H2H matches expanded into individual rows."""
        filepath = os.path.join(self.output_dir, "analysis_h2h_records.csv")

        fieldnames = [
            "fixture_id",
            "parent_match_date",
            "parent_competition",
            "h2h_date",
            "h2h_competition",
            "h2h_home_team",
            "h2h_away_team",
            "home_goals",
            "away_goals",
            "score_ft",
            "score_ht",
            "total_goals",
            "bts_result",
            "outcome",
            "events_count",
        ]

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item in data:
                fix = item.get("fixture", {})
                fixture_id = fix.get("match_id", "")
                parent_date = fix.get("date", "")
                parent_comp = fix.get("competition", "")
                h2h_list = item.get("h2h_matches", [])

                for m in h2h_list:
                    h_goals_str = m.get("home_goals")
                    a_goals_str = m.get("away_goals")
                    
                    home_goals = int(h_goals_str) if h_goals_str is not None and str(h_goals_str).isdigit() else None
                    away_goals = int(a_goals_str) if a_goals_str is not None and str(a_goals_str).isdigit() else None

                    score_ft = f"{home_goals}-{away_goals}" if home_goals is not None and away_goals is not None else ""
                    score_ht = m.get("half_time_score", "")
                    
                    total_goals = home_goals + away_goals if home_goals is not None and away_goals is not None else ""
                    bts_result = (home_goals > 0 and away_goals > 0) if home_goals is not None and away_goals is not None else ""

                    outcome = ""
                    if home_goals is not None and away_goals is not None:
                        if home_goals > away_goals:
                            outcome = "1"
                        elif home_goals == away_goals:
                            outcome = "X"
                        else:
                            outcome = "2"

                    events = m.get("events", [])

                    row = {
                        "fixture_id": fixture_id,
                        "parent_match_date": parent_date,
                        "parent_competition": parent_comp,
                        "h2h_date": m.get("date", ""),
                        "h2h_competition": m.get("competition", ""),
                        "h2h_home_team": m.get("home_team", ""),
                        "h2h_away_team": m.get("away_team", ""),
                        "home_goals": home_goals if home_goals is not None else "",
                        "away_goals": away_goals if away_goals is not None else "",
                        "score_ft": score_ft,
                        "score_ht": score_ht,
                        "total_goals": total_goals,
                        "bts_result": 1 if bts_result is True else (0 if bts_result is False else ""),
                        "outcome": outcome,
                        "events_count": len(events),
                    }
                    writer.writerow(row)

        logger.info(f"Saved H2H records table: {filepath}")
        return filepath

    def _export_team_metrics(self, data: List[Dict[str, Any]]) -> str:
        """Export aggregated statistical metrics computed from H2H and team profiles."""
        filepath = os.path.join(self.output_dir, "analysis_team_metrics.csv")

        fieldnames = [
            "match_id",
            "date",
            "home_team",
            "away_team",
            "home_world_rank",
            "away_world_rank",
            "h2h_total_matches",
            "h2h_home_wins",
            "h2h_draws",
            "h2h_away_wins",
            "h2h_home_win_rate",
            "h2h_draw_rate",
            "h2h_away_rate",
            "h2h_home_win_pct",
            "h2h_draw_pct",
            "h2h_away_win_pct",
            "h2h_avg_goals",
            "h2h_bts_rate_pct",
            "home_recent_form_scores",
            "away_recent_form_scores",
        ]

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item in data:
                fix = item.get("fixture", {})
                match_id = fix.get("match_id", "")
                date_val = fix.get("date", "")
                home_team = fix.get("home_team", "")
                away_team = fix.get("away_team", "")

                h_info = item.get("home_team_info") or {}
                a_info = item.get("away_team_info") or {}

                h2h_list = item.get("h2h_matches", [])
                total_h2h = len(h2h_list)

                h_wins = 0
                draws = 0
                a_wins = 0
                total_goals_sum = 0
                valid_goals_count = 0
                bts_count = 0

                for m in h2h_list:
                    h_team_m = m.get("home_team", "")
                    h_goals_str = m.get("home_goals")
                    a_goals_str = m.get("away_goals")

                    if h_goals_str is not None and str(h_goals_str).isdigit() and a_goals_str is not None and str(a_goals_str).isdigit():
                        hg = int(h_goals_str)
                        ag = int(a_goals_str)
                        total_goals_sum += (hg + ag)
                        valid_goals_count += 1
                        if hg > 0 and ag > 0:
                            bts_count += 1

                        if hg == ag:
                            draws += 1
                        else:
                            # Match if home_team in today's fixture won this historical match
                            winner_team = h_team_m if hg > ag else m.get("away_team", "")
                            if home_team.lower() in winner_team.lower() or winner_team.lower() in home_team.lower():
                                h_wins += 1
                            else:
                                a_wins += 1

                home_win_pct = round((h_wins / total_h2h) * 100, 1) if total_h2h > 0 else 0.0
                draw_pct = round((draws / total_h2h) * 100, 1) if total_h2h > 0 else 0.0
                away_win_pct = round((a_wins / total_h2h) * 100, 1) if total_h2h > 0 else 0.0
                avg_goals = round(total_goals_sum / valid_goals_count, 2) if valid_goals_count > 0 else 0.0
                bts_rate_pct = round((bts_count / valid_goals_count) * 100, 1) if valid_goals_count > 0 else 0.0

                # Form strings
                recent_home = item.get("recent_form_home", [])
                recent_away = item.get("recent_form_away", [])
                home_scores_str = " | ".join([m.get("score", "") for m in recent_home if m.get("score")])
                away_scores_str = " | ".join([m.get("score", "") for m in recent_away if m.get("score")])

                row = {
                    "match_id": match_id,
                    "date": date_val,
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_world_rank": h_info.get("world_rank", "") if h_info.get("world_rank") is not None else "",
                    "away_world_rank": a_info.get("world_rank", "") if a_info.get("world_rank") is not None else "",
                    "h2h_total_matches": total_h2h,
                    "h2h_home_wins": h_wins,
                    "h2h_draws": draws,
                    "h2h_away_wins": a_wins,
                    "h2h_home_win_rate": home_win_pct,
                    "h2h_draw_rate": draw_pct,
                    "h2h_away_rate": away_win_pct,
                    "h2h_home_win_pct": home_win_pct,
                    "h2h_draw_pct": draw_pct,
                    "h2h_away_win_pct": away_win_pct,
                    "h2h_avg_goals": avg_goals,
                    "h2h_bts_rate_pct": bts_rate_pct,
                    "home_recent_form_scores": home_scores_str,
                    "away_recent_form_scores": away_scores_str,
                }
                writer.writerow(row)

        logger.info(f"Saved team metrics table: {filepath}")
        return filepath


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    input_json = sys.argv[1] if len(sys.argv) > 1 else "output/fixtures_summary.json"
    exporter = AnalyticsExporter()
    res = exporter.process_json_file(input_json)
    print("Analytics export complete:", res)
