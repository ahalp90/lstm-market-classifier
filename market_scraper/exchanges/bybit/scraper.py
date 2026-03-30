"""
Bybit Perpetuals scraper.

Combines two API endpoints.

Fetches market data (Open Interest, Long/Short Ratio) from Bybit API.
Handles rate limiting globally across all instances.

Note: Bybit returns data newest-first and paginates backwards in time,
which requires custom batch_scrape logic (overrides base class).
"""

import json
import logging
import time
from typing import Any, ClassVar
from zoneinfo import ZoneInfo

import requests

logger = logging.getLogger(__name__)

from market_scraper.core import (
    BaseScraper,
    DataType,
    DIR_MARKET_DATA,
    unix_ms_to_filename_str,
    get_current_unix_ms,
    calendar_datetime_to_utc_and_unix,
)
from .constants import (
    BybitSymbolType,
    BybitIntervalType,
    BYBIT_SYMBOLS,
    BYBIT_INTERVALS,
    BYBIT_OPEN_INTEREST_ENDPOINT,
    BYBIT_LONG_SHORT_RATIO_ENDPOINT,
    BYBIT_INSTRUMENTS_INFO_ENDPOINT,
    BYBIT_CATEGORY,
    MAX_RECORDS_OPEN_INTEREST,
    MAX_RECORDS_LONG_SHORT_RATIO,
    INTERVAL_TO_BYBIT,
    INTERVAL_DURATION_MS,
    BYBIT_V5_DATA_START_MS,
)


def interpret_bybit_response(response: requests.Response) -> bool:
    """Return True if request successful, else False"""
    # First check HTTP status
    if response.status_code == 403:
        logger.error("IP rate limit exceeded (403). Wait 10+ minutes.")
        return False
    elif response.status_code != 200:
        logger.error("HTTP Error: %d", response.status_code)
        return False

    # Check Bybit's retCode in response body
    try:
        data = response.json()
        ret_code = data.get("retCode", -1)

        if ret_code == 0:
            return True
        else:
            ret_msg = data.get("retMsg", "Unknown error")
            logger.error("Bybit API Error (retCode=%d): %s", ret_code, ret_msg)
            return False
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Error parsing Bybit response: %s", e)
        return False


