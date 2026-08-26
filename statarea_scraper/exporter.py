"""Export scraped match data to JSON and CSV formats."""

import csv
import json
import logging
import os
from typing import List
from dataclasses import asdict

from .models import DeepMatchData

logger = logging.getLogger(__name__)


class StatareaExporter:
    """Handles saving structured match and H2H statistics to disk."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def export_json(self, matches: List[DeepMatchData], filename: str = "fixtures_summary.json") -> str:
        """
        Export complete hierarchical match data to a JSON file.
        
        Args:
            matches: List of DeepMatchData objects
            filename: Target JSON filename
            
        Returns:
            Path to the saved JSON file.
        """
        filepath = os.path.join(self.output_dir, filename)
        data = [m.to_dict() for m in matches]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(matches)} match records to JSON: {filepath}")
        return filepath

    def export_csv(self, matches: List[DeepMatchData], filename: str = "fixtures_summary.csv") -> str:
        """
        Export flattened summary of matches and predictions to CSV.
        
        Args:
            matches: List of DeepMatchData objects
            filename: Target CSV filename
            
        Returns:
            Path to the saved CSV file.
        """
        filepath = os.path.join(self.output_dir, filename)

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
            "home_country",
            "home_world_rank",
            "away_country",
            "away_world_rank",
            "h2h_matches_count",
            "latest_h2h_date",
            "latest_h2h_score",
            "comparison_url",
        ]

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item in matches:
                fix = item.fixture
                odds = fix.odds
                votes = fix.user_votes
                h_info = item.home_team_info
                a_info = item.away_team_info
                
                latest_h2h = item.h2h_matches[0] if item.h2h_matches else None
                latest_score = ""
                latest_date = ""
                if latest_h2h:
                    latest_date = latest_h2h.date
                    if latest_h2h.home_goals is not None and latest_h2h.away_goals is not None:
                        latest_score = f"{latest_h2h.home_goals}-{latest_h2h.away_goals}"

                row = {
                    "match_id": fix.match_id,
                    "date": fix.date,
                    "time": fix.time,
                    "country": fix.country,
                    "competition": fix.competition,
                    "home_team": fix.home_team,
                    "away_team": fix.away_team,
                    "tip": fix.tip,
                    "coef_1": odds.coef_1,
                    "coef_x": odds.coef_x,
                    "coef_2": odds.coef_2,
                    "coef_ht1": odds.coef_ht1,
                    "coef_htx": odds.coef_htx,
                    "coef_ht2": odds.coef_ht2,
                    "coef_o15": odds.coef_o15,
                    "coef_o25": odds.coef_o25,
                    "coef_o35": odds.coef_o35,
                    "coef_bts": odds.coef_bts,
                    "coef_ots": odds.coef_ots,
                    "vote_1": votes.vote_1,
                    "vote_x": votes.vote_x,
                    "vote_2": votes.vote_2,
                    "likes": votes.likes,
                    "dislikes": votes.dislikes,
                    "home_country": h_info.country if h_info else "",
                    "home_world_rank": h_info.world_rank if h_info else "",
                    "away_country": a_info.country if a_info else "",
                    "away_world_rank": a_info.world_rank if a_info else "",
                    "h2h_matches_count": len(item.h2h_matches),
                    "latest_h2h_date": latest_date,
                    "latest_h2h_score": latest_score,
                    "comparison_url": fix.comparison_url,
                }
                writer.writerow(row)

        logger.info(f"Saved {len(matches)} match records to CSV: {filepath}")
        return filepath
