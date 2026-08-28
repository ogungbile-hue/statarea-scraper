"""Configuration constants for the Statarea scraper."""

BASE_URL = "https://www.statarea.com"
PREDICTIONS_URL = f"{BASE_URL}/predictions"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.statarea.com/",
    "Sec-Ch-Ua": '"Not-A.Brand";v="99", "Chromium";v="124", "Google Chrome";v="124"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# Concurrency and High-Speed Pacing
DEFAULT_MIN_DELAY = 0.15
DEFAULT_MAX_DELAY = 0.35
DEFAULT_MAX_WORKERS = 6
DEFAULT_POOL_SIZE = 25

# Retry configuration
MAX_RETRIES = 3
BACKOFF_FACTOR = 1.2
RETRY_STATUS_CODES = [429, 500, 502, 503, 504]
REQUEST_TIMEOUT = 12
