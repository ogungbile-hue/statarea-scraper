"""Live Scores, Settlement, and Multi-Timeframe Real Analytics Engine for Onítẹ́tẹ́.

Features:
- Pure real-world match score scraping from Statarea.
- Automated bet settlement across multi-market selections (1X2, Double Chance, Goals O/U, BTTS).
- Daily Slips score enrichment (attaches real live/FT scores directly to daily_5odds_slip.json).
- Real P&L and ROI ledger (NO synthetic or mock data).
"""

import csv
import datetime
import json
import logging
import os
import re
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

RESULTS_LEDGER_JSON = "output/results_ledger.json"
RESULTS_LEDGER_CSV = "output/results_ledger.csv"


@dataclass
class LegSettlement:
    """Settled individual leg of a slip."""
    match_id: str
    date: str
    time: str
    competition: str
    home_team: str
    away_team: str
    market: str
    selection: str
    estimated_odds: float
    confidence_score: float
    status: str  # "WON", "LOST", "PENDING", "LIVE"
    home_goals: Optional[int]
    away_goals: Optional[int]
    match_status: str  # "FT", "LIVE", "SCHEDULED"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SlipSettlement:
    """Settled accumulator slip entry in the real ledger."""
    slip_id: str
    date: str
    slip_name: str
    total_odds: float
    legs_count: int
    average_confidence: float
    status: str  # "WON", "LOST", "PENDING", "LIVE"
    stake: float
    payout: float
    profit: float
    legs: List[LegSettlement]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slip_id": self.slip_id,
            "date": self.date,
            "slip_name": self.slip_name,
            "total_odds": round(self.total_odds, 2),
            "legs_count": self.legs_count,
            "average_confidence": round(self.average_confidence, 1),
            "status": self.status,
            "stake": round(self.stake, 2),
            "payout": round(self.payout, 2),
            "profit": round(self.profit, 2),
            "legs": [l.to_dict() for l in self.legs],
        }


