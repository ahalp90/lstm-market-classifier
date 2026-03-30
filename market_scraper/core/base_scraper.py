"""
Abstract base class for market data scrapers.

Gives shared methods, classes and constants for:
* Batch scraping with pagination
* Rate limit handling
* Progress reporting
* Data saving
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Literal
from zoneinfo import ZoneInfo

import pandas as pd
import requests

logger = logging.getLogger(__name__)

from .utilities import (
    calendar_datetime_to_utc_and_unix,
    unix_ms_to_filename_str,
    get_current_unix_ms,
    save_json_data,
    create_timestamped_json_filepath,
)


class BaseScraper(ABC):
    """
    Abstract base class for exchange-specific scrapers.

    Subclasses must implement:
    - _fetch_data(): Make the actual API call
    - _parse_response(): Extract data list from response
    - _get_timestamps_from_data(): Extract first/last timestamps from data
    - _interpret_response(): Check if response was successful
    - _handle_rate_limit(): Handle rate limiting
    - _get_earliest_timestamp(): Get earliest available data timestamp

    Pagination works by:
        Default batch_scrape() uses forward pagination (oldest to newest).
        Set pagination_direction = "backward" and override batch_scrape() for
        exchanges returning newest-first (e.g., Bybit).
    """

    # To be set by subclasses
    exchange_name: str = "unknown"
    base_dir: str = ""

    # Pagination direction: "forward" (oldest to newest) or "backward" (newest to oldest)
    pagination_direction: Literal["forward", "backward"] = "forward"

    def __init__(self, symbol: str, interval: str, data_type: "DataType"):
        """
        Initialise scraper with symbol, interval, and data type.

        :param symbol: Trading pair symbol (e.g., "BTCUSDT")
        :param interval: Time interval (e.g., "15m", "1h")
        :param data_type: Type of data being scraped (DataType enum)
        """
        self.symbol = symbol
        self.interval = interval
        self.data_type = data_type
        self._validate_params()
    
    @abstractmethod
    def _validate_params(self) -> None:
        """Validate symbol and interval against allowed values."""
        pass
    
    @abstractmethod
    def _fetch_data(self,
                    start_time_ms: int | None = None,
                    end_time_ms: int | None = None,
                    limit: int | None = None) -> requests.Response:
        """
        Make the actual API call.
        
        :param start_time_ms: Start timestamp in milliseconds
        :param end_time_ms: End timestamp in milliseconds
        :param limit: Number of records to fetch
        :return: requests.Response object
        """
        pass
    
    @abstractmethod
    def _parse_response(self, response: requests.Response) -> list[Any]:
        """
        Extract data list from API response.
        
        :param response: requests.Response object
        :return: List of data records
        """
        pass
    
    @abstractmethod
    def _get_timestamps_from_data(self, data: list[Any]) -> tuple[int, int]:
        """
        Extract first and last timestamps from data.
        
        :param data: List of data records
        :return: Tuple of (first_timestamp_ms, last_timestamp_ms)
        """
        pass
    
    @abstractmethod
    def _interpret_response(self, response: requests.Response) -> bool:
        """
        Check if API response indicates success.
        
        :param response: requests.Response object
        :return: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def _handle_rate_limit(self, response: requests.Response) -> None:
        """
        Handle rate limiting - wait if necessary.
        
        :param response: requests.Response object
        """
        pass
    
    @abstractmethod
    def _get_earliest_timestamp(self) -> int:
        """
        Get the earliest available timestamp for this symbol/interval.
        
        :return: Unix timestamp in milliseconds
        """
        pass
    
    @abstractmethod
    def _get_next_start_time(self, data: list[Any]) -> int:
        """
        Calculate the next start time for pagination.
        
        :param data: List of data records from current batch
        :return: Unix timestamp in milliseconds for next batch start
        """
        pass
    
    def _is_rate_limit_error(self, response: requests.Response) -> bool:
        """
        Check if response indicates a rate limit error.

        Override in subclass if needed.

        :param response: requests.Response object
        :return: True if rate limited
        """
        return response.status_code == 429

    def _deduplicate(self, data: list[Any]) -> list[Any]:
        """
        Remove duplicate records from data using pandas.

        Override in subclass if data format requires different handling
        (e.g., list-based data that needs column names).

        :param data: List of data records (dicts or lists)
        :return: Deduplicated list
        """
        if not data:
            return data
        df = pd.DataFrame(data)
        df = df.drop_duplicates()
        return df.to_dict('records')

    def _fetch_with_retry(self,
                          start_time_ms: int | None = None,
                          end_time_ms: int | None = None,
                          limit: int | None = None,
                          max_retries: int = 3,
                          base_delay: float = 2.0) -> requests.Response | None:
        """
        Fetch data with automatic retry on fail.

        :param max_retries: Maximum number of attempts
        :param base_delay: Base delay for exponential backoff
        :return: Response if successful, None if all retries exhausted
        """
        for attempt in range(max_retries):
            try:
                response = self._fetch_data(start_time_ms, end_time_ms, limit)
                self._handle_rate_limit(response)

                if self._interpret_response(response):
                    return response

                if self._is_rate_limit_error(response):
                    continue  # rate limit handler already waited

                logger.warning("Attempt %d/%d failed. Status: %d",
                               attempt + 1, max_retries, response.status_code)

            except requests.exceptions.RequestException as e:
                logger.warning("Attempt %d/%d error: %s", attempt + 1, max_retries, e)

            if attempt < max_retries - 1:
                delay = base_delay ** (attempt + 1)
                logger.debug("Retrying in %.1fs...", delay)
                time.sleep(delay)

        logger.error("All %d attempts failed.", max_retries)
        return None

    # PUBLIC METHODS
    #******

    def fetch(self,
              limit: int | None = None,
              start_date_str: str | None = None,
              start_time_str: str | None = None,
              end_date_str: str | None = None,
              end_time_str: str | None = None,
              start_unix_ms: int | None = None,
              end_unix_ms: int | None = None,
              tz: ZoneInfo = ZoneInfo("UTC")) -> tuple[list[Any], bool]:
        """
        Fetch data for a single request.

        Can specify time range via date strings or unix timestamps.

        :return: Tuple of (data_list, success_bool)
        """
        if start_date_str:
            _, start_unix_ms = calendar_datetime_to_utc_and_unix(start_date_str, start_time_str, tz)
        if end_date_str:
            _, end_unix_ms = calendar_datetime_to_utc_and_unix(end_date_str, end_time_str, tz)

        response = self._fetch_with_retry(start_unix_ms, end_unix_ms, limit)

        if response is not None:
            return self._parse_response(response), True
        return [], False

    def batch_scrape(self,
                     limit: int | None = None,
                     start_date_str: str | None = None,
                     start_time_str: str | None = None,
                     end_date_str: str | None = None,
                     end_time_str: str | None = None,
                     tz: ZoneInfo = ZoneInfo("UTC")) -> list[Any]:
        """
        Batch scrape data across a time range with pagination.

        Handles rate limiting, progress reporting, and pagination automatically.

        :return: List of all data records
        """
        request_start_time = get_current_unix_ms()

        # Determine end time
        if end_date_str:
            _, end_scrape_unix_time = calendar_datetime_to_utc_and_unix(end_date_str, end_time_str, tz)
        else:
            end_scrape_unix_time = request_start_time

        # Determine start time
        if start_date_str:
            _, start_scrape_unix_time = calendar_datetime_to_utc_and_unix(start_date_str, start_time_str, tz)
        else:
            start_scrape_unix_time = self._get_earliest_timestamp()

        current_start_time = start_scrape_unix_time
        last_timestamp: int = 0
        all_data: list[Any] = []
        requests_count = 0

        # Log progress header
        logger.info("*" * 20)
        logger.info("Starting batch scrape: %s %s %s (%s)",
                    self.exchange_name, self.symbol, self.interval, self.data_type)
        logger.info("Date range: %s to %s",
                    unix_ms_to_filename_str(start_scrape_unix_time),
                    unix_ms_to_filename_str(end_scrape_unix_time))
        logger.info("*" * 20)

        while last_timestamp < end_scrape_unix_time:
            response = self._fetch_with_retry(current_start_time, end_scrape_unix_time, limit)
            requests_count += 1

            # Progress update every 10 requests
            if requests_count % 10 == 0 and last_timestamp > 0:
                progress_pct = ((last_timestamp - start_scrape_unix_time) /
                                (end_scrape_unix_time - start_scrape_unix_time)) * 100
                logger.info("Progress: %.1f%% | Records: %d | Requests: %d",
                            progress_pct, len(all_data), requests_count)

            if response is None:
                logger.error("Error occurred. Last successful timestamp: %s",
                             unix_ms_to_filename_str(last_timestamp))
                break

            # Parse and accumulate data
            batch_data = self._parse_response(response)

            if not batch_data:
                logger.info("No more data available.")
                break

            _, last_timestamp = self._get_timestamps_from_data(batch_data)
            current_start_time = self._get_next_start_time(batch_data)
            all_data.extend(batch_data)

        # Deduplicate (handles API returning duplicate records)
        all_data = self._deduplicate(all_data)

        # Log completion
        elapsed = (get_current_unix_ms() - request_start_time) / 1000
        logger.info("*" * 20)
        logger.info("Batch scrape complete!")
        logger.info("Total records: %d", len(all_data))
        logger.info("Total requests: %d", requests_count)
        logger.info("Time elapsed: %.1fs", elapsed)
        logger.info("*" * 20)

        return all_data
    
    def save(self,
             data: list[Any],
             create_numbered_version_if_exists: bool = False) -> bool:
        """
        Save scraped data to JSON file.
        
        :param data: List of data records
        :param create_numbered_version_if_exists: Create numbered version if file exists
        :return: True if saved successfully
        """
        if not data:
            logger.warning("No data to save.")
            return False
        
        timestamps = self._get_timestamps_from_data(data)
        filepath = create_timestamped_json_filepath(
            self.base_dir,
            self.exchange_name,
            self.symbol,
            self.data_type,
            self.interval,
            timestamps
        )
        
        metadata = {
            "exchange": self.exchange_name,
            "data_type": self.data_type,
            "symbol": self.symbol,
            "interval": self.interval,
            "first_timestamp": timestamps[0],
            "last_timestamp": timestamps[1],
            "calendar_range_utc": f"{unix_ms_to_filename_str(timestamps[0])}_to_{unix_ms_to_filename_str(timestamps[1])}",
            "record_count": len(data),
        }
        
        return save_json_data(data, filepath, metadata, create_numbered_version_if_exists)
    
    def scrape_and_save(self,
                        batch: bool = False,
                        limit: int | None = None,
                        start_date_str: str | None = None,
                        start_time_str: str | None = None,
                        end_date_str: str | None = None,
                        end_time_str: str | None = None,
                        start_unix_ms: int | None = None,
                        end_unix_ms: int | None = None,
                        tz: ZoneInfo = ZoneInfo("UTC"),
                        create_numbered_version_if_exists: bool = False) -> bool:
        """
        Convenience method to scrape and save in one call.
        
        :param batch: If True, use batch_scrape; otherwise single fetch
        :return: True if data was saved successfully
        """
        if batch:
            data = self.batch_scrape(
                limit, start_date_str, start_time_str, end_date_str, end_time_str, tz
            )
        else:
            data, success = self.fetch(
                limit, start_date_str, start_time_str, end_date_str, end_time_str,
                start_unix_ms, end_unix_ms, tz
            )
            if not success:
                return False
        
        return self.save(data, create_numbered_version_if_exists)
