"""Main orchestrator for two-stage crawling of Statarea soccer predictions and H2H statistics."""

import concurrent.futures
import logging
import threading
from typing import List, Optional, Callable
from tqdm import tqdm

from .config import PREDICTIONS_URL, DEFAULT_MIN_DELAY, DEFAULT_MAX_DELAY, DEFAULT_MAX_WORKERS
from .client import StatareaClient
from .parser import StatareaParser
from .exporter import StatareaExporter
from .analytics_exporter import AnalyticsExporter
from .accumulator_engine import AccumulatorEngine
from .models import MatchFixture, DeepMatchData

logger = logging.getLogger(__name__)


class StatareaScraper:
    """Two-Stage Scraper for Statarea match predictions and Head-to-Head statistics."""

    def __init__(
        self,
        min_delay: float = DEFAULT_MIN_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        max_workers: int = DEFAULT_MAX_WORKERS,
        output_dir: str = "output",
    ):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_workers = max_workers
        self.output_dir = output_dir
        self.client = StatareaClient(min_delay=min_delay, max_delay=max_delay)
        self.parser = StatareaParser()
        self.exporter = StatareaExporter(output_dir=output_dir)
        self.analytics_exporter = AnalyticsExporter(output_dir=output_dir)
        self.accumulator_engine = AccumulatorEngine(output_dir=output_dir)

    def scrape_fixtures_list(self, date_str: Optional[str] = None) -> List[MatchFixture]:
        """
        Stage 1: Fetch and parse the main predictions list for today or a specific date.
        
        Args:
            date_str: Optional date in YYYY-MM-DD format
            
        Returns:
            List of MatchFixture objects
        """
        if date_str:
            url = f"{PREDICTIONS_URL}/date/{date_str}/competition"
        else:
            url = PREDICTIONS_URL

        logger.info(f"Stage 1: Fetching predictions list from {url}...")
        html = self.client.get(url, apply_delay=False)
        if not html:
            logger.error("Failed to retrieve predictions index page.")
            return []

        fixtures = self.parser.parse_predictions_page(html, default_date=date_str or "")
        return fixtures

    def scrape_match_details(self, fixture: MatchFixture) -> DeepMatchData:
        """
        Stage 2: Fetch and parse deep comparison data for a single fixture.
        
        Args:
            fixture: MatchFixture object
            
        Returns:
            DeepMatchData object
        """
        if not fixture.comparison_url:
            logger.debug(f"No comparison URL for {fixture.home_team} vs {fixture.away_team}")
            return DeepMatchData(fixture=fixture)

        logger.debug(f"Stage 2: Fetching comparison details: {fixture.comparison_url}")
        html = self.client.get(fixture.comparison_url, apply_delay=True)

        if not html:
            logger.warning(
                f"Failed to fetch details for {fixture.home_team} vs {fixture.away_team}. "
                "Returning fixture with basic data."
            )
            return DeepMatchData(fixture=fixture)

        try:
            deep_data = self.parser.parse_comparison_page(html, fixture)
            return deep_data
        except Exception as e:
            logger.error(f"Error parsing comparison page for {fixture.comparison_url}: {e}")
            return DeepMatchData(fixture=fixture)

    def run(
        self,
        date_str: Optional[str] = None,
        limit: Optional[int] = None,
        export: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[DeepMatchData]:
        """
        Run the complete two-stage crawl pipeline with high-speed concurrency.
        
        Args:
            date_str: Optional target date string (YYYY-MM-DD)
            limit: Maximum number of fixtures to process deeply (useful for test runs)
            export: Whether to automatically save output to JSON & CSV
            progress_callback: Optional callback receiving (current_idx, total_matches, match_title)
            
        Returns:
            List of DeepMatchData objects
        """
        # --- Stage 1: Index / Fixtures List ---
        print("\n=======================================================")
        print("   Statarea Soccer Match Predictions & H2H Scraper     ")
        print("=======================================================\n")
        print("[+] Stage 1: Crawling fixture predictions...")

        fixtures = self.scrape_fixtures_list(date_str)
        total_found = len(fixtures)
        print(f"[OK] Stage 1 Complete: Found {total_found} fixtures.")

        if not fixtures:
            print("[!] No fixtures found to scrape.")
            return []

        if limit is not None and limit > 0:
            fixtures = fixtures[:limit]
            print(f"[*] Processing limit applied: crawling first {len(fixtures)} fixtures...")

        # --- Stage 2: Deep Extraction (Concurrent Worker Pool) ---
        workers = min(self.max_workers, max(1, len(fixtures)))
        print(f"\n[+] Stage 2: Concurrent deep scraping H2H & Team Stats ({len(fixtures)} matches with {workers} workers)...")
        results: List[DeepMatchData] = [None] * len(fixtures)
        total_count = len(fixtures)
        completed_count = 0
        lock = threading.Lock()

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_idx = {
                executor.submit(self.scrape_match_details, fix): i
                for i, fix in enumerate(fixtures)
            }

            with tqdm(
                total=total_count,
                desc="Deep Crawl Progress",
                unit="match",
                ncols=80,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            ) as pbar:
                for future in concurrent.futures.as_completed(future_to_idx):
                    i = future_to_idx[future]
                    fix = fixtures[i]
                    try:
                        deep_info = future.result()
                    except Exception as e:
                        logger.error(f"Error scraping match {fix.home_team} vs {fix.away_team}: {e}")
                        deep_info = DeepMatchData(fixture=fix)

                    results[i] = deep_info
                    with lock:
                        completed_count += 1
                        done_now = completed_count

                    pbar.update(1)
                    pbar.set_postfix_str(f"{fix.home_team[:12]} vs {fix.away_team[:12]}")
                    if progress_callback:
                        try:
                            progress_callback(done_now, total_count, f"{fix.home_team} vs {fix.away_team}")
                        except Exception:
                            pass

        print(f"\n[OK] Stage 2 Complete: Successfully processed {len(results)} matches.")

        # --- Output & Data Persistence ---
        if export and results:
            json_file = self.exporter.export_json(results)
            csv_file = self.exporter.export_csv(results)
            
            # Analytics relational datasets
            raw_dicts = [r.to_dict() for r in results]
            analytics_files = self.analytics_exporter.process_data(raw_dicts)

            # Generate 5-Odds Accumulator Slip
            slip_result = self.accumulator_engine.generate_and_save()

            print("\n[+] Output Data Persistence:")
            print(f"    - JSON Raw:         {json_file}")
            print(f"    - CSV Summary:      {csv_file}")
            print("\n[+] ML-Ready Analytical Relational Datasets:")
            print(f"    - Match Metadata:   {analytics_files['fixtures_today']}")
            print(f"    - H2H Records:      {analytics_files['h2h_records']}")
            print(f"    - Team Metrics:     {analytics_files['team_metrics']}")
            print("\n[+] Daily 5-Odds Slip Persistence:")
            print(f"    - Slip JSON:        {slip_result['json_file']}")
            print(f"    - Slip TXT:         {slip_result['txt_file']}")
            print("\n" + slip_result["text_report"])

        return results

    def close(self) -> None:
        """Clean up resources."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
