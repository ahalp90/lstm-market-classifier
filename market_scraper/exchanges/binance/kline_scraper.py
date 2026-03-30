"""
Binance Kline (candlestick) scraper. Fetches OHLCV data from the Binance spot API.
"""

import datetime
import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

from market_scraper.core import (
    BaseScraper,
    DIR_MARKET_DATA,
    DataType,
)
from .constants import (
    BinanceSymbolType,
    BinanceIntervalType,
    BINANCE_SYMBOLS,
    BINANCE_INTERVALS,
    BINANCE_API_BASE_URL,
    BINANCE_KLINE_ENDPOINT,
    MAX_RECORDS_PER_REQUEST,
    MAX_REQUESTS_PER_MINUTE,
    REQUEST_TIMEOUT,
    BinanceKlineRaw,
    KlineIndex,
)


def interpret_binance_status_code(response: requests.Response) -> bool:
    """
    Interpret Binance API response status code.

    :param response: requests.Response object
    :return: True if request was successful (200), False otherwise
    """
    rsc = response.status_code

    if rsc == 200:
        return True
    elif rsc == 403:
        logger.error("WAF Limit (Web Application Firewall) has been violated.")
    elif rsc == 409:
        logger.error("cancelReplace order partially succeeded. "
                     "Cancellation of the order failed but the new order placement succeeded.")
    elif rsc == 429:
        logger.error("Request rate limit exceeded.")
    elif rsc == 418:
        logger.error("IP has been auto-banned for continuing to send requests after receiving 429 codes.")
    elif rsc // 100 == 5:  # 5xx series
        logger.error("Internal Server Error: The issue is on Binance's side. "
                     "It is important to NOT treat this as a failure operation; "
                     "the execution status is UNKNOWN and could have been a success.")
    else:
        logger.error("Unknown error: HTTP %d", rsc)
    return False


class BinanceKlineScraper(BaseScraper):
    """
    Scraper for Binance kline/candlestick data.

    Use core market_scraper methods:
        # Single fetch
        data, success = scraper.fetch(args)
        # Batch scrape
        data = scraper.batch_scrape(args)
        # Scrape and save
        scraper.scrape_and_save(args)
    """

    exchange_name = "binance"
    base_dir = DIR_MARKET_DATA

    def __init__(self,
                 symbol: BinanceSymbolType,
                 interval: BinanceIntervalType):
        """
        Initialise Binance kline scraper.

        :param symbol: Trading pair
        :param interval: Kline interval
        """
        super().__init__(symbol, interval, DataType.KLINE)
    
    def _validate_params(self) -> None:
        """Validate symbol and interval against Binance allowed values."""
        if self.symbol not in BINANCE_SYMBOLS:
            raise ValueError(f"Invalid Binance symbol: {self.symbol}. "
                             f"Allowed: {BINANCE_SYMBOLS}")
        if self.interval not in BINANCE_INTERVALS:
            raise ValueError(f"Invalid Binance interval: {self.interval}. "
                             f"Allowed: {BINANCE_INTERVALS}")
    
    def _fetch_data(self,
                    start_time_ms: int | None = None,
                    end_time_ms: int | None = None,
                    limit: int | None = MAX_RECORDS_PER_REQUEST) -> requests.Response:
        """Make API call to Binance klines endpoint."""
        url = f"{BINANCE_API_BASE_URL}{BINANCE_KLINE_ENDPOINT}"
        
        # Validate limit
        if limit is not None and not 1 <= limit <= MAX_RECORDS_PER_REQUEST:
            raise ValueError(f"Invalid limit: {limit}. Must be 1-{MAX_RECORDS_PER_REQUEST}")
        
        params: dict[str, Any] = {
            "symbol": self.symbol,
            "interval": self.interval,
            "limit": limit or MAX_RECORDS_PER_REQUEST,
        }
        
        if start_time_ms:
            params["startTime"] = start_time_ms
        if end_time_ms:
            params["endTime"] = end_time_ms
        
        return requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    
    def _parse_response(self, response: requests.Response) -> list[BinanceKlineRaw]:
        """Extract kline list from response."""
        return response.json()
    
    def _get_timestamps_from_data(self, data: list[BinanceKlineRaw]) -> tuple[int, int]:
        """Extract first open time and last close time from kline data."""
        return data[0][KlineIndex.OPEN_TIME], data[-1][KlineIndex.CLOSE_TIME]
    
    def _interpret_response(self, response: requests.Response) -> bool:
        """Check if Binance response was successful."""
        return interpret_binance_status_code(response)
    
    def _handle_rate_limit(self, response: requests.Response) -> None:
        """Handle Binance rate limiting based on response headers."""
        minute_usage_str = response.headers.get("x-mbx-used-weight-1m", "0")
        minute_usage = int(minute_usage_str)
        
        if minute_usage > MAX_REQUESTS_PER_MINUTE - 2 or response.status_code == 429:
            date_string = response.headers.get("Date", "")
            if date_string:
                # Parse: 'Tue, 04 Nov 2025 03:21:16 GMT'
                dt = datetime.datetime.strptime(date_string, "%a, %d %b %Y %H:%M:%S %Z")
                seconds_to_wait = 60 - dt.second
            else:
                seconds_to_wait = 60
            
            logger.info("%d of max %d requests in last minute.",
                        minute_usage, MAX_REQUESTS_PER_MINUTE)
            logger.info("Pausing for %d seconds...", seconds_to_wait)
            time.sleep(seconds_to_wait)

    def _get_earliest_timestamp(self) -> int:
        """Get earliest available kline timestamp for this symbol/interval."""
        response = self._fetch_with_retry(start_time_ms=1, limit=1)
        if response is not None:
            data = self._parse_response(response)
            return data[0][KlineIndex.OPEN_TIME]
        else:
            raise ValueError(f"Failed to retrieve earliest kline for {self.symbol} {self.interval}")

    def _get_next_start_time(self, data: list[BinanceKlineRaw]) -> int:
        """Get next start time from last close time + 1ms."""
        last_close_time = data[-1][KlineIndex.CLOSE_TIME]
        return last_close_time + 1
    
    def _is_rate_limit_error(self, response: requests.Response) -> bool:
        """Check if response indicates rate limiting."""
        return response.status_code == 429

    def _deduplicate(self, data: list[BinanceKlineRaw]) -> list[BinanceKlineRaw]:
        """
        Remove duplicate records from list-based kline data.

        Override of base class method to preserve list format (not convert to dicts).
        """
        if not data:
            return data
        import pandas as pd
        df = pd.DataFrame(data)
        df = df.drop_duplicates()
        return df.values.tolist()


