"""HTML parsing routines for Statarea predictions and detailed H2H comparison pages."""

import logging
import re
from typing import List, Optional, Dict, Any, Tuple
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin

from .config import BASE_URL
from .models import (
    MatchFixture,
    PredictionOdds,
    UserVotes,
    TeamInfo,
    H2HMatch,
    DeepMatchData,
)

logger = logging.getLogger(__name__)


def _safe_int(val: Optional[str]) -> Optional[int]:
    """Safely convert string to integer or return None."""
    if not val:
        return None
    cleaned = re.sub(r"[^\d]", "", str(val).strip())
    if cleaned.isdigit():
        try:
            return int(cleaned)
        except ValueError:
            return None
    return None


def _clean_text(tag: Optional[Tag]) -> str:
    """Extract and normalize stripped text from a tag."""
    if not tag:
        return ""
    return " ".join(tag.get_text().split())


class StatareaParser:
    """Parser for Statarea HTML pages."""

    @staticmethod
    def parse_predictions_page(html_content: str, default_date: str = "") -> List[MatchFixture]:
        """
        Stage 1 Parser: Parse the main predictions fixture list page.
        
        Args:
            html_content: HTML source string of /predictions
            default_date: Optional fallback date if not found in DOM
            
        Returns:
            List of MatchFixture objects.
        """
        soup = BeautifulSoup(html_content, "lxml")
        fixtures: List[MatchFixture] = []

        # Find global page date
        cdate_el = soup.find(id="cdate")
        page_date = _clean_text(cdate_el) if cdate_el else default_date

        # Iterate over all competition sections
        competition_divs = soup.find_all("div", class_="competition")
        for comp_div in competition_divs:
            # Skip advertisement blocks
            header = comp_div.find("div", class_="header")
            if not header:
                continue

            name_el = header.find("div", class_="name")
            comp_name_full = _clean_text(name_el) if name_el else ""
            if "advertisement" in comp_name_full.lower():
                continue

            # Extract Country and Competition name
            country = ""
            comp_title = comp_name_full
            logo_img = header.find("div", class_="logo")
            if logo_img and logo_img.find("img"):
                alt_text = logo_img.find("img").get("alt", "")
                country_match = re.search(r"^(.*?)\s+country\s+flag", alt_text, re.IGNORECASE)
                if country_match:
                    country = country_match.group(1).strip()

            if " - " in comp_name_full:
                parts = comp_name_full.split(" - ", 1)
                if not country:
                    country = parts[0].strip()
                comp_title = parts[1].strip()

            body = comp_div.find("div", class_="body")
            if not body:
                continue

            # Find all match rows in this competition
            match_elements = body.find_all("div", class_="match")
            for match_el in match_elements:
                try:
                    fixture = StatareaParser._parse_single_match_row(
                        match_el,
                        body=body,
                        comp_title=comp_title,
                        country=country,
                        page_date=page_date,
                    )
                    if fixture:
                        fixtures.append(fixture)
                except Exception as e:
                    logger.warning(f"Error parsing match row: {e}", exc_info=False)
                    continue

        logger.info(f"Extracted {len(fixtures)} fixtures from predictions page.")
        return fixtures

    @staticmethod
    def _parse_single_match_row(
        match_el: Tag,
        body: Tag,
        comp_title: str,
        country: str,
        page_date: str,
    ) -> Optional[MatchFixture]:
        """Parse an individual match div."""
        match_id = match_el.get("id", "")
        
        # Match Kickoff Time
        date_el = match_el.find("div", class_="date")
        match_time = _clean_text(date_el)

        # Teams
        teams_row = match_el.find("div", class_="teams")
        home_team = ""
        away_team = ""
        comparison_url = ""

        if teams_row:
            host_el = teams_row.find("div", class_="hostteam")
            guest_el = teams_row.find("div", class_="guestteam")
            if host_el:
                home_team = _clean_text(host_el.find("div", class_="name") or host_el)
                link = host_el.find("a")
                if link and link.get("href"):
                    comparison_url = urljoin(BASE_URL, link.get("href"))
            if guest_el:
                away_team = _clean_text(guest_el.find("div", class_="name") or guest_el)
                if not comparison_url:
                    link = guest_el.find("a")
                    if link and link.get("href"):
                        comparison_url = urljoin(BASE_URL, link.get("href"))

        # Fallback comparison URL from info action link
        if not comparison_url:
            info_link = match_el.find("div", class_="info")
            if info_link and info_link.find("a"):
                comparison_url = urljoin(BASE_URL, info_link.find("a").get("href"))

        # Tip / Prediction
        tip_el = match_el.find("div", class_="tip")
        tip_val = ""
        if tip_el:
            val_div = tip_el.find("div", class_="value")
            tip_val = _clean_text(val_div or tip_el)

        # Coefficients / Odds
        odds = PredictionOdds()
        inforow = match_el.find("div", class_="inforow")
        if inforow:
            coefrow = inforow.find("div", class_="coefrow")
            if coefrow:
                coef_boxes = coefrow.find_all("div", class_="coefbox")
                val_boxes = [cb for cb in coef_boxes if cb.find("div", class_="value")]
                vals = []
                for b in val_boxes:
                    v_el = b.find("div", class_="value")
                    vals.append(_safe_int(_clean_text(v_el)))

                if len(vals) >= 11:
                    odds.coef_1 = vals[0]
                    odds.coef_x = vals[1]
                    odds.coef_2 = vals[2]
                    odds.coef_ht1 = vals[3]
                    odds.coef_htx = vals[4]
                    odds.coef_ht2 = vals[5]
                    odds.coef_o15 = vals[6]
                    odds.coef_o25 = vals[7]
                    odds.coef_o35 = vals[8]
                    odds.coef_bts = vals[9]
                    odds.coef_ots = vals[10]

        # User Votes & Likes
        user_votes = UserVotes()
        if inforow:
            vote_div = inforow.find("div", class_="vote")
            if vote_div:
                v1 = vote_div.find("div", class_="vote1")
                vx = vote_div.find("div", class_="voteX")
                v2 = vote_div.find("div", class_="vote2")
                user_votes.vote_1 = _safe_int(_clean_text(v1.find("div", class_="value"))) if v1 else None
                user_votes.vote_x = _safe_int(_clean_text(vx.find("div", class_="value"))) if vx else None
                user_votes.vote_2 = _safe_int(_clean_text(v2.find("div", class_="value"))) if v2 else None

        # Likes / Dislikes
        like_pos = match_el.find("div", class_="likepositive")
        like_neg = match_el.find("div", class_="likenegative")
        if like_pos:
            user_votes.likes = _safe_int(_clean_text(like_pos.find("div", class_="value")))
        if like_neg:
            user_votes.dislikes = _safe_int(_clean_text(like_neg.find("div", class_="value")))

        if not home_team or not away_team:
            return None

        return MatchFixture(
            match_id=match_id,
            date=page_date,
            time=match_time,
            competition=comp_title,
            country=country,
            home_team=home_team,
            away_team=away_team,
            tip=tip_val,
            comparison_url=comparison_url,
            odds=odds,
            user_votes=user_votes,
        )

    @staticmethod
    def parse_comparison_page(html_content: str, fixture: MatchFixture) -> DeepMatchData:
        """
        Stage 2 Parser: Parse detailed team information, H2H matches, and recent form.
        
        Args:
            html_content: HTML source string of /compare/teams/...
            fixture: The corresponding MatchFixture object
            
        Returns:
            DeepMatchData object populated with detailed stats.
        """
        soup = BeautifulSoup(html_content, "lxml")
        
        # 1. Parse Teams Info
        home_team_info, away_team_info = StatareaParser._parse_teams_info(soup)

        # 2. Parse H2H Matches
        h2h_matches = StatareaParser._parse_h2h_matches(soup)

        # 3. Parse Recent Form for both teams
        recent_home, recent_away = StatareaParser._parse_recent_form(soup)

        # 4. Parse Match Facts
        facts = StatareaParser._parse_match_facts(soup)

        return DeepMatchData(
            fixture=fixture,
            home_team_info=home_team_info,
            away_team_info=away_team_info,
            h2h_matches=h2h_matches,
            recent_form_home=recent_home,
            recent_form_away=recent_away,
            match_facts=facts,
        )

    @staticmethod
    def _parse_teams_info(soup: BeautifulSoup) -> Tuple[Optional[TeamInfo], Optional[TeamInfo]]:
        """Extract detailed team profile boxes."""
        teams_info_container = soup.find("div", class_="teamsinfo")
        if not teams_info_container:
            return None, None

        half_containers = teams_info_container.find_all("div", class_="halfcontainer")
        infos = []

        for hc in half_containers[:2]:
            try:
                caption = hc.find("div", class_="caption")
                name = _clean_text(caption.find("div", class_="name")) if caption else ""
                
                official_name = ""
                found = ""
                country = ""
                website = ""
                world_rank = None

                teamname_el = hc.find(id="teamname")
                if teamname_el:
                    official_name = _clean_text(teamname_el)

                teamfound_el = hc.find(id="teamfound")
                if teamfound_el:
                    found = _clean_text(teamfound_el)

                teamcountry_el = hc.find(id="teamcountry")
                if teamcountry_el:
                    country = _clean_text(teamcountry_el.find("span", class_="name") or teamcountry_el)

                teamwebsite_el = hc.find(id="teamwebsite")
                if teamwebsite_el:
                    link = teamwebsite_el.find("a")
                    website = link.get("href", "") if link else _clean_text(teamwebsite_el)

                # World rank
                for row in hc.find_all("div", class_="datarow"):
                    label = _clean_text(row.find("div", class_="label")).lower()
                    if "world rank" in label or "rank" in label:
                        val_el = row.find("div", class_="value")
                        world_rank = _safe_int(_clean_text(val_el))

                infos.append(TeamInfo(
                    name=name,
                    official_name=official_name,
                    found=found,
                    country=country,
                    website=website,
                    world_rank=world_rank,
                ))
            except Exception as e:
                logger.warning(f"Error parsing team info block: {e}")
                infos.append(None)

        home_info = infos[0] if len(infos) > 0 else None
        away_info = infos[1] if len(infos) > 1 else None
        return home_info, away_info

    @staticmethod
    def _parse_h2h_matches(soup: BeautifulSoup) -> List[H2HMatch]:
        """Extract head-to-head historical matches from the matches container."""
        h2h_list: List[H2HMatch] = []
        matches_container = soup.find("div", class_="matches")
        if not matches_container:
            # Fallback: look for matchbtwteams container with matchitem children
            for div in soup.find_all("div", class_="matchbtwteams"):
                if div.find("div", class_="matchitem"):
                    matches_container = div
                    break

        if not matches_container:
            return h2h_list

        match_items = matches_container.find_all("div", class_="matchitem")
        for item in match_items:
            try:
                comp_el = item.find("div", class_="competition")
                competition = _clean_text(comp_el)

                date_el = item.find("div", class_="date")
                match_date = _clean_text(date_el)

                match_div = item.find("div", class_="match")
                home_team = ""
                away_team = ""
                home_goals = None
                away_goals = None

                if match_div:
                    host = match_div.find("div", class_="hostteam")
                    guest = match_div.find("div", class_="guestteam")
                    if host:
                        home_team = _clean_text(host.find("div", class_="name") or host)
                        goals_el = host.find("div", class_="goals")
                        home_goals = _clean_text(goals_el) if goals_el else None
                    if guest:
                        away_team = _clean_text(guest.find("div", class_="name") or guest)
                        goals_el = guest.find("div", class_="goals")
                        away_goals = _clean_text(goals_el) if goals_el else None

                # Details: Halftime and events
                half_time_score = ""
                events = []
                details = item.find("div", class_="details")
                if details:
                    for info in details.find_all("div", class_="info"):
                        label = _clean_text(info.find("div", class_="label")).lower()
                        if "half time" in label:
                            goals = info.find_all("div", class_="goals")
                            if len(goals) >= 2:
                                half_time_score = f"{_clean_text(goals[0])}-{_clean_text(goals[1])}"

                    for act in details.find_all("div", class_="action"):
                        p_el = act.find("div", class_="player")
                        if p_el:
                            event_text = _clean_text(p_el)
                            action_box = act.find("div", class_="matchaction")
                            action_type = ""
                            if action_box and action_box.find("div"):
                                action_type = action_box.find("div").get("class", [""])[0]
                            if action_type:
                                events.append(f"[{action_type}] {event_text}")
                            else:
                                events.append(event_text)

                if home_team or away_team:
                    h2h_list.append(H2HMatch(
                        date=match_date,
                        competition=competition,
                        home_team=home_team,
                        away_team=away_team,
                        home_goals=home_goals,
                        away_goals=away_goals,
                        half_time_score=half_time_score,
                        events=events,
                    ))
            except Exception as e:
                logger.warning(f"Error parsing H2H match item: {e}")
                continue

        return h2h_list

    @staticmethod
    def _parse_recent_form(soup: BeautifulSoup) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract recent form / last matches for both teams."""
        recent_home: List[Dict[str, Any]] = []
        recent_away: List[Dict[str, Any]] = []

        last_teams = soup.find("div", class_="lastteamsmatches")
        if not last_teams:
            return recent_home, recent_away

        half_containers = last_teams.find_all("div", class_="halfcontainer")
        for idx, hc in enumerate(half_containers[:2]):
            target_list = recent_home if idx == 0 else recent_away
            match_items = hc.find_all("div", class_="matchitem")
            for item in match_items:
                try:
                    comp = _clean_text(item.find("div", class_="competition"))
                    m_date = _clean_text(item.find("div", class_="date"))
                    match_div = item.find("div", class_="match")
                    h_team, a_team, h_goals, a_goals = "", "", "", ""
                    if match_div:
                        host = match_div.find("div", class_="hostteam")
                        guest = match_div.find("div", class_="guestteam")
                        if host:
                            h_team = _clean_text(host.find("div", class_="name") or host)
                            h_goals = _clean_text(host.find("div", class_="goals"))
                        if guest:
                            a_team = _clean_text(guest.find("div", class_="name") or guest)
                            a_goals = _clean_text(guest.find("div", class_="goals"))

                    target_list.append({
                        "date": m_date,
                        "competition": comp,
                        "home_team": h_team,
                        "away_team": a_team,
                        "score": f"{h_goals}-{a_goals}" if h_goals and a_goals else "",
                    })
                except Exception:
                    continue

        return recent_home, recent_away

    @staticmethod
    def _parse_match_facts(soup: BeautifulSoup) -> List[str]:
        """Extract match facts if available."""
        facts_list: List[str] = []
        stats = soup.find("div", class_="teamsstatistics")
        if not stats:
            return facts_list

        for row in stats.find_all("div", class_="datarow"):
            t = _clean_text(row)
            if t:
                facts_list.append(t)

        return facts_list
