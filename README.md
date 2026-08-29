# Onítẹ́tẹ́ - AI Soccer Prediction & Multi-Tier (1.5x, 3x, 5x, 10x) Odds Engine
*Powered by Eighty-Two Limited AI*

**Onítẹ́tẹ́** is an automated, resilient soccer prediction intelligence engine and web scraper designed to extract daily soccer match predictions, statistical probability coefficients, community user votes, and detailed head-to-head (H2H) comparison statistics from [Statarea](https://www.statarea.com/predictions).

Featuring an **official animated Eighty-Two Limited element badge**, dynamic H2H recency filtering, safety-first market constraints, real-time live score settlement, and a 4-tier daily accumulator strategy (**1.5 Odds Ultra Banker**, **3 Odds Banker**, **5 Odds Banker**, and **10 Odds Multiplier**).

---

## 🌟 Key Features

- **Official Eighty-Two Animated Badge**:
  - Embedded zero-dependency SVG component with 5 synchronized CSS keyframe animations (rotations, atomic orange rim pulses, core glow).
- **Two-Stage Crawling Architecture**:
  - **Stage 1 (Index / Fixtures List)**: Scrapes all daily fixture rows from `https://www.statarea.com/predictions` including kickoff time, competition, country, home/away teams, tip, 11 probability coefficients (1, X, 2, HT 1/X/2, Over/Under 1.5/2.5/3.5, BTS, OTS), and community voting statistics.
  - **Stage 2 (Deep Extraction)**: Visits each fixture's comparison endpoint (`/compare/teams/...`) to extract complete team profiles (founded date, country, website, world rank), historical H2H matches with scores and match events, recent form, and match statistics.
- **Multi-Tier Daily Accumulators (`1.5x`, `3x`, `5x`, `10x`) (`statarea_scraper/accumulator_engine.py`)**:
  - **🛡️ 1.5-Odds Ultra Banker**: 2 to 3 highest-confidence banker selections (Over 1.5 $\ge 90\%$, Double Chance $\ge 88\%$) targeting $\sim 1.40\text{x} - 1.80\text{x}$ odds.
  - **🎯 3-Odds Banker**: 3 to 4 balanced selections targeting $\sim 2.80\text{x} - 3.50\text{x}$ odds.
  - **🚀 5-Odds Banker**: 4 to 6 ultra-conservative selections targeting $\sim 4.50\text{x} - 5.50\text{x}$ odds.
  - **💎 10-Odds Multiplier**: 5 to 8 safe selections targeting $\sim 8.50\text{x} - 12.50\text{x}$ odds.
  - **Dynamic H2H Recency**: Filters historical records to matches from $\ge 2023$ only.
  - **Automatic Downgrades**: High-risk Straight Wins automatically downgraded to Double Chance.
  - **Cup Squad Rotation Penalty**: $-15\%$ confidence penalty applied to Cup and Friendly matches.
- **⚡ Real-Time Live Score Tracking & Auto-Settlement (`statarea_scraper/results_tracker.py`)**:
  - Pure real-world live match scores and in-play status scraped from Statarea with 30s auto-refresh in the web dashboard.
  - Automatic settlement across all 4 daily slips with realtime P&L and ROI tracking in `results_ledger.json`.
- **Interactive Web Dashboard (`dashboard.py`)**:
  - Real-time Tailwind CSS dark-mode dashboard at `http://localhost:5000` with 4-tier slip selector, live score sync, searchable match tables, and P&L analytics.
- **Automated OS Scheduling**:
  - Windows Task Scheduler task `StatareaDailyPredictions` configured to run `run_daily.bat` every morning at **07:00 AM**.

---

## 📁 Project Structure

```text
statarea-scraper/
├── statarea_scraper/
│   ├── __init__.py              # Package exports
│   ├── config.py                # URLs, headers, rate-limiting & retry settings
│   ├── models.py                # Dataclass models (MatchFixture, TeamInfo, etc.)
│   ├── client.py                # Resilient HTTP client with retry & polite pacing
│   ├── parser.py                # HTML BeautifulSoup parsing routines
│   ├── exporter.py              # JSON and summary CSV persistence
│   ├── analytics_exporter.py    # Relational ML-ready CSV exporter
│   ├── accumulator_engine.py    # Multi-Market 5-Odds Accumulator Slip Builder
│   └── scraper.py               # Main two-stage crawler coordinator
├── tests/
│   ├── test_parser.py           # Automated unit tests for parsers
│   ├── test_analytics_exporter.py # Unit tests for relational analytics exporter
│   └── test_accumulator_engine.py # Unit tests for 5-odds accumulator engine
├── output/                      # Scraped datasets & betting tickets
│   ├── fixtures_summary.json    # Hierarchical JSON export
│   ├── fixtures_summary.csv     # Flattened summary CSV export
│   ├── analysis_fixtures_today.csv # Normalized match & odds dataset
│   ├── analysis_h2h_records.csv # Expanded historical H2H records (688+ matches)
│   ├── analysis_team_metrics.csv# Aggregated club stats, form, & H2H metrics
│   ├── daily_5odds_slip.json    # 5-Odds Banker & Value accumulator slips (JSON)
│   └── daily_5odds_slip.txt     # Formatted daily betting ticket table (TXT)
├── main.py                      # CLI entry point
├── requirements.txt             # Python dependencies
└── README.md                    # Documentation
```

---

## 🚀 Quickstart & Usage

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Run Test Verification (3 Fixtures)

```bash
python main.py --test
```

### 3. Run Full Crawl for Today's Matches

```bash
python main.py
```

### 4. Custom CLI Options

```bash
# Scrape a specific date with a limit of 10 matches
python main.py --date 2026-08-26 --limit 10

# Customize polite request pacing (1.5s to 3.0s delay)
python main.py --min-delay 1.5 --max-delay 3.0

# Specify custom output directory and enable verbose debugging
python main.py --output-dir my_data -v
```

---

## 📊 Output Data Schema

### 1. JSON (`output/fixtures_summary.json`)
```json
[
  {
    "fixture": {
      "match_id": "1713582",
      "date": "2026-08-26",
      "time": "20:00",
      "competition": "LALIGA",
      "country": "Spain",
      "home_team": "Real Madrid",
      "away_team": "Real Sociedad",
      "tip": "1",
      "comparison_url": "https://www.statarea.com/compare/teams/Real+Madrid (Spain)/Real+Sociedad (Spain)",
      "odds": {
        "coef_1": 68,
        "coef_x": 24,
        "coef_2": 8,
        "coef_ht1": 49,
        "coef_htx": 35,
        "coef_ht2": 16,
        "coef_o15": 92,
        "coef_o25": 67,
        "coef_o35": 45,
        "coef_bts": 63,
        "coef_ots": 37
      },
      "user_votes": {
        "vote_1": 39,
        "vote_x": 3,
        "vote_2": 5,
        "likes": 25,
        "dislikes": 3
      }
    },
    "home_team_info": {
      "name": "Real Madrid",
      "official_name": "Real Madrid Club de Fútbol",
      "found": "6 March 1902",
      "country": "Spain",
      "website": "http://www.realmadrid.com",
      "world_rank": 7
    },
    "away_team_info": {
      "name": "Real Sociedad",
      "official_name": "Real Sociedad de Fútbol, S.A.D.",
      "found": "7 September 1909",
      "country": "Spain",
      "website": "http://www.realsociedad.com",
      "world_rank": 93
    },
    "h2h_matches": [
      {
        "date": "2026-02-14",
        "competition": "Spain - Laliga 2025/2026",
        "home_team": "Real Madrid",
        "away_team": "Real Sociedad",
        "home_goals": "4",
        "away_goals": "1",
        "half_time_score": "1-3",
        "events": [
          "[goal] 5' Gonzalo Garcia",
          "[ycard] 20' Dean Huijsen",
          "[penalty] 21' Mikel Oyarzabal"
        ]
      }
    ]
  }
]
```

### 2. CSV (`output/fixtures_summary.csv`)
Columns:
`match_id, date, time, country, competition, home_team, away_team, tip, coef_1, coef_x, coef_2, coef_ht1, coef_htx, coef_ht2, coef_o15, coef_o25, coef_o35, coef_bts, coef_ots, vote_1, vote_x, vote_2, likes, dislikes, home_country, home_world_rank, away_country, away_world_rank, h2h_matches_count, latest_h2h_date, latest_h2h_score, comparison_url`

## ⏰ Automated Midnight Updates (12:00 AM Daily)

Onítẹ́tẹ́ features two zero-maintenance methods to automatically scrape today's matches and regenerate **1.5x, 3x, 5x, and 10x slips** every day at **12:00 AM Midnight**:

### 1. Dashboard Embedded Auto-Scheduler (`dashboard.py`)
- If the web dashboard is running on your machine (`python main.py --serve`), a lightweight background daemon automatically detects the clock turning **00:00 (12:00 AM)**.
- It settles previous scores into the results ledger, crawls all fresh fixtures for the new calendar day, recalculates the multi-tier accumulator tickets, and auto-refreshes the dashboard in realtime.
- An animated status badge in the header shows: `Auto: 12:00 AM Daily`.

### 2. GitHub Actions Cloud Cron (`.github/workflows/daily_scrape.yml`)
- Runs automatically in the cloud every day at **00:00 UTC (12:00 AM)** even if your local computer is powered off.
- Automatically settles scores, runs `python main.py`, and commits the freshly generated JSON/CSV datasets directly back to your repository with `[skip ci]`.
- Can also be triggered manually anytime via GitHub's **Actions** tab (`workflow_dispatch`).

---

## 🧪 Running Unit Tests

```bash
python -m unittest discover tests
```

