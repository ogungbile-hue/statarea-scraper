"""Resilient HTTP client with retry logic, exponential backoff, and polite rate limiting."""

import logging
import random
import time
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import (
    DEFAULT_HEADERS,
    DEFAULT_MIN_DELAY,
    DEFAULT_MAX_DELAY,
    MAX_RETRIES,
    BACKOFF_FACTOR,
    RETRY_STATUS_CODES,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)


class StatareaClient:
    """HTTP Client for Statarea with session persistence, retries, and rate limiting."""

    def __init__(
        self,
        min_delay: float = DEFAULT_MIN_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = REQUEST_TIMEOUT,
    ):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.headers = headers or DEFAULT_HEADERS.copy()

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Setup standard urllib3 retry strategy as first line of defense
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=BACKOFF_FACTOR,
            status_forcelist=RETRY_STATUS_CODES,
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _polite_delay(self, custom_delay: Optional[float] = None) -> None:
        """Wait politely between requests to avoid overloading the server."""
        if custom_delay is not None:
            delay = custom_delay
        else:
            delay = random.uniform(self.min_delay, self.max_delay)
        
        logger.debug(f"Pacing: waiting {delay:.2f}s before next request...")
        time.sleep(delay)

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        apply_delay: bool = True,
        max_attempts: int = MAX_RETRIES,
    ) -> Optional[str]:
        """
        Fetch HTML content from a URL with retry logic and exponential backoff.
        
        Args:
            url: Target URL string
            params: Optional query parameters
            apply_delay: Whether to enforce polite rate limiting before fetching
            max_attempts: Maximum number of manual retry attempts
            
        Returns:
            HTML text if successful, or None if all attempts failed.
        """
        if apply_delay:
            self._polite_delay()

        attempt = 0
        current_backoff = BACKOFF_FACTOR

        while attempt < max_attempts:
            attempt += 1
            try:
                logger.debug(f"GET {url} (Attempt {attempt}/{max_attempts})")
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    return response.text
                elif response.status_code in RETRY_STATUS_CODES:
                    logger.warning(
                        f"Received HTTP {response.status_code} from {url}. "
                        f"Backing off for {current_backoff:.2f}s..."
                    )
                    time.sleep(current_backoff)
                    current_backoff *= 2
                else:
                    logger.error(
                        f"Unexpected HTTP {response.status_code} for {url}."
                    )
                    return None

            except (requests.exceptions.RequestException, Exception) as e:
                logger.warning(
                    f"Request failed for {url} on attempt {attempt}: {e}. "
                    f"Retrying in {current_backoff:.2f}s..."
                )
                time.sleep(current_backoff)
                current_backoff *= 2

        logger.error(f"Failed to fetch {url} after {max_attempts} attempts.")
        return None

    def close(self) -> None:
        """Close the underlying session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
