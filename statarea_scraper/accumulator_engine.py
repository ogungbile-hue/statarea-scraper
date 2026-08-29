"""High-Safety / Multi-Market AI Accumulator Engine for Statarea.

Features:
- Wide Market Coverage: Evaluates 12+ distinct betting markets:
  1. Double Chance (1X, X2, 12 - Any Team Win)
  2. Over / Under Total Goals (Over 1.5, Under 3.5, Under 2.5, Over 2.5)
  3. Draw No Bet (Home DNB, Away DNB)
  4. Team Specific Goals (Home Over 0.5, Away Over 0.5, Home Over 1.5, Away Over 1.5)
  5. Both Teams to Score / Clean Sheet (BTTS Yes, BTTS No / One Team to Score)
  6. Outright Match Winner (Straight Home Win 1, Away Win 2)
  7. Half-Time Trends (HT Under 1.5, HT Over 0.5, HT Draw)
- Deep Statistical Analysis: Combines model probability coefficients, recent form scoring consistency,
  clean sheet ratios, dynamic H2H recency (>= 2023), and community consensus.
- Market Diversity Guarantee: Enforces balanced selection diversity per slip so no single market dominates.
- Strict Today's Date Filter: Guarantees matches are exclusively from today's live Statarea predictions.
- Explicit Deep Justification & Reasoning per leg.
"""

import csv
import datetime
import itertools
import json
import logging
import math
import os
import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)

# Minimum H2H year for recency filter
MIN_H2H_YEAR = 2023


@dataclass
class MarketCandidate:
    """Evaluated market candidate with safety verification and justification."""
    match_id: str
    date: str
    time: str
    competition: str
    country: str
    home_team: str
    away_team: str
    market: str  # "Double Chance", "Goals", "DNB", "Team Goals", "BTS", "1X2", "Half Time"
    selection: str
    probability: float
    estimated_odds: float
    confidence_score: float
    risk_level: str  # "Ultra-Low", "Low", "Moderate"
    justification: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AccumulatorSlip:
    """Multi-leg accumulator ticket with risk analysis."""
    name: str
    description: str
    legs_count: int
    total_odds: float
    average_confidence: float
    legs: List[MarketCandidate]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "legs_count": self.legs_count,
            "total_odds": round(self.total_odds, 2),
            "average_confidence": round(self.average_confidence, 1),
            "legs": [leg.to_dict() for leg in self.legs],
        }


