"""Unit tests for Statarea HTML parsers."""

import unittest
from statarea_scraper.parser import StatareaParser
from statarea_scraper.models import MatchFixture


SAMPLE_PREDICTIONS_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div class="predictions">
        <div class="navigator"><div class="value" id="cdate">2026-08-26</div></div>
        <div class="competition" id="017185">
            <div class="header">
                <div class="logo"><img src="https://media02.statarea.com/images/flags/roundflag/170.png" alt="Spain country flag" /></div>
                <div class="name">SPAIN - LALIGA</div>
            </div>
            <div class="body">
                <div class="match" id="1713582">
                    <div class="date">15:00</div>
                    <div class="tip"><div class="value">1</div></div>
                    <div class="teams">
                        <div class="hostteam"><div class="name"><a href="https://www.statarea.com/compare/teams/Real+Madrid (Spain)/Real+Sociedad (Spain)">Real Madrid</a></div></div>
                        <div class="guestteam"><div class="name"><a href="https://www.statarea.com/compare/teams/Real+Madrid (Spain)/Real+Sociedad (Spain)">Real Sociedad</a></div></div>
                    </div>
                    <div class="inforow">
                        <div class="coefrow">
                            <div class="coefbox"><div class="value r68">68</div></div>
                            <div class="coefbox"><div class="value r24">24</div></div>
                            <div class="coefbox"><div class="value r8">8</div></div>
                            <div class="coefbox"><div class="value b49">49</div></div>
                            <div class="coefbox"><div class="value b35">35</div></div>
                            <div class="coefbox"><div class="value b16">16</div></div>
                            <div class="coefbox"><div class="value o92">92</div></div>
                            <div class="coefbox"><div class="value o67">67</div></div>
                            <div class="coefbox"><div class="value o45">45</div></div>
                            <div class="coefbox"><div class="value g63">63</div></div>
                            <div class="coefbox"><div class="value g37">37</div></div>
                        </div>
                        <div class="vote">
                            <div class="vote1"><div class="value">39</div></div>
                            <div class="voteX"><div class="value">3</div></div>
                            <div class="vote2"><div class="value">5</div></div>
                        </div>
                    </div>
                    <div class="likepositive"><div class="value">25</div></div>
                    <div class="likenegative"><div class="value">3</div></div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

SAMPLE_COMPARISON_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div class="teamsinfo">
        <div class="halfcontainer">
            <div class="caption"><div class="name">Real Madrid</div></div>
            <div class="data">
                <div class="datarow"><div class="label">name</div><div class="value" id="teamname">Real Madrid Club de Fútbol</div></div>
                <div class="datarow"><div class="label">found</div><div class="value" id="teamfound">6 March 1902</div></div>
                <div class="datarow"><div class="label">country</div><div class="value" id="teamcountry"><span class="name">Spain</span></div></div>
                <div class="datarow"><div class="label">website</div><div class="value" id="teamwebsite"><a href="http://www.realmadrid.com">http://www.realmadrid.com</a></div></div>
                <div class="datarow"><div class="label">world rank</div><div class="value">7</div></div>
            </div>
        </div>
        <div class="halfcontainer">
            <div class="caption"><div class="name">Real Sociedad</div></div>
            <div class="data">
                <div class="datarow"><div class="label">name</div><div class="value" id="teamname">Real Sociedad de Fútbol, S.A.D.</div></div>
                <div class="datarow"><div class="label">found</div><div class="value" id="teamfound">7 September 1909</div></div>
                <div class="datarow"><div class="label">country</div><div class="value" id="teamcountry"><span class="name">Spain</span></div></div>
                <div class="datarow"><div class="label">website</div><div class="value" id="teamwebsite"><a href="http://www.realsociedad.com">http://www.realsociedad.com</a></div></div>
                <div class="datarow"><div class="label">world rank</div><div class="value">93</div></div>
            </div>
        </div>
    </div>
    <div class="matchbtwteams">
        <div class="matches">
            <div class="matchitem">
                <div class="competition">Spain - Laliga 2025/2026</div>
                <div class="date">2026-02-14</div>
                <div class="match">
                    <div class="hostteam"><div class="goals">4</div><div class="name">Real Madrid</div></div>
                    <div class="guestteam"><div class="goals">1</div><div class="name">Real Sociedad</div></div>
                </div>
                <div class="details">
                    <div class="info"><div class="goals">3</div><div class="goals">1</div><div class="label">half time result</div></div>
                    <div class="action">
                        <div class="matchaction"><div class="goal"></div></div>
                        <div class="player">5' Gonzalo Garcia</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


class TestStatareaParser(unittest.TestCase):
    """Test suite for StatareaParser methods."""

    def test_parse_predictions_page(self):
        fixtures = StatareaParser.parse_predictions_page(SAMPLE_PREDICTIONS_HTML)
        self.assertEqual(len(fixtures), 1)

        fix = fixtures[0]
        self.assertEqual(fix.match_id, "1713582")
        self.assertEqual(fix.date, "2026-08-26")
        self.assertEqual(fix.time, "15:00")
        self.assertEqual(fix.country, "Spain")
        self.assertEqual(fix.competition, "LALIGA")
        self.assertEqual(fix.home_team, "Real Madrid")
        self.assertEqual(fix.away_team, "Real Sociedad")
        self.assertEqual(fix.tip, "1")
        self.assertEqual(fix.odds.coef_1, 68)
        self.assertEqual(fix.odds.coef_x, 24)
        self.assertEqual(fix.odds.coef_2, 8)
        self.assertEqual(fix.odds.coef_ht1, 49)
        self.assertEqual(fix.odds.coef_o25, 67)
        self.assertEqual(fix.user_votes.vote_1, 39)
        self.assertEqual(fix.user_votes.likes, 25)
        self.assertEqual(fix.user_votes.dislikes, 3)
        self.assertIn("compare/teams/Real+Madrid", fix.comparison_url)

    def test_parse_comparison_page(self):
        fix = MatchFixture(
            match_id="1713582",
            home_team="Real Madrid",
            away_team="Real Sociedad",
        )
        deep = StatareaParser.parse_comparison_page(SAMPLE_COMPARISON_HTML, fix)
        
        self.assertIsNotNone(deep.home_team_info)
        self.assertEqual(deep.home_team_info.name, "Real Madrid")
        self.assertEqual(deep.home_team_info.official_name, "Real Madrid Club de Fútbol")
        self.assertEqual(deep.home_team_info.world_rank, 7)
        self.assertEqual(deep.home_team_info.country, "Spain")

        self.assertIsNotNone(deep.away_team_info)
        self.assertEqual(deep.away_team_info.name, "Real Sociedad")
        self.assertEqual(deep.away_team_info.world_rank, 93)

        self.assertEqual(len(deep.h2h_matches), 1)
        h2h = deep.h2h_matches[0]
        self.assertEqual(h2h.home_goals, "4")
        self.assertEqual(h2h.away_goals, "1")
        self.assertEqual(h2h.date, "2026-02-14")


if __name__ == "__main__":
    unittest.main()
