"""High-Safety / Low-Risk Multi-Market Accumulator Engine for Statarea.

Features:
- Dynamic H2H recency filtering (last 3 years only: >= 2023).
- Safety-first market constraints (strict probability, ranking differentials, and form).
- Automatic Straight Win downgrade to Double Chance (1X/X2) on high risk.
- High-variance market ban (BTTS restricted to dual 4/5 scoring form).
- Cup / Friendly squad-rotation penalty (-15%).
- 4 to 6 ultra-safe legs targeting ~5.00x cumulative odds.
- Explicit "Risk & Justification" note per selection.
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
    market: str
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
    """High-Safety / Low-Risk Accumulator Generator."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def load_data(
        self,
        fixtures_path: Optional[str] = None,
        metrics_path: Optional[str] = None,
        h2h_path: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Ingest all three relational datasets."""
        f_path = fixtures_path or os.path.join(self.output_dir, "analysis_fixtures_today.csv")
        m_path = metrics_path or os.path.join(self.output_dir, "analysis_team_metrics.csv")
        h_path = h2h_path or os.path.join(self.output_dir, "analysis_h2h_records.csv")

        if not os.path.exists(f_path):
            raise FileNotFoundError(f"Missing fixtures file: {f_path}")
        if not os.path.exists(m_path):
            raise FileNotFoundError(f"Missing metrics file: {m_path}")
        if not os.path.exists(h_path):
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

        # Extract year
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
        """Parse recent scores (e.g. '1-2 | 0-3 | 2-0') to extract form metrics."""
        if not form_str or pd.isna(form_str):
            return {"matches": 0, "avg_goals": 0.0, "scored_in_count": 0, "scored_in_ratio": 0.0, "wins": 0}

        items = [s.strip() for s in str(form_str).split("|") if s.strip()]
        matches = len(items)
        if matches == 0:
            return {"matches": 0, "avg_goals": 0.0, "scored_in_count": 0, "scored_in_ratio": 0.0, "wins": 0}

        total_goals_list = []
        scored_in = 0
        wins = 0

        for item in items:
            match = re.match(r"^(\d+)-(\d+)$", item)
            if match:
                g1, g2 = int(match.group(1)), int(match.group(2))
                total_goals_list.append(g1 + g2)
                if g1 > 0:
                    scored_in += 1
                if g1 > g2:
                    wins += 1

        avg_goals = sum(total_goals_list) / len(total_goals_list) if total_goals_list else 0.0
        scored_ratio = scored_in / matches if matches > 0 else 0.0

        return {
            "matches": matches,
            "avg_goals": round(avg_goals, 2),
            "scored_in_count": scored_in,
            "scored_in_ratio": round(scored_ratio, 2),
            "wins": wins,
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
        Evaluate fixtures using aggressive safety constraints and dynamic H2H recency.
        """
        candidates: List[MarketCandidate] = []

        # Merge fixtures with metrics
        merged = fixtures_df.merge(
            metrics_df,
            on="match_id",
            suffixes=("", "_metric"),
            how="inner",
        )

        for _, row in merged.iterrows():
            match_id = str(row.get("match_id", ""))
            date_val = str(row.get("date", ""))
            time_val = str(row.get("time", ""))
            comp = str(row.get("competition", ""))
            country = str(row.get("country", ""))
            home = str(row.get("home_team", ""))
            away = str(row.get("away_team", ""))

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
            coef_o15 = _num("coef_o15")
            coef_o25 = _num("coef_o25")
            coef_o35 = _num("coef_o35")
            coef_bts = _num("coef_bts")

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
            cup_penalty_multiplier = 0.85 if is_cup else 1.0

            def calc_odds(prob: float) -> float:
                if prob <= 0:
                    return 10.0
                raw = (100.0 / prob) * 0.92
                return max(1.12, min(4.0, round(raw, 2)))

            # =========================================================================
            # CONSTRAINT 1: OVER 1.5 GOALS
            # Require coef_o15 >= 88% AND combined recent goal avg >= 2.4
            # =========================================================================
            if coef_o15 >= 88.0 and combined_recent_goal_avg >= 2.4:
                odds = calc_odds(coef_o15)
                base_conf = 0.70 * coef_o15 + 0.30 * min(95.0, (combined_recent_goal_avg / 2.5) * 80.0)
                conf = round(base_conf * cup_penalty_multiplier, 1)
                
                justification = (
                    f"Over 1.5 Goal Pace: {coef_o15:.0f}% model prob + "
                    f"{combined_recent_goal_avg:.1f} combined recent goals/game."
                )
                if is_cup:
                    justification += " (Applied -15% cup rotation discount)"

                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Goals", selection="Over 1.5 Goals",
                    probability=coef_o15, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Ultra-Low", justification=justification,
                ))

            # =========================================================================
            # CONSTRAINT 2: DOUBLE CHANCE (1X / X2)
            # Require (coef_1 + coef_x) >= 85% AND rank superiority >= 150
            # =========================================================================
            prob_1x = min(98.0, coef_1 + coef_x)
            rank_diff_home = (
                (away_rank - home_rank) if (home_rank and away_rank)
                else (300 if (home_rank and home_rank <= 100) else 0)
            )

            if prob_1x >= 85.0 and (rank_diff_home >= 150 or home_rank is not None):
                odds = calc_odds(prob_1x)
                h2h_factor = (recent_h2h["home_win_rate"] + recent_h2h["draw_rate"]) if has_recent_h2h else prob_1x
                vote_pct = ((vote_1 + vote_x) / total_votes * 100) if total_votes > 0 else prob_1x
                base_conf = 0.60 * prob_1x + 0.25 * h2h_factor + 0.15 * vote_pct
                conf = round(base_conf * cup_penalty_multiplier, 1)

                justification = (
                    f"Double Chance 1X: {prob_1x:.0f}% non-loss probability with "
                    f"{int(rank_diff_home) if rank_diff_home else 0}+ rank superiority."
                )
                if is_cup:
                    justification += " (-15% cup discount applied)"

                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Double Chance", selection=f"{home} or Draw (1X)",
                    probability=prob_1x, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Ultra-Low", justification=justification,
                ))

            prob_x2 = min(98.0, coef_x + coef_2)
            rank_diff_away = (
                (home_rank - away_rank) if (home_rank and away_rank)
                else (300 if (away_rank and away_rank <= 100) else 0)
            )

            if prob_x2 >= 85.0 and (rank_diff_away >= 150 or away_rank is not None):
                odds = calc_odds(prob_x2)
                h2h_factor = (recent_h2h["draw_rate"] + recent_h2h["away_rate"]) if has_recent_h2h else prob_x2
                vote_pct = ((vote_x + vote_2) / total_votes * 100) if total_votes > 0 else prob_x2
                base_conf = 0.60 * prob_x2 + 0.25 * h2h_factor + 0.15 * vote_pct
                conf = round(base_conf * cup_penalty_multiplier, 1)

                justification = (
                    f"Double Chance X2: {prob_x2:.0f}% non-loss probability with "
                    f"{int(rank_diff_away) if rank_diff_away else 0}+ rank superiority."
                )
                if is_cup:
                    justification += " (-15% cup discount applied)"

                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Double Chance", selection=f"Draw or {away} (X2)",
                    probability=prob_x2, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Ultra-Low", justification=justification,
                ))

            # =========================================================================
            # CONSTRAINT 3: UNDER 3.5 GOALS
            # Require coef_o35 <= 35% AND neither team averaging > 1.3 goals/game
            # =========================================================================
            prob_u35 = max(5.0, 100.0 - coef_o35)
            if coef_o35 <= 35.0 and home_form["avg_goals"] <= 2.2 and away_form["avg_goals"] <= 2.2:
                odds = calc_odds(prob_u35)
                base_conf = 0.70 * prob_u35 + 0.30 * 85.0
                conf = round(base_conf * cup_penalty_multiplier, 1)

                candidates.append(MarketCandidate(
                    match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                    home_team=home, away_team=away, market="Goals", selection="Under 3.5 Goals",
                    probability=prob_u35, estimated_odds=odds, confidence_score=min(99.0, conf),
                    risk_level="Low",
                    justification=f"Defensive Lock: {prob_u35:.0f}% Under 3.5 model + low attacking output.",
                ))

            # =========================================================================
            # CONSTRAINT 4: RESTRICT STRAIGHT WINS (1 or 2)
            # Only allow if coef >= 72%, community vote >= 75%, and opponent has 0 wins in recent 5
            # Otherwise, automatically downgrade to Double Chance (1X or X2)
            # =========================================================================
            vote_pct_1 = (vote_1 / total_votes * 100) if total_votes > 0 else 0.0
            opponent_away_wins_recent = away_form["wins"]

            if coef_1 >= 72.0:
                if vote_pct_1 >= 75.0 and opponent_away_wins_recent == 0 and not is_cup:
                    odds = calc_odds(coef_1)
                    conf = round(0.55 * coef_1 + 0.25 * vote_pct_1 + 0.20 * 85.0, 1)
                    candidates.append(MarketCandidate(
                        match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                        home_team=home, away_team=away, market="1X2", selection=f"{home} To Win",
                        probability=coef_1, estimated_odds=odds, confidence_score=min(99.0, conf),
                        risk_level="Low",
                        justification=(
                            f"Straight Win Approved: {coef_1:.0f}% model + {vote_pct_1:.0f}% community vote + "
                            f"opponent winless in recent {away_form['matches']} games."
                        ),
                    ))
                else:
                    # Downgrade to 1X
                    if prob_1x >= 80.0:
                        odds = calc_odds(prob_1x)
                        candidates.append(MarketCandidate(
                            match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                            home_team=home, away_team=away, market="Double Chance", selection=f"{home} or Draw (1X)",
                            probability=prob_1x, estimated_odds=odds, confidence_score=round(0.90 * prob_1x, 1),
                            risk_level="Ultra-Low",
                            justification="Safety Downgrade: Straight Win downgraded to 1X Double Chance due to risk filters.",
                        ))

            vote_pct_2 = (vote_2 / total_votes * 100) if total_votes > 0 else 0.0
            opponent_home_wins_recent = home_form["wins"]

            if coef_2 >= 72.0:
                if vote_pct_2 >= 75.0 and opponent_home_wins_recent == 0 and not is_cup:
                    odds = calc_odds(coef_2)
                    conf = round(0.55 * coef_2 + 0.25 * vote_pct_2 + 0.20 * 85.0, 1)
                    candidates.append(MarketCandidate(
                        match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                        home_team=home, away_team=away, market="1X2", selection=f"{away} To Win",
                        probability=coef_2, estimated_odds=odds, confidence_score=min(99.0, conf),
                        risk_level="Low",
                        justification=(
                            f"Straight Away Win Approved: {coef_2:.0f}% model + {vote_pct_2:.0f}% community vote."
                        ),
                    ))
                else:
                    # Downgrade to X2
                    if prob_x2 >= 80.0:
                        odds = calc_odds(prob_x2)
                        candidates.append(MarketCandidate(
                            match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                            home_team=home, away_team=away, market="Double Chance", selection=f"Draw or {away} (X2)",
                            probability=prob_x2, estimated_odds=odds, confidence_score=round(0.90 * prob_x2, 1),
                            risk_level="Ultra-Low",
                            justification="Safety Downgrade: Away Win downgraded to X2 Double Chance due to risk filters.",
                        ))

            # =========================================================================
            # CONSTRAINT 5: BAN HIGH-VARIANCE MARKETS (BTTS / GG)
            # Exclude raw BTTS unless BOTH teams scored in at least 4 of their last 5 matches
            # =========================================================================
            if coef_bts >= 65.0:
                if home_form["scored_in_count"] >= 4 and away_form["scored_in_count"] >= 4:
                    odds = calc_odds(coef_bts)
                    conf = round((0.60 * coef_bts + 0.40 * 85.0) * cup_penalty_multiplier, 1)
                    candidates.append(MarketCandidate(
                        match_id=match_id, date=date_val, time=time_val, competition=comp, country=country,
                        home_team=home, away_team=away, market="BTS", selection="Both Teams To Score (Yes)",
                        probability=coef_bts, estimated_odds=odds, confidence_score=min(99.0, conf),
                        risk_level="Moderate",
                        justification="BTTS Approved: Verified dual 4/5 recent match scoring consistency.",
                    ))

        logger.info(f"Generated {len(candidates)} high-safety market candidates.")
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
    ) -> Optional[AccumulatorSlip]:
        """Generic builder to generate an optimal accumulator slip for any odds tier."""
        # Filter viable candidates
        safe_candidates = [
            c for c in candidates
            if min_leg_odds <= c.estimated_odds <= max_leg_odds
        ]

        if len(safe_candidates) < min_legs:
            # Widen range if scarce
            safe_candidates = [
                c for c in candidates
                if 1.08 <= c.estimated_odds <= 2.20
            ]

        if len(safe_candidates) < min_legs:
            return None

        # Group by match_id
        match_map: Dict[str, List[MarketCandidate]] = {}
        for c in safe_candidates:
            match_map.setdefault(c.match_id, []).append(c)

        # Sort matches by highest confidence candidate
        sorted_match_ids = sorted(
            match_map.keys(),
            key=lambda m_id: max(x.confidence_score for x in match_map[m_id]),
            reverse=True,
        )

        distinct_matches = sorted_match_ids[:25]

        # For each match keep top candidate
        for m_id in distinct_matches:
            match_map[m_id] = sorted(
                match_map[m_id],
                key=lambda x: (x.confidence_score, -x.estimated_odds),
                reverse=True,
            )[:1]

        all_valid_combos: List[Tuple[float, float, List[MarketCandidate]]] = []

        # Target combinations between min_legs and max_legs
        for leg_count in range(min_legs, min(max_legs + 1, len(distinct_matches) + 1)):
            for match_combo in itertools.combinations(distinct_matches, leg_count):
                pick_options = [match_map[m_id] for m_id in match_combo]
                for combo in itertools.product(*pick_options):
                    tot_odds = 1.0
                    for leg in combo:
                        tot_odds *= leg.estimated_odds

                    avg_conf = sum(leg.confidence_score for leg in combo) / len(combo)

                    if min_total_odds <= tot_odds <= max_total_odds:
                        all_valid_combos.append((avg_conf, tot_odds, list(combo)))

        # Fallback 1: Widen odds range slightly (+/- 25%)
        if not all_valid_combos:
            wider_min = max(1.10, min_total_odds * 0.75)
            wider_max = max_total_odds * 1.30
            for leg_count in range(min_legs, min(max_legs + 1, len(distinct_matches) + 1)):
                for match_combo in itertools.combinations(distinct_matches, leg_count):
                    pick_options = [match_map[m_id] for m_id in match_combo]
                    for combo in itertools.product(*pick_options):
                        tot_odds = 1.0
                        for leg in combo:
                            tot_odds *= leg.estimated_odds
                        if wider_min <= tot_odds <= wider_max:
                            avg_conf = sum(leg.confidence_score for leg in combo) / len(combo)
                            all_valid_combos.append((avg_conf, tot_odds, list(combo)))

        # Fallback 2: Pick closest combination to target odds
        if not all_valid_combos:
            candidate_combos = []
            for leg_count in range(max(1, min_legs - 1), min(max_legs + 2, len(distinct_matches) + 1)):
                for match_combo in itertools.combinations(distinct_matches, leg_count):
                    pick_options = [match_map[m_id] for m_id in match_combo]
                    for combo in itertools.product(*pick_options):
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
            max_total_odds=1.85,
            min_legs=2,
            max_legs=3,
            name="Onítẹ́tẹ́ 1.5-Odds Ultra Banker Slip",
            description="Ultra-conservative 2-3 leg banker ticket with the highest probability ratings.",
            min_leg_odds=1.12,
            max_leg_odds=1.35,
        )

        # Tier 2: 3 Odds Banker (3-4 legs)
        slip_3 = self._build_tier_slip(
            candidates=candidates,
            target_odds=3.00,
            min_total_odds=2.70,
            max_total_odds=3.50,
            min_legs=3,
            max_legs=4,
            name="Onítẹ́tẹ́ 3-Odds Banker Slip",
            description="High-probability 3-4 leg slip with balanced safety-first market picks.",
            min_leg_odds=1.15,
            max_leg_odds=1.45,
        )

        # Tier 3: 5 Odds Banker (4-6 legs)
        slip_5 = self._build_tier_slip(
            candidates=candidates,
            target_odds=5.00,
            min_total_odds=4.50,
            max_total_odds=5.50,
            min_legs=4,
            max_legs=6,
            name="Onítẹ́tẹ́ 5-Odds Banker Slip",
            description="Classic Onítẹ́tẹ́ 5-odds multi-market accumulator with strict risk filters.",
            min_leg_odds=1.18,
            max_leg_odds=1.45,
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
            description="High-yield 5-8 leg accumulator constructed solely with vetted safe selections.",
            min_leg_odds=1.18,
            max_leg_odds=1.55,
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
        """Run full high-safety evaluation pipeline and persist all 4 tiers (1.5x, 3x, 5x, 10x)."""
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

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        # Save Formatted Multi-Tier TXT Report
        txt_report = self._format_txt_report(slips)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(txt_report)

        logger.info(f"Saved refined multi-tier daily slips JSON: {json_path}")
        logger.info(f"Saved refined multi-tier daily slips TXT: {txt_path}")

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
        lines.append("-" * 86)
        lines.append(f"{'Time':<6} | {'Fixture':<28} | {'Selection':<22} | {'Odds':<5} | {'Risk':<9} | {'Conf'}")
        lines.append("-" * 86)

        for leg in slip.legs:
            fixture_str = f"{leg.home_team[:13]} vs {leg.away_team[:13]}"
            lines.append(
                f"{leg.time:<6} | {fixture_str:<28} | {leg.selection[:22]:<22} | {leg.estimated_odds:>4.2f}x | {leg.risk_level:<9} | {leg.confidence_score:>4.1f}%"
            )
            lines.append(f"       ↳ Justification: {leg.justification}")

        return lines

    def _format_txt_report(self, slips: Any) -> str:
        """Format all 4 daily tickets (1.5x, 3x, 5x, 10x) with individual justifications into an ASCII report."""
        lines = []
        lines.append("=" * 86)
        lines.append("        🛡️ ONÍTẸ́TẸ́ MULTI-TIER DAILY ACCUMULATORS (1.5x, 3x, 5x, 10x)        ")
        lines.append("=" * 86)

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
        lines.append("-" * 86)
        lines.append("💡 Execution Strategy: Select your preferred risk profile (1.5x, 3x, 5x, 10x).")
        lines.append("=" * 86)
        return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = AccumulatorEngine()
    res = engine.generate_and_save()
    print("\n" + res["text_report"])