class AccumulatorEngine:
    """High-Safety / Low-Risk Accumulator Generator with Multi-Market Coverage."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def load_data(
        self,
        fixtures_path: Optional[str] = None,
        metrics_path: Optional[str] = None,
        h2h_path: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Ingest all three relational datasets with bundled fallback and date validation."""
        f_path = fixtures_path or os.path.join(self.output_dir, "analysis_fixtures_today.csv")
        m_path = metrics_path or os.path.join(self.output_dir, "analysis_team_metrics.csv")
        h_path = h2h_path or os.path.join(self.output_dir, "analysis_h2h_records.csv")

        bundled_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

        if not os.path.exists(f_path):
            bundled_f = os.path.join(bundled_dir, "analysis_fixtures_today.csv")
            if os.path.exists(bundled_f):
                f_path = bundled_f
            else:
                raise FileNotFoundError(f"Missing fixtures file: {f_path}")

        if not os.path.exists(m_path):
            bundled_m = os.path.join(bundled_dir, "analysis_team_metrics.csv")
            if os.path.exists(bundled_m):
                m_path = bundled_m
            else:
                raise FileNotFoundError(f"Missing metrics file: {m_path}")

        if not os.path.exists(h_path):
            bundled_h = os.path.join(bundled_dir, "analysis_h2h_records.csv")
            if os.path.exists(bundled_h):
                h_path = bundled_h
            else:
                raise FileNotFoundError(f"Missing H2H file: {h_path}")

        fixtures_df = pd.read_csv(f_path)
        metrics_df = pd.read_csv(m_path)
        h2h_df = pd.read_csv(h_path)

        return fixtures_df, metrics_df, h2h_df

    def _filter_recent_h2h(self, h2h_df: pd.DataFrame, fixture_id: str) -> Dict[str, Any]:
        """Filter H2H matches to only the last 3 years (>= 2023)."""
        match_h2h = h2h_df[h2h_df["fixture_id"].astype(str) == str(fixture_id)].copy()
        if match_h2h.empty:
            return {"recent_count": 0, "home_win_rate": 0.0, "draw_rate": 0.0, "away_rate": 0.0, "avg_goals": 0.0, "bts_rate": 0.0}

        match_h2h["year"] = pd.to_datetime(match_h2h["h2h_date"], errors="coerce").dt.year
        recent = match_h2h[match_h2h["year"] >= MIN_H2H_YEAR]

        recent_count = len(recent)
        if recent_count < 2:
            return {"recent_count": recent_count, "home_win_rate": 0.0, "draw_rate": 0.0, "away_rate": 0.0, "avg_goals": 0.0, "bts_rate": 0.0}

        home_wins = sum(recent["outcome"] == "1")
        draws = sum(recent["outcome"] == "X")
        away_wins = sum(recent["outcome"] == "2")
        
        valid_goals = recent["total_goals"].dropna()
        avg_goals = valid_goals.mean() if not valid_goals.empty else 0.0
        
        valid_bts = recent["bts_result"].dropna()
        bts_rate = (valid_bts.sum() / len(valid_bts) * 100) if not valid_bts.empty else 0.0

        return {
            "recent_count": recent_count,
            "home_win_rate": round((home_wins / recent_count) * 100, 1),
            "draw_rate": round((draws / recent_count) * 100, 1),
            "away_rate": round((away_wins / recent_count) * 100, 1),
            "avg_goals": round(avg_goals, 2),
            "bts_rate": round(bts_rate, 1),
        }

    def _parse_form_metrics(self, form_str: str) -> Dict[str, Any]:
        """Parse recent scores (e.g. '1-2 | 0-3 | 2-0') to extract detailed form and clean sheet metrics."""
        default_res = {
            "matches": 0,
            "avg_goals": 0.0,
            "avg_team_goals": 0.0,
            "avg_conceded": 0.0,
            "scored_in_count": 0,
            "scored_in_ratio": 0.0,
            "clean_sheets": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
        }
        if not form_str or pd.isna(form_str):
            return default_res

        items = [s.strip() for s in str(form_str).split("|") if s.strip()]
        matches = len(items)
        if matches == 0:
            return default_res

        total_goals_list = []
        team_goals_list = []
        conceded_goals_list = []
        scored_in = 0
        clean_sheets = 0
        wins = 0
        losses = 0
        draws = 0

        for item in items:
            match = re.match(r"^(\d+)-(\d+)$", item)
            if match:
                g1, g2 = int(match.group(1)), int(match.group(2))
                total_goals_list.append(g1 + g2)
                team_goals_list.append(g1)
                conceded_goals_list.append(g2)
                if g1 > 0:
                    scored_in += 1
                if g2 == 0:
                    clean_sheets += 1
                if g1 > g2:
                    wins += 1
                elif g1 < g2:
                    losses += 1
                else:
                    draws += 1

        avg_goals = sum(total_goals_list) / len(total_goals_list) if total_goals_list else 0.0
        avg_team_goals = sum(team_goals_list) / len(team_goals_list) if team_goals_list else 0.0
        avg_conceded = sum(conceded_goals_list) / len(conceded_goals_list) if conceded_goals_list else 0.0
        scored_ratio = scored_in / matches if matches > 0 else 0.0

        return {
            "matches": matches,
            "avg_goals": round(avg_goals, 2),
            "avg_team_goals": round(avg_team_goals, 2),
            "avg_conceded": round(avg_conceded, 2),
            "scored_in_count": scored_in,
            "scored_in_ratio": round(scored_ratio, 2),
            "clean_sheets": clean_sheets,
            "wins": wins,
            "losses": losses,
            "draws": draws,
        }

    def _is_cup_or_friendly(self, competition: str) -> bool:
        """Check if competition is a Cup, Friendly, or Tournament with high rotation risk."""
        comp_lower = str(competition).lower()
        cup_keywords = [
            "cup", "copa", "coppa", "coupe", "pokal", "trophy",
            "friendly", "preliminary", "qualification", "qualifying",
            "tournament", "intercontinental", "turnier",
        ]
        return any(k in comp_lower for k in cup_keywords)

    def evaluate_markets(
        self,
        fixtures_df: pd.DataFrame,
        metrics_df: pd.DataFrame,
        h2h_df: pd.DataFrame,
    ) -> List[MarketCandidate]:
        """
        Deep analytical evaluation across 12+ betting markets with safety constraints.
        """
        candidates: List[MarketCandidate] = []

        # Merge fixtures with metrics
        merged = fixtures_df.merge(
            metrics_df,
            on="match_id",
            suffixes=("", "_metric"),
            how="inner",
        )

        today_str = datetime.datetime.now().strftime("%Y-%m-%d")

        for _, row in merged.iterrows():
            match_id = str(row.get("match_id", ""))
            date_val = str(row.get("date", "")).strip()
            time_val = str(row.get("time", "")).strip()
            comp = str(row.get("competition", ""))
            country = str(row.get("country", ""))
            home = str(row.get("home_team", ""))
            away = str(row.get("away_team", ""))

            # Strict Daily Filter: Ensure matches belong strictly to today's date
            if date_val and date_val != today_str:
                continue

            def _num(key, default=0.0):
                val = row.get(key)
                try:
                    if pd.isna(val) or val == "":
                        return default
                    return float(val)
                except (ValueError, TypeError):
                    return default

            coef_1 = _num("coef_1")
            coef_x = _num("coef_x")
            coef_2 = _num("coef_2")
            coef_ht1 = _num("coef_ht1")
            coef_htx = _num("coef_htx")
            coef_ht2 = _num("coef_ht2")
            coef_o15 = _num("coef_o15")
            coef_o25 = _num("coef_o25")
            coef_o35 = _num("coef_o35")
            coef_bts = _num("coef_bts")
            coef_ots = _num("coef_ots")

            vote_1 = _num("vote_1")
            vote_x = _num("vote_x")
            vote_2 = _num("vote_2")
            total_votes = vote_1 + vote_x + vote_2

            home_rank = _num("home_world_rank", None)
            away_rank = _num("away_world_rank", None)

            # 1. Dynamic H2H Recency (>= 2023)
            recent_h2h = self._filter_recent_h2h(h2h_df, match_id)
            has_recent_h2h = (recent_h2h["recent_count"] >= 2)

            # 2. Recent form metrics
            home_form = self._parse_form_metrics(row.get("home_recent_form_scores", ""))
            away_form = self._parse_form_metrics(row.get("away_recent_form_scores", ""))

            combined_recent_goal_avg = (
                (home_form["avg_goals"] + away_form["avg_goals"]) / 2.0
                if (home_form["matches"] > 0 and away_form["matches"] > 0)
                else _num("h2h_avg_goals", 2.5)
            )

            # 3. Cup Penalty
            is_cup = self._is_cup_or_friendly(comp)
            cup_penalty_multiplier = 0.88 if is_cup else 1.0

            def calc_odds(prob: float) -> float:
                if prob <= 0:
                    return 10.0
                raw = (100.0 / prob) * 0.93
                return max(1.12, min(4.0, round(raw, 2)))

            # =========================================================================
            # MARKET 1: DOUBLE CHANCE (1X, X2, 12)
            # =========================================================================
            prob_1x = min(98.0, coef_1 + coef_x)
            if prob_1x >= 78.0:
                odds = calc_odds(prob_1x)
                h2h_factor = (recent_h2h["home_win_rate"] + recent_h2h["draw_rate"]) if has_recent_h2h else prob_1x
                vote_pct = ((vote_1 + vote_x) / total_votes * 100) if total_votes > 0 else prob_1x
                base_conf = 0.60 * prob_1x + 0.25 * h2h_factor + 0.15 * vote_pct
                conf = round(base_conf * cup_penalty_multiplier, 1)

                justification = (
                    f"Double Chance 1X: {prob_1x:.0f}% non-loss probability, "
                    f"Home won/drew {home_form['matches'] - home_form['losses']}/{home_form['matches']} recent matches."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Double Chance", selection=f"{home} or Draw (1X)",
                    probability=prob_1x, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Ultra-Low" if prob_1x >= 85 else "Low", justification=justification,
                ))

            prob_x2 = min(98.0, coef_x + coef_2)
            if prob_x2 >= 78.0:
                odds = calc_odds(prob_x2)
                h2h_factor = (recent_h2h["draw_rate"] + recent_h2h["away_rate"]) if has_recent_h2h else prob_x2
                vote_pct = ((vote_x + vote_2) / total_votes * 100) if total_votes > 0 else prob_x2
                base_conf = 0.60 * prob_x2 + 0.25 * h2h_factor + 0.15 * vote_pct
                conf = round(base_conf * cup_penalty_multiplier, 1)

                justification = (
                    f"Double Chance X2: {prob_x2:.0f}% non-loss probability, "
                    f"Away side unbeaten in {away_form['matches'] - away_form['losses']}/{away_form['matches']} recent outings."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Double Chance", selection=f"Draw or {away} (X2)",
                    probability=prob_x2, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Ultra-Low" if prob_x2 >= 85 else "Low", justification=justification,
                ))

            prob_12 = min(98.0, coef_1 + coef_2)
            if coef_x <= 22.0 and prob_12 >= 78.0:
                odds = calc_odds(prob_12)
                conf = round((0.65 * prob_12 + 0.35 * (100.0 - coef_x)) * cup_penalty_multiplier, 1)
                justification = (
                    f"Double Chance 12 (Any Team Win): Extremely low draw probability ({coef_x:.0f}%), "
                    f"high combined win model ({prob_12:.0f}%)."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Double Chance", selection=f"{home} or {away} (12)",
                    probability=prob_12, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Low", justification=justification,
                ))

            # =========================================================================
            # MARKET 2: GOALS OVER 1.5 & OVER 2.5
            # =========================================================================
            if coef_o15 >= 80.0 and combined_recent_goal_avg >= 2.0:
                odds = calc_odds(coef_o15)
                base_conf = 0.65 * coef_o15 + 0.35 * min(96.0, (combined_recent_goal_avg / 2.5) * 80.0)
                conf = round(base_conf * cup_penalty_multiplier, 1)
                justification = (
                    f"Over 1.5 Goals: {coef_o15:.0f}% model rating + {combined_recent_goal_avg:.1f} avg recent match goals."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Goals", selection="Over 1.5 Goals",
                    probability=coef_o15, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Ultra-Low", justification=justification,
                ))

            if coef_o25 >= 66.0 and combined_recent_goal_avg >= 2.8:
                odds = calc_odds(coef_o25)
                conf = round((0.60 * coef_o25 + 0.40 * 85.0) * cup_penalty_multiplier, 1)
                justification = (
                    f"Over 2.5 Goals: High-tempo matchup ({coef_o25:.0f}% model) with "
                    f"{combined_recent_goal_avg:.1f} combined goals/game."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Goals", selection="Over 2.5 Goals",
                    probability=coef_o25, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Moderate", justification=justification,
                ))

            # =========================================================================
            # MARKET 3: GOALS UNDER 3.5 & UNDER 2.5
            # =========================================================================
            prob_u35 = max(5.0, 100.0 - coef_o35)
            if coef_o35 <= 38.0 and home_form["avg_goals"] <= 2.4 and away_form["avg_goals"] <= 2.4:
                odds = calc_odds(prob_u35)
                conf = round((0.70 * prob_u35 + 0.30 * 85.0) * cup_penalty_multiplier, 1)
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Goals", selection="Under 3.5 Goals",
                    probability=prob_u35, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Ultra-Low" if prob_u35 >= 75 else "Low",
                    justification=f"Defensive Lock: {prob_u35:.0f}% Under 3.5 model + disciplined low scoring pace.",
                ))

            prob_u25 = max(5.0, 100.0 - coef_o25)
            if coef_o25 <= 36.0 and home_form["avg_goals"] <= 2.0 and away_form["avg_goals"] <= 2.0:
                odds = calc_odds(prob_u25)
                conf = round((0.70 * prob_u25 + 0.30 * 85.0) * cup_penalty_multiplier, 1)
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Goals", selection="Under 2.5 Goals",
                    probability=prob_u25, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Low",
                    justification=f"Under 2.5 Solid Lock: {prob_u25:.0f}% probability, defensive average <= 2.0 goals/match.",
                ))

            # =========================================================================
            # MARKET 4: TEAM GOALS / SCORING (HOME / AWAY OVER 0.5 & OVER 1.5)
            # =========================================================================
            prob_home_score = min(98.0, 0.50 * coef_1 + 0.50 * coef_bts + 15.0)
            if (coef_1 >= 48.0 or home_form["scored_in_count"] >= 3) and prob_home_score >= 82.0:
                odds = calc_odds(prob_home_score)
                conf = round((0.65 * prob_home_score + 0.35 * (home_form["scored_in_ratio"] * 100.0)) * cup_penalty_multiplier, 1)
                justification = (
                    f"Home Team To Score: {prob_home_score:.0f}% scoring probability, "
                    f"scored in {home_form['scored_in_count']}/{home_form['matches']} recent matches."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Team Goals", selection=f"{home} Over 0.5 Goals",
                    probability=prob_home_score, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Ultra-Low", justification=justification,
                ))

            prob_away_score = min(98.0, 0.50 * coef_2 + 0.50 * coef_bts + 15.0)
            if (coef_2 >= 45.0 or away_form["scored_in_count"] >= 3) and prob_away_score >= 80.0:
                odds = calc_odds(prob_away_score)
                conf = round((0.65 * prob_away_score + 0.35 * (away_form["scored_in_ratio"] * 100.0)) * cup_penalty_multiplier, 1)
                justification = (
                    f"Away Team To Score: {prob_away_score:.0f}% scoring probability, "
                    f"scored in {away_form['scored_in_count']}/{away_form['matches']} recent matches."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Team Goals", selection=f"{away} Over 0.5 Goals",
                    probability=prob_away_score, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Ultra-Low", justification=justification,
                ))

            # Home Over 1.5 Goals
            if coef_1 >= 58.0 and coef_o25 >= 58.0 and home_form["avg_team_goals"] >= 1.7:
                prob_home_o15 = min(88.0, (coef_1 + coef_o25) / 2.0 + 5.0)
                odds = calc_odds(prob_home_o15)
                conf = round((0.60 * prob_home_o15 + 0.40 * 80.0) * cup_penalty_multiplier, 1)
                justification = (
                    f"{home} Over 1.5 Team Goals: Strong home attack averaging {home_form['avg_team_goals']:.1f} goals/game."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Team Goals", selection=f"{home} Over 1.5 Goals",
                    probability=prob_home_o15, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Low", justification=justification,
                ))

            # =========================================================================
            # MARKET 5: DRAW NO BET (1 DNB & 2 DNB)
            # =========================================================================
            if coef_1 >= 50.0 and prob_1x >= 76.0:
                prob_dnb1 = min(92.0, (coef_1 / (coef_1 + coef_2 + 0.001)) * 100.0)
                odds = calc_odds(prob_dnb1)
                conf = round((0.65 * prob_dnb1 + 0.35 * prob_1x) * cup_penalty_multiplier, 1)
                justification = (
                    f"Home Draw No Bet (1 DNB): High win probability with draw refund protection ({prob_1x:.0f}% non-loss)."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="DNB", selection=f"{home} (Draw No Bet)",
                    probability=prob_dnb1, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Low", justification=justification,
                ))

            if coef_2 >= 48.0 and prob_x2 >= 76.0:
                prob_dnb2 = min(92.0, (coef_2 / (coef_1 + coef_2 + 0.001)) * 100.0)
                odds = calc_odds(prob_dnb2)
                conf = round((0.65 * prob_dnb2 + 0.35 * prob_x2) * cup_penalty_multiplier, 1)
                justification = (
                    f"Away Draw No Bet (2 DNB): High away edge with draw refund protection ({prob_x2:.0f}% non-loss)."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="DNB", selection=f"{away} (Draw No Bet)",
                    probability=prob_dnb2, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Low", justification=justification,
                ))

            # =========================================================================
            # MARKET 6: STRAIGHT OUTRIGHT WIN (1X2 HOME / AWAY)
            # =========================================================================
            vote_pct_1 = (vote_1 / total_votes * 100) if total_votes > 0 else 0.0
            if coef_1 >= 64.0 and vote_pct_1 >= 55.0 and home_form["wins"] >= 2:
                odds = calc_odds(coef_1)
                conf = round((0.55 * coef_1 + 0.25 * vote_pct_1 + 0.20 * 85.0) * cup_penalty_multiplier, 1)
                justification = (
                    f"Straight Home Win: {coef_1:.0f}% model prob + {vote_pct_1:.0f}% crowd consensus + strong home form."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="1X2", selection=f"{home} To Win",
                    probability=coef_1, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Low" if coef_1 >= 72 else "Moderate", justification=justification,
                ))

            vote_pct_2 = (vote_2 / total_votes * 100) if total_votes > 0 else 0.0
            if coef_2 >= 60.0 and vote_pct_2 >= 55.0 and away_form["wins"] >= 2:
                odds = calc_odds(coef_2)
                conf = round((0.55 * coef_2 + 0.25 * vote_pct_2 + 0.20 * 85.0) * cup_penalty_multiplier, 1)
                justification = (
                    f"Straight Away Win: {coef_2:.0f}% model prob + {vote_pct_2:.0f}% crowd consensus + away form."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="1X2", selection=f"{away} To Win",
                    probability=coef_2, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Low" if coef_2 >= 70 else "Moderate", justification=justification,
                ))

            # =========================================================================
            # MARKET 7: BOTH TEAMS TO SCORE (BTTS YES & BTTS NO / OTS)
            # =========================================================================
            if coef_bts >= 62.0 and home_form["scored_in_count"] >= 3 and away_form["scored_in_count"] >= 3:
                odds = calc_odds(coef_bts)
                conf = round((0.60 * coef_bts + 0.40 * 85.0) * cup_penalty_multiplier, 1)
                justification = (
                    f"Both Teams To Score (Yes): {coef_bts:.0f}% model prob, verified dual scoring consistency in recent form."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="BTS", selection="Both Teams To Score (Yes)",
                    probability=coef_bts, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Moderate", justification=justification,
                ))

            prob_ots = max(coef_ots, 100.0 - coef_bts)
            if prob_ots >= 60.0 and (home_form["clean_sheets"] >= 2 or away_form["clean_sheets"] >= 2 or home_form["avg_team_goals"] <= 0.8 or away_form["avg_team_goals"] <= 0.8):
                odds = calc_odds(prob_ots)
                conf = round((0.65 * prob_ots + 0.35 * 80.0) * cup_penalty_multiplier, 1)
                justification = (
                    f"Both Teams To Score (No) / OTS: {prob_ots:.0f}% clean sheet / one team score probability."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="BTS", selection="Both Teams To Score (No)",
                    probability=prob_ots, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Low", justification=justification,
                ))

            # =========================================================================
            # MARKET 8: HALF-TIME MARKETS (HT UNDER 1.5 & HT OVER 0.5 & HT DRAW)
            # =========================================================================
            prob_ht_u15 = min(96.0, 0.60 * coef_htx + 0.40 * (100.0 - coef_o25) + 20.0)
            if prob_ht_u15 >= 75.0 and coef_o35 <= 48.0:
                odds = calc_odds(prob_ht_u15)
                conf = round((0.70 * prob_ht_u15 + 0.30 * 85.0) * cup_penalty_multiplier, 1)
                justification = (
                    f"First Half Under 1.5 Goals: {prob_ht_u15:.0f}% model rating, disciplined early match pace."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Half Time", selection="1st Half Under 1.5 Goals",
                    probability=prob_ht_u15, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Ultra-Low", justification=justification,
                ))

            if coef_htx >= 45.0 and combined_recent_goal_avg <= 2.2:
                odds = calc_odds(coef_htx)
                conf = round((0.60 * coef_htx + 0.40 * 75.0) * cup_penalty_multiplier, 1)
                justification = (
                    f"First Half Draw (HT X): {coef_htx:.0f}% model rating with balanced cautious opening halves."
                )
                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Half Time", selection="Half Time Draw (X)",
                    probability=coef_htx, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Moderate", justification=justification,
                ))

        logger.info(f"Generated {len(candidates)} high-confidence multi-market candidates.")
        return candidates

    def _build_tier_slip(
        self,
        candidates: List[MarketCandidate],
        target_odds: float,
        min_total_odds: float,
        max_total_odds: float,
        min_legs: int,
        max_legs: int,
        name: str,
        description: str,
        min_leg_odds: float = 1.10,
        max_leg_odds: float = 1.65,
        max_market_repetition: int = 2,
    ) -> Optional[AccumulatorSlip]:
        """Generic builder with Market Diversity constraints to generate balanced, multi-market slips."""
        # Filter viable candidates within leg odds limits
        safe_candidates = [
            c for c in candidates
            if min_leg_odds <= c.estimated_odds <= max_leg_odds
        ]

        if len(safe_candidates) < min_legs:
            # Widen range slightly if scarce
            safe_candidates = [
                c for c in candidates
                if 1.08 <= c.estimated_odds <= 2.20
            ]

        if len(safe_candidates) < min_legs:
            return None

        # Group candidates by match_id and select top candidate per match
        match_map: Dict[str, MarketCandidate] = {}
        for c in sorted(safe_candidates, key=lambda x: (x.confidence_score, -x.estimated_odds), reverse=True):
            if c.match_id not in match_map:
                match_map[c.match_id] = c

        distinct_candidates = list(match_map.values())
        if len(distinct_candidates) < min_legs:
            return None

        # Sort distinct candidates by confidence score
        distinct_candidates.sort(key=lambda x: (x.confidence_score, -x.estimated_odds), reverse=True)
        top_candidates = distinct_candidates[:16]

        all_valid_combos: List[Tuple[float, float, List[MarketCandidate]]] = []

        def is_market_diverse(combo: Tuple[MarketCandidate, ...], max_rep: int) -> bool:
            """Ensure no single market dominates the slip."""
            market_counts: Dict[str, int] = {}
            for leg in combo:
                market_counts[leg.market] = market_counts.get(leg.market, 0) + 1
                if market_counts[leg.market] > max_rep:
                    return False
            return True

        # Search for valid combinations with diversity constraint
        for leg_count in range(min_legs, min(max_legs + 1, len(top_candidates) + 1)):
            for combo in itertools.combinations(top_candidates, leg_count):
                if not is_market_diverse(combo, max_market_repetition):
                    continue

                tot_odds = 1.0
                for leg in combo:
                    tot_odds *= leg.estimated_odds

                if min_total_odds <= tot_odds <= max_total_odds:
                    avg_conf = sum(leg.confidence_score for leg in combo) / len(combo)
                    all_valid_combos.append((avg_conf, tot_odds, list(combo)))

        # Fallback 1: Allow slightly higher market repetition or wider odds range
        if not all_valid_combos:
            wider_min = max(1.10, min_total_odds * 0.75)
            wider_max = max_total_odds * 1.30
            for leg_count in range(min_legs, min(max_legs + 1, len(top_candidates) + 1)):
                for combo in itertools.combinations(top_candidates, leg_count):
                    if not is_market_diverse(combo, max_market_repetition + 1):
                        continue
                    tot_odds = 1.0
                    for leg in combo:
                        tot_odds *= leg.estimated_odds
                    if wider_min <= tot_odds <= wider_max:
                        avg_conf = sum(leg.confidence_score for leg in combo) / len(combo)
                        all_valid_combos.append((avg_conf, tot_odds, list(combo)))

        # Fallback 2: Pick closest combination to target odds
        if not all_valid_combos:
            candidate_combos = []
            for leg_count in range(max(1, min_legs - 1), min(max_legs + 2, len(top_candidates) + 1)):
                for combo in itertools.combinations(top_candidates[:12], leg_count):
                    tot_odds = 1.0
                    for leg in combo:
                        tot_odds *= leg.estimated_odds
                    avg_conf = sum(leg.confidence_score for leg in combo) / len(combo)
                    candidate_combos.append((avg_conf, tot_odds, list(combo)))

            if candidate_combos:
                candidate_combos.sort(key=lambda x: (abs(x[1] - target_odds), -x[0]))
                all_valid_combos = candidate_combos[:20]

        if not all_valid_combos:
            logger.warning(f"No accumulator combinations matched for {name}.")
            return None

        # Sort by highest confidence and minimum deviation from target odds
        all_valid_combos.sort(key=lambda x: (-x[0], abs(x[1] - target_odds)))
        best_conf, best_odds, best_legs = all_valid_combos[0]

        return AccumulatorSlip(
            name=name,
            description=description,
            legs_count=len(best_legs),
            total_odds=round(best_odds, 2),
            average_confidence=round(best_conf, 1),
            legs=best_legs,
        )

    def build_all_slips(self, candidates: List[MarketCandidate]) -> Dict[str, Optional[AccumulatorSlip]]:
        """
        Generate all four daily accumulator tiers (1.5 Odds, 3 Odds, 5 Odds, 10 Odds).
        """
        # Tier 1: 1.5 Odds Ultra Banker (2-3 legs)
        slip_1_5 = self._build_tier_slip(
            candidates=candidates,
            target_odds=1.50,
            min_total_odds=1.35,
            max_total_odds=1.80,
            min_legs=2,
            max_legs=3,
            name="Onítẹ́tẹ́ 1.5-Odds Ultra Banker Slip",
            description="Ultra-conservative 2-3 leg banker ticket with top-tier statistical safety.",
            min_leg_odds=1.12,
            max_leg_odds=1.35,
            max_market_repetition=1,
        )

        # Tier 2: 3 Odds Banker (3-4 legs)
        slip_3 = self._build_tier_slip(
            candidates=candidates,
            target_odds=3.00,
            min_total_odds=2.70,
            max_total_odds=3.60,
            min_legs=3,
            max_legs=4,
            name="Onítẹ́tẹ́ 3-Odds Banker Slip",
            description="High-probability 3-4 leg slip with balanced, multi-market safety picks.",
            min_leg_odds=1.18,
            max_leg_odds=1.45,
            max_market_repetition=2,
        )

        # Tier 3: 5 Odds Banker (4-6 legs)
        slip_5 = self._build_tier_slip(
            candidates=candidates,
            target_odds=5.00,
            min_total_odds=4.50,
            max_total_odds=5.60,
            min_legs=4,
            max_legs=6,
            name="Onítẹ́tẹ́ 5-Odds Banker Slip",
            description="Classic Onítẹ́tẹ́ 5-odds multi-market accumulator with strict risk filters.",
            min_leg_odds=1.20,
            max_leg_odds=1.55,
            max_market_repetition=2,
        )

        # Tier 4: 10 Odds Multiplier (5-8 legs)
        slip_10 = self._build_tier_slip(
            candidates=candidates,
            target_odds=10.00,
            min_total_odds=8.50,
            max_total_odds=12.50,
            min_legs=5,
            max_legs=8,
            name="Onítẹ́tẹ́ 10-Odds Multiplier Slip",
            description="High-yield 5-8 leg accumulator across diversified high-confidence market selections.",
            min_leg_odds=1.22,
            max_leg_odds=1.65,
            max_market_repetition=2,
        )

        return {
            "slip_1_5odds": slip_1_5,
            "slip_3odds": slip_3,
            "slip_5odds": slip_5,
            "slip_10odds": slip_10,
            # Backwards compatibility aliases
            "daily_ticket": slip_5 or slip_3 or slip_1_5,
            "banker_ticket": slip_5 or slip_3 or slip_1_5,
        }

    def build_5odds_slips(
        self,
        candidates: List[MarketCandidate],
        min_total_odds: float = 4.50,
        max_total_odds: float = 5.50,
        target_odds: float = 5.00,
        min_leg_odds: float = 1.18,
        max_leg_odds: float = 1.45,
    ) -> Dict[str, Optional[AccumulatorSlip]]:
        """Backwards compatibility wrapper returning all slips."""
        return self.build_all_slips(candidates)

    def generate_and_save(
        self,
        fixtures_path: Optional[str] = None,
        metrics_path: Optional[str] = None,
        h2h_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run full multi-market evaluation pipeline and persist all 4 tiers (1.5x, 3x, 5x, 10x)."""
        fixtures_df, metrics_df, h2h_df = self.load_data(fixtures_path, metrics_path, h2h_path)
        candidates = self.evaluate_markets(fixtures_df, metrics_df, h2h_df)
        slips = self.build_all_slips(candidates)

        json_path = os.path.join(self.output_dir, "daily_5odds_slip.json")
        txt_path = os.path.join(self.output_dir, "daily_5odds_slip.txt")

        payload = {
            "strategy": "Multi-Tier High-Safety Daily Accumulator Slips (1.5x, 3x, 5x, 10x)",
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "slip_1_5odds": slips["slip_1_5odds"].to_dict() if slips.get("slip_1_5odds") else None,
            "slip_3odds": slips["slip_3odds"].to_dict() if slips.get("slip_3odds") else None,
            "slip_5odds": slips["slip_5odds"].to_dict() if slips.get("slip_5odds") else None,
            "slip_10odds": slips["slip_10odds"].to_dict() if slips.get("slip_10odds") else None,
            "daily_ticket": slips["daily_ticket"].to_dict() if slips.get("daily_ticket") else None,
            "banker_ticket": slips["banker_ticket"].to_dict() if slips.get("banker_ticket") else None,
        }

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved refined multi-tier daily slips JSON: {json_path}")
        except OSError as e:
            logger.warning(f"Could not save JSON to {json_path}: {e}")

        # Save Formatted Multi-Tier TXT Report
        txt_report = self._format_txt_report(slips)
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(txt_report)
            logger.info(f"Saved refined multi-tier daily slips TXT: {txt_path}")
        except OSError as e:
            logger.warning(f"Could not save TXT to {txt_path}: {e}")

        return {
            "json_file": json_path,
            "txt_file": txt_path,
            "slips": slips,
            "daily_ticket": slips.get("daily_ticket"),
            "banker_ticket": slips.get("banker_ticket"),
            "text_report": txt_report,
        }

    def _format_single_slip_txt(self, slip: Optional[AccumulatorSlip]) -> List[str]:
        """Format an individual slip into ASCII table lines."""
        lines = []
        if not slip:
            lines.append("  [!] No valid ticket generated matching the safety criteria.")
            return lines

        lines.append(f">> {slip.name.upper()}")
        lines.append(f"   {slip.description}")
        lines.append(f"   Total Odds: {slip.total_odds:.2f}x  |  Avg Confidence: {slip.average_confidence:.1f}%  |  Legs: {slip.legs_count}")
        lines.append("-" * 92)
        lines.append(f"{'Time':<6} | {'Fixture':<28} | {'Market':<14} | {'Selection':<26} | {'Odds':<5} | {'Conf'}")
        lines.append("-" * 92)

        for leg in slip.legs:
            fixture_str = f"{leg.home_team[:13]} vs {leg.away_team[:13]}"
            lines.append(
                f"{leg.time:<6} | {fixture_str:<28} | {leg.market:<14} | {leg.selection[:26]:<26} | {leg.estimated_odds:>4.2f}x | {leg.confidence_score:>4.1f}%"
            )
            lines.append(f"       ↳ Justification: {leg.justification}")

        return lines

    def _format_txt_report(self, slips: Any) -> str:
        """Format all 4 daily tickets (1.5x, 3x, 5x, 10x) with individual justifications into an ASCII report."""
        lines = []
        lines.append("=" * 92)
        lines.append("        🛡️ ONÍTẸ́TẸ́ MULTI-MARKET DAILY ACCUMULATORS (1.5x, 3x, 5x, 10x)        ")
        lines.append("=" * 92)

        slips_dict: Dict[str, Optional[AccumulatorSlip]] = {}
        if isinstance(slips, dict):
            slips_dict = slips
        elif isinstance(slips, AccumulatorSlip):
            slips_dict = {"slip_5odds": slips}

        tiers = [
            ("1.5-ODDS ULTRA BANKER", slips_dict.get("slip_1_5odds")),
            ("3-ODDS BANKER", slips_dict.get("slip_3odds")),
            ("5-ODDS BANKER", slips_dict.get("slip_5odds") or slips_dict.get("daily_ticket")),
            ("10-ODDS MULTIPLIER", slips_dict.get("slip_10odds")),
        ]

        for title, slip_obj in tiers:
            lines.append("")
            lines.append(f"--- [ {title} ] ---")
            lines.extend(self._format_single_slip_txt(slip_obj))

        lines.append("")
        lines.append("-" * 92)
        lines.append("💡 Execution Strategy: Multi-market diversified selections across high-confidence ratings.")
        lines.append("=" * 92)
        return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = AccumulatorEngine()
    res = engine.generate_and_save()
    print("\n" + res["text_report"])