class BybitScraper(BaseScraper):
    """
    Combined scraper for Bybit market data endpoints.

    - Supports both Open Interest and Long/Short Ratio.
    - Shared rate limiter to avoid 403 bans when running multiple instances.
    - Auto-detection of instrument launch time to prevent 'empty list' errors.
    - Backward pagination (Bybit returns newest-first).

    """

    exchange_name = "bybit"
    base_dir = DIR_MARKET_DATA

    # Bybit returns data newest-first, requiring backward pagination
    pagination_direction = "backward"

    # Global shared rate limit tracker (shared across ALL instances)
    _request_times: ClassVar[list[float]] = []

    # Cache for instrument launch times (shared across ALL instances)
    _launch_time_cache: ClassVar[dict[str, int]] = {}

    def __init__(self,
                 symbol: BybitSymbolType,
                 interval: BybitIntervalType | str,
                 data_type: DataType):
        """
        Initialise Bybit scraper.

        :param symbol: Perpetual contract symbol (e.g., "BTCUSDT")
        :param interval: Data interval (e.g., "15min" or "15m")
        :param data_type: DataType.OPEN_INTEREST or DataType.LONG_SHORT_RATIO
        """
        self.data_type = data_type

        # Configure endpoint and limits based on data type
        if data_type == DataType.OPEN_INTEREST:
            self.endpoint = BYBIT_OPEN_INTEREST_ENDPOINT
            self.max_records_limit = MAX_RECORDS_OPEN_INTEREST
        elif data_type == DataType.LONG_SHORT_RATIO:
            self.endpoint = BYBIT_LONG_SHORT_RATIO_ENDPOINT
            self.max_records_limit = MAX_RECORDS_LONG_SHORT_RATIO

        else:
            raise ValueError(f"BybitScraper does not support data type: {data_type}")

        # Convert shared interval format to Bybit format if needed
        if interval in INTERVAL_TO_BYBIT:
            interval = INTERVAL_TO_BYBIT[interval]

        # Initialise BaseScraper (sets self.symbol, self.interval, and self.data_type)
        super().__init__(symbol, interval, data_type)

    def _validate_params(self) -> None:
        """Validate symbol and interval against Bybit allowed values."""
        if self.symbol not in BYBIT_SYMBOLS:
            raise ValueError(f"Invalid Bybit symbol: {self.symbol}. "
                             f"Allowed: {BYBIT_SYMBOLS}")
        if self.interval not in BYBIT_INTERVALS:
            raise ValueError(f"Invalid Bybit interval: {self.interval}. "
                             f"Allowed: {BYBIT_INTERVALS}")

    def _get_earliest_timestamp(self) -> int:
        """
        Auto-detect the instrument's launch time via API.

        Results are cached to avoid repeated API calls for the same symbol.
        """
        # Check cache first
        if self.symbol in BybitScraper._launch_time_cache:
            return BybitScraper._launch_time_cache[self.symbol]

        url = f"{BYBIT_API_BASE_URL}{BYBIT_INSTRUMENTS_INFO_ENDPOINT}"
        params = {
            "category": BYBIT_CATEGORY,
            "symbol": self.symbol,
            "limit": 1
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                BybitScraper._request_times.append(time.time())

                if response.status_code == 200:
                    data = response.json()
                    items = data.get("result", {}).get("list", [])

                    if items:
                        launch_time_str = items[0].get("launchTime")
                        if launch_time_str:
                            launch_time = int(launch_time_str)
                            BybitScraper._launch_time_cache[self.symbol] = launch_time
                            return launch_time

                logger.warning("Attempt %d/%d failed for launch time lookup",
                               attempt + 1, max_retries)

            except Exception as e:
                logger.warning("Attempt %d/%d error: %s", attempt + 1, max_retries, e)

            if attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))

        logger.warning("Could not auto-detect launch time for %s, using fallback", self.symbol)
        return BYBIT_V5_DATA_START_MS

    def _fetch_data(self,
                    start_time_ms: int | None = None,
                    end_time_ms: int | None = None,
                    limit: int | None = None) -> requests.Response:
        """Make API call to the configured Bybit endpoint."""
        url = f"{BYBIT_API_BASE_URL}{self.endpoint}"

        # Enforce API specific limits
        actual_limit = limit if limit is not None else self.max_records_limit
        if actual_limit > self.max_records_limit:
            actual_limit = self.max_records_limit

        params: dict[str, Any] = {
            "category": BYBIT_CATEGORY,
            "symbol": self.symbol,
            "limit": actual_limit,
        }

        # Bybit uses different parameter names for interval depending on endpoint
        if self.data_type == DataType.OPEN_INTEREST:
            params["intervalTime"] = self.interval
        elif self.data_type == DataType.LONG_SHORT_RATIO:
            params["period"] = self.interval

        if start_time_ms:
            params["startTime"] = start_time_ms
        if end_time_ms:
            params["endTime"] = end_time_ms

        return requests.get(url, params=params, timeout=REQUEST_TIMEOUT)

    def _parse_response(self, response: requests.Response) -> list[dict[str, str]]:
        """Extract data list from response (keeps newest-first order from API)."""
        data = response.json()
        return data.get("result", {}).get("list", [])

    def _get_timestamps_from_data(self, data: list[dict[str, str]]) -> tuple[int, int]:
        """Extract first and last timestamps from chronologically-sorted data."""
        return int(data[0]["timestamp"]), int(data[-1]["timestamp"])

    def _get_next_start_time(self, data: list[dict[str, str]]) -> int:
        """Not used for Bybit (backward pagination), but required by base class."""
        raise NotImplementedError

    def _handle_rate_limit(self, response: requests.Response) -> None:
        """
        Handle rate limiting using a shared ClassVar sliding window.

        This ensures that multiple BybitScraper instances share the same
        rate limit counter (avoid global rate limit ban).
        """
        current_time = time.time()

        # Clean old entries from sliding window
        BybitScraper._request_times = [
            t for t in BybitScraper._request_times
            if current_time - t < RATE_LIMIT_WINDOW_SECONDS
        ]

        # Record this request
        BybitScraper._request_times.append(current_time)

        # Check limit (leave a buffer of 5 requests)
        if len(BybitScraper._request_times) >= MAX_REQUESTS_PER_5_SECONDS - 5:
            oldest = min(BybitScraper._request_times)
            wait_time = RATE_LIMIT_WINDOW_SECONDS - (current_time - oldest) + 0.5

            if wait_time > 0:
                logger.info("[Bybit Rate Limit] %d requests in window. Waiting %.2fs...",
                            len(BybitScraper._request_times), wait_time)
                time.sleep(wait_time)
                BybitScraper._request_times.clear()

        # Handle explicit 403 (IP Ban/Rate Limit)
        if response.status_code == 403:
            logger.error("CRITICAL: Bybit 403 Rate Limit Exceeded. Pausing for 60 seconds...")
            time.sleep(60)
            BybitScraper._request_times.clear()

    def _interpret_response(self, response: requests.Response) -> bool:
        """Check if Bybit response was successful."""
        return interpret_bybit_response(response)

    def _is_rate_limit_error(self, response: requests.Response) -> bool:
        """Check if response indicates rate limiting."""
        return response.status_code == 403


    # OVERRIDE BATCH_SCRAPE FOR BACKWARD PAGINATION
    # ******

    def batch_scrape(self,
                     limit: int | None = None,
                     start_date_str: str | None = None,
                     start_time_str: str | None = None,
                     end_date_str: str | None = None,
                     end_time_str: str | None = None,
                     tz: ZoneInfo = ZoneInfo("UTC")) -> list[dict[str, str]]:
        """
        Batch scrape data with backward pagination (Bybit returns newest-first).

        Starts from end_time and works backwards to start_time.

        :return: List of all data records in chronological order (oldest first)
        """
        request_start_time = get_current_unix_ms()

        # Determine end time (where we start scraping from)
        if end_date_str:
            _, end_scrape_unix_time = calendar_datetime_to_utc_and_unix(end_date_str, end_time_str, tz)
        else:
            end_scrape_unix_time = request_start_time

        # Determine start time (where we stop scraping)
        if start_date_str:
            _, start_scrape_unix_time = calendar_datetime_to_utc_and_unix(start_date_str, start_time_str, tz)
        else:
            start_scrape_unix_time = self._get_earliest_timestamp()

        # Current end time for pagination (moves backward)
        current_end_time = end_scrape_unix_time
        all_data: list[dict[str, str]] = []
        requests_count = 0

        # Log progress header
        logger.info("=" * 60)
        logger.info("Starting batch scrape: %s %s %s (%s)",
                    self.exchange_name, self.symbol, self.interval, self.data_type)
        logger.info("Date range: %s to %s",
                    unix_ms_to_filename_str(start_scrape_unix_time),
                    unix_ms_to_filename_str(end_scrape_unix_time))
        logger.info("=" * 60)

        while current_end_time > start_scrape_unix_time:
            response = self._fetch_with_retry(end_time_ms=current_end_time, limit=limit)
            requests_count += 1

            if response is None:
                oldest_ts = int(all_data[0]["timestamp"]) if all_data else current_end_time
                logger.error("Error occurred. Oldest successful timestamp: %s",
                             unix_ms_to_filename_str(oldest_ts))
                break

            # Parse response (newest-first from API)
            batch_data = self._parse_response(response)

            if not batch_data:
                logger.info("No more data available.")
                break

            # Get oldest timestamp from this batch (last item since newest-first)
            oldest_in_batch = int(batch_data[-1]["timestamp"])

            # Progress update every 10 requests
            if requests_count % 10 == 0:
                progress_pct = ((end_scrape_unix_time - oldest_in_batch) /
                                (end_scrape_unix_time - start_scrape_unix_time)) * 100
                logger.info("Progress: %.1f%% | Records: %d | Requests: %d",
                            progress_pct, len(all_data), requests_count)

            # Prepend batch to all_data (since we're going backwards)
            # batch_data is newest-first, so reverse it before prepending
            all_data = list(reversed(batch_data)) + all_data

            # Move end time backward for next request (1ms before oldest ensures no gap)
            current_end_time = oldest_in_batch - 1

            # NB: *Don't* break when len(batch_data) < limit, because Bybit may gaps.
            # A partial batch probably means it's one of these gaps, not the beginning of data.
            # The while loop and empty batch check handle actual scrape end.

        # Trim any records before start_scrape_unix_time
        all_data = [d for d in all_data if int(d["timestamp"]) >= start_scrape_unix_time]

        # Deduplicate (handles API returning duplicate records)
        all_data = self._deduplicate(all_data)

        # Log completion
        elapsed = (get_current_unix_ms() - request_start_time) / 1000
        logger.info("=" * 60)
        logger.info("Batch scrape complete!")
        logger.info("Total records: %d", len(all_data))
        logger.info("Total requests: %d", requests_count)
        logger.info("Time elapsed: %.1fs", elapsed)
        logger.info("=" * 60)

        return all_data


