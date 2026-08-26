"""Statarea Web Scraper & Prediction Engine (Onítẹ́tẹ́)."""

from .scraper import StatareaScraper
from .models import MatchFixture, DeepMatchData
from .analytics_exporter import AnalyticsExporter
from .accumulator_engine import AccumulatorEngine, AccumulatorSlip, MarketCandidate
from .results_tracker import ResultsTracker, SlipSettlement, LegSettlement

__all__ = [
    "StatareaScraper",
    "MatchFixture",
    "DeepMatchData",
    "AnalyticsExporter",
    "AccumulatorEngine",
    "AccumulatorSlip",
    "MarketCandidate",
    "ResultsTracker",
    "SlipSettlement",
    "LegSettlement",
]
