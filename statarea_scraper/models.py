"""Data models for Statarea matches, predictions, and H2H statistics."""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class PredictionOdds:
    """Statistical prediction percentage values / coefficients from Statarea."""
    coef_1: Optional[int] = None
    coef_x: Optional[int] = None
    coef_2: Optional[int] = None
    coef_ht1: Optional[int] = None
    coef_htx: Optional[int] = None
    coef_ht2: Optional[int] = None
    coef_o15: Optional[int] = None
    coef_o25: Optional[int] = None
    coef_o35: Optional[int] = None
    coef_bts: Optional[int] = None
    coef_ots: Optional[int] = None


@dataclass
class UserVotes:
    """Community user predictions and likes."""
    vote_1: Optional[int] = None
    vote_x: Optional[int] = None
    vote_2: Optional[int] = None
    likes: Optional[int] = None
    dislikes: Optional[int] = None


@dataclass
class TeamInfo:
    """Detailed profile info of a team."""
    name: str = ""
    official_name: str = ""
    found: str = ""
    country: str = ""
    website: str = ""
    world_rank: Optional[int] = None


@dataclass
class H2HMatch:
    """Historical head-to-head match result."""
    date: str = ""
    competition: str = ""
    home_team: str = ""
    away_team: str = ""
    home_goals: Optional[str] = None
    away_goals: Optional[str] = None
    half_time_score: str = ""
    events: List[str] = field(default_factory=list)


@dataclass
class MatchFixture:
    """Stage 1: Match metadata from daily fixture prediction list."""
    match_id: str = ""
    date: str = ""
    time: str = ""
    competition: str = ""
    country: str = ""
    home_team: str = ""
    away_team: str = ""
    tip: str = ""
    comparison_url: str = ""
    odds: PredictionOdds = field(default_factory=PredictionOdds)
    user_votes: UserVotes = field(default_factory=UserVotes)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DeepMatchData:
    """Stage 2: Complete match data including deep H2H and team statistics."""
    fixture: MatchFixture
    home_team_info: Optional[TeamInfo] = None
    away_team_info: Optional[TeamInfo] = None
    h2h_matches: List[H2HMatch] = field(default_factory=list)
    recent_form_home: List[Dict[str, Any]] = field(default_factory=list)
    recent_form_away: List[Dict[str, Any]] = field(default_factory=list)
    match_facts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