# CONVENIENCE FUNCTIONS
# ******

def get_and_save_bybit_data(symbol: BybitSymbolType,
                            interval: BybitIntervalType | str,
                            data_type: DataType,
                            batch_scrape: bool = False,
                            limit: int | None = None,
                            start_date_str: str | None = None,
                            end_date_str: str | None = None,
                            create_numbered_version_if_exists: bool = False) -> bool:
    """
    Convenience function to fetch and save Bybit data.

    :param symbol: Trading pair (e.g., "BTCUSDT")
    :param interval: Data interval (e.g., "15m" or "15min")
    :param data_type: DataType.OPEN_INTEREST or DataType.LONG_SHORT_RATIO
    :param batch_scrape: If True, scrape full history; otherwise single fetch
    :param limit: Number of records per request
    :param start_date_str: Start date for batch scrape (YYYY-MM-DD)
    :param end_date_str: End date for batch scrape (YYYY-MM-DD)
    :param create_numbered_version_if_exists: Create versioned file if exists
    :return: True if saved successfully
    """
    scraper = BybitScraper(symbol, interval, data_type)
    return scraper.scrape_and_save(
        batch=batch_scrape,
        limit=limit,
        start_date_str=start_date_str,
        end_date_str=end_date_str,
        tz=ZoneInfo("UTC"),
        create_numbered_version_if_exists=create_numbered_version_if_exists,
    )