class ResultsTracker:
    """Real Data Live Results Tracking and Settlement Engine."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.ledger_json_path = os.path.join(self.output_dir, "results_ledger.json")
        self.ledger_csv_path = os.path.join(self.output_dir, "results_ledger.csv")
        self._ensure_ledger_initialized()

    def _ensure_ledger_initialized(self) -> None:
        """Initialize empty ledger if not present (real data only)."""
        if not os.path.exists(self.ledger_json_path):
            with open(self.ledger_json_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)
            self._export_ledger_csv([])

    def _export_ledger_csv(self, ledger_data: List[Dict[str, Any]]) -> None:
        """Export flat ledger summary to CSV."""
        fieldnames = [
            "slip_id", "date", "slip_name", "total_odds", "legs_count",
            "average_confidence", "status", "stake", "payout", "profit",
            "winning_legs_count", "lost_legs_count",
        ]
        with open(self.ledger_csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for s in ledger_data:
                legs = s.get("legs", [])
                won_count = sum(1 for l in legs if l.get("status") == "WON")
                lost_count = sum(1 for l in legs if l.get("status") == "LOST")
                writer.writerow({
                    "slip_id": s.get("slip_id", ""),
                    "date": s.get("date", ""),
                    "slip_name": s.get("slip_name", ""),
                    "total_odds": s.get("total_odds", 0.0),
                    "legs_count": s.get("legs_count", 0),
                    "average_confidence": s.get("average_confidence", 0.0),
                    "status": s.get("status", "PENDING"),
                    "stake": s.get("stake", 1.0),
                    "payout": s.get("payout", 0.0),
                    "profit": s.get("profit", 0.0),
                    "winning_legs_count": won_count,
                    "lost_legs_count": lost_count,
                })

    def load_ledger(self) -> List[Dict[str, Any]]:
        """Load all real historical slips from ledger."""
        if not os.path.exists(self.ledger_json_path):
            return []
        try:
            with open(self.ledger_json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading ledger JSON: {e}")
            return []

    def save_ledger(self, ledger_data: List[Dict[str, Any]]) -> None:
        """Persist updated ledger to JSON and CSV."""
        with open(self.ledger_json_path, "w", encoding="utf-8") as f:
            json.dump(ledger_data, f, indent=2, ensure_ascii=False)
        self._export_ledger_csv(ledger_data)

    def evaluate_market_result(
        self,
        market: str,
        selection: str,
        home_goals: Optional[int],
        away_goals: Optional[int],
        match_status: str,
    ) -> str:
        """
        Evaluate whether an individual market selection WON, LOST, or is PENDING.
        """
        if home_goals is None or away_goals is None:
            return "PENDING"
        if match_status not in ["FT", "AET", "Final"]:
            return "LIVE"

        hg = int(home_goals)
        ag = int(away_goals)
        tot_goals = hg + ag

        market_norm = market.lower()
        sel_norm = selection.lower()

        # 1. Goals: Over 1.5 Goals
        if "over 1.5" in sel_norm:
            return "WON" if tot_goals >= 2 else "LOST"

        # 2. Goals: Over 2.5 Goals
        if "over 2.5" in sel_norm:
            return "WON" if tot_goals >= 3 else "LOST"

        # 3. Goals: Under 3.5 Goals
        if "under 3.5" in sel_norm:
            return "WON" if tot_goals <= 3 else "LOST"

        # 4. BTS (Both Teams To Score)
        if "both teams to score" in sel_norm or "bts" in market_norm or "gg" in sel_norm:
            return "WON" if (hg > 0 and ag > 0) else "LOST"

        # 5. Double Chance: 1X (Home or Draw)
        if "1x" in sel_norm or "or draw" in sel_norm:
            return "WON" if hg >= ag else "LOST"

        # 6. Double Chance: X2 (Draw or Away)
        if "x2" in sel_norm or "draw or" in sel_norm:
            return "WON" if ag >= hg else "LOST"

        # 7. Straight Win (1)
        if "to win" in sel_norm:
            if hg > ag:
                return "WON"
            else:
                return "LOST"

        return "PENDING"

    def fetch_live_scores_from_statarea(self, date_str: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Fetch real match scores and status from Statarea.
        Checks both target date and main prediction endpoints.
        """
        from statarea_scraper.client import StatareaClient
        from bs4 import BeautifulSoup

        target_date = date_str or datetime.date.today().strftime("%Y-%m-%d")
        urls = [
            f"https://www.statarea.com/predictions/date/{target_date}",
            "https://www.statarea.com/predictions",
            "https://www.statarea.com/predictions/date/2026-08-26",
        ]
        
        scores_map: Dict[str, Dict[str, Any]] = {}
        client = StatareaClient()

        for url in urls:
            try:
                html = client.get(url, apply_delay=False)
                if not html:
                    continue

                soup = BeautifulSoup(html, "lxml")
                rows = soup.select("div.match")

                for r in rows:
                    match_id = str(r.get("id", "")).replace("match_", "").strip()
                    if not match_id:
                        continue

                    host_goals_el = r.select_one("div.hostteam a.goals, div.hostteam .goals")
                    guest_goals_el = r.select_one("div.guestteam a.goals, div.guestteam .goals")
                    ht_el = r.select_one("div.htres")

                    home_goals = None
                    away_goals = None
                    match_status = "SCHEDULED"

                    if host_goals_el and guest_goals_el:
                        hg_txt = host_goals_el.get_text(strip=True)
                        ag_txt = guest_goals_el.get_text(strip=True)
                        if hg_txt.isdigit() and ag_txt.isdigit():
                            home_goals = int(hg_txt)
                            away_goals = int(ag_txt)
                            match_status = "FT"

                    # Check for in-play status indicator
                    status_el = r.select_one("div.date, div.time, div.status")
                    if status_el:
                        st_txt = status_el.get_text(strip=True).upper()
                        if "'" in st_txt or "HT" in st_txt or "LIVE" in st_txt:
                            match_status = "LIVE"
                        elif "FT" in st_txt or "FIN" in st_txt:
                            match_status = "FT"

                    scores_map[match_id] = {
                        "match_id": match_id,
                        "home_goals": home_goals,
                        "away_goals": away_goals,
                        "match_status": match_status,
                    }

            except Exception as e:
                logger.warning(f"Error fetching scores from {url}: {e}")

        logger.info(f"Loaded live/FT scores for {len(scores_map)} matches from Statarea.")
        return scores_map

    def settle_today_slips(self) -> Dict[str, Any]:
        """
        Settle today's slips against latest real live scores, update Daily Slips JSON,
        and record strictly real data into the ledger.
        """
        slips_path = os.path.join(self.output_dir, "daily_5odds_slip.json")
        if not os.path.exists(slips_path):
            return {"success": False, "message": "No daily slips found."}

        with open(slips_path, "r", encoding="utf-8") as f:
            daily_data = json.load(f)

        live_scores = self.fetch_live_scores_from_statarea()
        ledger = self.load_ledger()
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        settled_banker = self._settle_single_slip(daily_data.get("banker_ticket"), live_scores, today_str, "banker")
        settled_value = self._settle_single_slip(daily_data.get("value_ticket"), live_scores, today_str, "value")

        # 1. Update Daily Slips JSON so "Daily Slips" view displays live scores directly
        daily_data["banker_ticket"] = settled_banker
        daily_data["value_ticket"] = settled_value
        with open(slips_path, "w", encoding="utf-8") as f:
            json.dump(daily_data, f, indent=2, ensure_ascii=False)

        # 2. Update real ledger
        for settled in [settled_banker, settled_value]:
            if not settled:
                continue
            idx = next((i for i, s in enumerate(ledger) if s["slip_id"] == settled["slip_id"]), None)
            if idx is not None:
                ledger[idx] = settled
            else:
                ledger.insert(0, settled)

        self.save_ledger(ledger)
        return {
            "success": True,
            "settled_banker": settled_banker,
            "settled_value": settled_value,
            "total_records": len(ledger),
        }

    def _settle_single_slip(
        self,
        slip_data: Optional[Dict[str, Any]],
        live_scores: Dict[str, Dict[str, Any]],
        date_str: str,
        slip_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Settle a single slip object."""
        if not slip_data or not slip_data.get("legs"):
            return None

        slip_id = f"{date_str}-{slip_type}"
        slip_name = slip_data.get("name", "Onítẹ́tẹ́ Slip")
        total_odds = float(slip_data.get("total_odds", 5.0))
        avg_conf = float(slip_data.get("average_confidence", 75.0))
        stake = 1.0

        settled_legs: List[LegSettlement] = []
        any_lost = False
        all_won = True
        has_pending = False

        for leg in slip_data.get("legs", []):
            m_id = str(leg.get("match_id", ""))
            score_info = live_scores.get(m_id, {})

            hg = score_info.get("home_goals")
            ag = score_info.get("away_goals")
            m_status = score_info.get("match_status", "SCHEDULED")

            leg_status = self.evaluate_market_result(
                market=leg.get("market", ""),
                selection=leg.get("selection", ""),
                home_goals=hg,
                away_goals=ag,
                match_status=m_status,
            )

            if leg_status == "LOST":
                any_lost = True
                all_won = False
            elif leg_status in ["PENDING", "LIVE"]:
                has_pending = True
                all_won = False

            settled_legs.append(LegSettlement(
                match_id=m_id,
                date=leg.get("date", date_str),
                time=leg.get("time", ""),
                competition=leg.get("competition", ""),
                home_team=leg.get("home_team", ""),
                away_team=leg.get("away_team", ""),
                market=leg.get("market", ""),
                selection=leg.get("selection", ""),
                estimated_odds=float(leg.get("estimated_odds", 1.25)),
                confidence_score=float(leg.get("confidence_score", 75.0)),
                status=leg_status,
                home_goals=hg,
                away_goals=ag,
                match_status=m_status,
            ))

        if any_lost:
            slip_status = "LOST"
            payout = 0.0
            profit = -stake
        elif all_won:
            slip_status = "WON"
            payout = round(stake * total_odds, 2)
            profit = round(payout - stake, 2)
        elif has_pending:
            slip_status = "LIVE" if any(l.match_status == "LIVE" for l in settled_legs) else "PENDING"
            payout = 0.0
            profit = 0.0
        else:
            slip_status = "PENDING"
            payout = 0.0
            profit = 0.0

        settled = SlipSettlement(
            slip_id=slip_id,
            date=date_str,
            slip_name=slip_name,
            total_odds=total_odds,
            legs_count=len(settled_legs),
            average_confidence=avg_conf,
            status=slip_status,
            stake=stake,
            payout=payout,
            profit=profit,
            legs=settled_legs,
        )
        return settled.to_dict()

    def compute_analytics(self) -> Dict[str, Any]:
        """
        Compute real Daily, Weekly, Monthly, and Market-by-Market P&L analytics.
        Contains STRICTLY real crawled and settled match data.
        """
        ledger = self.load_ledger()
        if not ledger:
            return self._empty_analytics()

        total_slips = len(ledger)
        settled_slips = [s for s in ledger if s.get("status") in ["WON", "LOST"]]
        settled_count = len(settled_slips)

        won_slips = [s for s in settled_slips if s.get("status") == "WON"]
        lost_slips = [s for s in settled_slips if s.get("status") == "LOST"]
        pending_slips = [s for s in ledger if s.get("status") in ["PENDING", "LIVE"]]

        total_staked = sum(s.get("stake", 1.0) for s in settled_slips)
        total_payout = sum(s.get("payout", 0.0) for s in settled_slips)
        net_profit = round(total_payout - total_staked, 2)
        roi_pct = round((net_profit / total_staked * 100), 1) if total_staked > 0 else 0.0
        win_rate = round((len(won_slips) / settled_count * 100), 1) if settled_count > 0 else 0.0

        # Current streak
        current_streak_type = "None"
        streak_count = 0
        for s in settled_slips:
            st = s.get("status")
            if current_streak_type == "None":
                current_streak_type = st
                streak_count = 1
            elif st == current_streak_type:
                streak_count += 1
            else:
                break

        # 1. Daily Breakdown
        daily_map: Dict[str, Dict[str, Any]] = {}
        for s in ledger:
            d = s.get("date", "Unknown")
            daily_map.setdefault(d, {"date": d, "total": 0, "won": 0, "lost": 0, "pending": 0, "profit": 0.0, "staked": 0.0})
            daily_map[d]["total"] += 1
            st = s.get("status")
            if st == "WON":
                daily_map[d]["won"] += 1
                daily_map[d]["profit"] += s.get("profit", 0.0)
                daily_map[d]["staked"] += s.get("stake", 1.0)
            elif st == "LOST":
                daily_map[d]["lost"] += 1
                daily_map[d]["profit"] += s.get("profit", 0.0)
                daily_map[d]["staked"] += s.get("stake", 1.0)
            else:
                daily_map[d]["pending"] += 1

        daily_list = sorted(daily_map.values(), key=lambda x: x["date"], reverse=True)
        for d in daily_list:
            d["profit"] = round(d["profit"], 2)
            d["win_rate"] = round((d["won"] / (d["won"] + d["lost"]) * 100), 1) if (d["won"] + d["lost"]) > 0 else 0.0

        # 2. Weekly Breakdown (ISO Weeks)
        weekly_map: Dict[str, Dict[str, Any]] = {}
        for s in ledger:
            d_str = s.get("date", "")
            try:
                dt = datetime.datetime.strptime(d_str, "%Y-%m-%d")
                week_key = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
            except Exception:
                week_key = "Recent"

            weekly_map.setdefault(week_key, {"week": week_key, "total": 0, "won": 0, "lost": 0, "profit": 0.0, "staked": 0.0})
            weekly_map[week_key]["total"] += 1
            st = s.get("status")
            if st == "WON":
                weekly_map[week_key]["won"] += 1
                weekly_map[week_key]["profit"] += s.get("profit", 0.0)
                weekly_map[week_key]["staked"] += s.get("stake", 1.0)
            elif st == "LOST":
                weekly_map[week_key]["lost"] += 1
                weekly_map[week_key]["profit"] += s.get("profit", 0.0)
                weekly_map[week_key]["staked"] += s.get("stake", 1.0)

        weekly_list = sorted(weekly_map.values(), key=lambda x: x["week"], reverse=True)
        for w in weekly_list:
            w["profit"] = round(w["profit"], 2)
            w["roi"] = round((w["profit"] / w["staked"] * 100), 1) if w["staked"] > 0 else 0.0
            w["win_rate"] = round((w["won"] / (w["won"] + w["lost"]) * 100), 1) if (w["won"] + w["lost"]) > 0 else 0.0

        # 3. Monthly Breakdown
        monthly_map: Dict[str, Dict[str, Any]] = {}
        for s in ledger:
            d_str = s.get("date", "")
            m_key = d_str[:7] if len(d_str) >= 7 else "Current"
            monthly_map.setdefault(m_key, {"month": m_key, "total": 0, "won": 0, "lost": 0, "profit": 0.0, "staked": 0.0})
            monthly_map[m_key]["total"] += 1
            st = s.get("status")
            if st == "WON":
                monthly_map[m_key]["won"] += 1
                monthly_map[m_key]["profit"] += s.get("profit", 0.0)
                monthly_map[m_key]["staked"] += s.get("stake", 1.0)
            elif st == "LOST":
                monthly_map[m_key]["lost"] += 1
                monthly_map[m_key]["profit"] += s.get("profit", 0.0)
                monthly_map[m_key]["staked"] += s.get("stake", 1.0)

        monthly_list = sorted(monthly_map.values(), key=lambda x: x["month"], reverse=True)
        for m in monthly_list:
            m["profit"] = round(m["profit"], 2)
            m["roi"] = round((m["profit"] / m["staked"] * 100), 1) if m["staked"] > 0 else 0.0
            m["win_rate"] = round((m["won"] / (m["won"] + m["lost"]) * 100), 1) if (m["won"] + m["lost"]) > 0 else 0.0

        # 4. Market-by-Market Accuracy Breakdown
        market_stats: Dict[str, Dict[str, Any]] = {
            "Double Chance": {"market": "Double Chance (1X/X2)", "total": 0, "won": 0, "lost": 0},
            "Goals": {"market": "Goals (O1.5 / U3.5)", "total": 0, "won": 0, "lost": 0},
            "BTS": {"market": "Both Teams To Score", "total": 0, "won": 0, "lost": 0},
            "1X2": {"market": "Straight Win (1/2)", "total": 0, "won": 0, "lost": 0},
        }

        all_legs = [leg for s in ledger for leg in s.get("legs", [])]
        for leg in all_legs:
            m_type = leg.get("market", "Other")
            key = "Double Chance" if "chance" in m_type.lower() else ("Goals" if "goal" in m_type.lower() else ("BTS" if "bts" in m_type.lower() else "1X2"))
            market_stats.setdefault(key, {"market": key, "total": 0, "won": 0, "lost": 0})
            
            st = leg.get("status")
            if st in ["WON", "LOST"]:
                market_stats[key]["total"] += 1
                if st == "WON":
                    market_stats[key]["won"] += 1
                else:
                    market_stats[key]["lost"] += 1

        market_list = list(market_stats.values())
        for m in market_list:
            m["win_rate"] = round((m["won"] / m["total"] * 100), 1) if m["total"] > 0 else 0.0

        return {
            "summary": {
                "total_slips": total_slips,
                "settled_count": settled_count,
                "won_count": len(won_slips),
                "lost_count": len(lost_slips),
                "pending_count": len(pending_slips),
                "win_rate": win_rate,
                "total_staked": total_staked,
                "total_payout": total_payout,
                "net_profit": net_profit,
                "roi_pct": roi_pct,
                "current_streak": f"{streak_count} {current_streak_type}" if streak_count > 0 else "None",
            },
            "daily": daily_list,
            "weekly": weekly_list,
            "monthly": monthly_list,
            "market_accuracy": market_list,
            "recent_slips": ledger,
        }

    def _empty_analytics(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total_slips": 0, "settled_count": 0, "won_count": 0, "lost_count": 0, "pending_count": 0,
                "win_rate": 0.0, "total_staked": 0.0, "total_payout": 0.0, "net_profit": 0.0, "roi_pct": 0.0,
                "current_streak": "None",
            },
            "daily": [], "weekly": [], "monthly": [], "market_accuracy": [], "recent_slips": [],
        }
