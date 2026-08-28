#!/usr/bin/env python3
"""
Onítẹ́tẹ́ - AI Soccer Prediction & Multi-Tier (1.5x, 3x, 5x, 10x) Accumulator Engine.
Powered by Eighty-Two AI Engine.

Usage Examples:
    # Quick 3-fixture test run:
    python main.py --test

    # Full scrape & accumulator generation:
    python main.py

    # Launch the interactive web dashboard on http://localhost:5000:
    python main.py --serve

    # Re-generate 1.5x, 3x, 5x, 10x slips instantly from existing data:
    python main.py --slip-only

    # Fetch live scores and settle today's slips:
    python main.py --update-scores
"""

import argparse
import logging
import sys
from statarea_scraper import StatareaScraper
from statarea_scraper.config import DEFAULT_MIN_DELAY, DEFAULT_MAX_DELAY


def setup_logging(verbose: bool = False) -> None:
    """Configure logging format and levels."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Suppress overly noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Onítẹ́tẹ́: AI soccer predictions, dynamic H2H recency filtering, and 1.5x/3x/5x/10x accumulator engine.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode: scrapes only the first 3 fixtures for quick verification.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of fixtures to process deeply.",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date for fixtures in YYYY-MM-DD format (default: today).",
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=DEFAULT_MIN_DELAY,
        help="Minimum polite delay between HTTP requests in seconds.",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=DEFAULT_MAX_DELAY,
        help="Maximum polite delay between HTTP requests in seconds.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory path to save JSON and CSV output files.",
    )
    parser.add_argument(
        "--slip-only",
        action="store_true",
        help="Re-generate and display 1.5x, 3x, 5x, and 10x accumulator tickets from existing analytical data without re-crawling.",
    )
    parser.add_argument(
        "--update-scores",
        action="store_true",
        help="Fetch live/finished match scores from Statarea and settle today's accumulator slips.",
    )
    parser.add_argument(
        "--analytics",
        action="store_true",
        help="Display historical Daily, Weekly, and Monthly performance & ROI analytics in terminal.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Launch the interactive web dashboard on http://localhost:5000 and open in browser.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable detailed debug logging.",
    )
    return parser.parse_args()


def main() -> int:
    """CLI execution entrypoint."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    args = parse_args()
    setup_logging(verbose=args.verbose)

    # Handle update-scores mode
    if args.update_scores:
        from statarea_scraper import ResultsTracker
        tracker = ResultsTracker(output_dir=args.output_dir)
        try:
            res = tracker.settle_today_slips()
            print(f"\n[+] Score settlement complete. Updated records: {res.get('total_records', 0)}")
            return 0
        except Exception as e:
            logging.error(f"Error settling scores: {e}")
            return 1

    # Handle analytics mode
    if args.analytics:
        from statarea_scraper import ResultsTracker
        tracker = ResultsTracker(output_dir=args.output_dir)
        try:
            an = tracker.compute_analytics()
            sum_data = an.get("summary", {})
            print("\n" + "=" * 65)
            print("         📊 ONÍTẸ́TẸ́ HISTORICAL PERFORMANCE ANALYTICS         ")
            print("=" * 65)
            print(f" Total Slips:    {sum_data.get('total_slips')} (Won: {sum_data.get('won_count')} | Lost: {sum_data.get('lost_count')})")
            print(f" Ticket Hit Rate:{sum_data.get('win_rate')}%")
            print(f" Net Profit:     {'+' if sum_data.get('net_profit', 0) >= 0 else ''}{sum_data.get('net_profit')} units (1u stake)")
            print(f" Lifetime ROI:   {sum_data.get('roi_pct')}%")
            print(f" Current Streak: {sum_data.get('current_streak')}")
            print("=" * 65 + "\n")
            return 0
        except Exception as e:
            logging.error(f"Error computing analytics: {e}")
            return 1

    # Handle serve mode
    if args.serve:
        from dashboard import start_server
        try:
            start_server(port=5000, open_browser=True)
            return 0
        except Exception as e:
            logging.error(f"Error running dashboard server: {e}")
            return 1

    # Handle slip-only mode
    if args.slip_only:
        from statarea_scraper import AccumulatorEngine
        engine = AccumulatorEngine(output_dir=args.output_dir)
        try:
            res = engine.generate_and_save()
            print("\n" + res["text_report"])
            return 0
        except Exception as e:
            logging.error(f"Error generating accumulator slip: {e}")
            return 1

    limit = args.limit
    if args.test:
        limit = 3
        print("\n[i] Test Mode Active: Will scrape the first 3 fixtures.")

    scraper = StatareaScraper(
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        output_dir=args.output_dir,
    )

    try:
        results = scraper.run(
            date_str=args.date,
            limit=limit,
            export=True,
        )
        if not results:
            print("[!] Scrape finished with 0 results.")
            return 1

        print(f"\n[OK] Successfully completed! {len(results)} matches saved.")
        return 0
    except KeyboardInterrupt:
        print("\n[!] Crawl interrupted by user.")
        return 130
    except Exception as e:
        logging.error(f"Fatal error during scraping: {e}", exc_info=True)
        return 1
    finally:
        scraper.close()


if __name__ == "__main__":
    sys.exit(main())
