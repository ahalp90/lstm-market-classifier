"""
Core market data scraper

Gives shared methods, classes and constants for:
*Base scraper class with batch scraping
*Time conversion and file read/write
*General constants and types
"""

from .constants import (
    SharedIntervalsType,
    SHARED_INTERVALS,
    DataType,
    DIR_MARKET_DATA,
    JSON_FILENAME_FORMAT,
    MAX_FILE_VERSIONS,
)

from .utilities import (
    calendar_datetime_to_utc_and_unix,
    unix_ms_to_utc_datetime,
    unix_ms_to_filename_str,
    get_current_unix_ms,
    create_timestamped_json_filepath,
    save_json_data,
    parse_market_data_filename,
    build_market_data_filepath,
    load_json_file,
    find_duplicates_and_time_gaps,
)

from .base_scraper import BaseScraper
from .exchange_config import ExchangeConfig
from .tagged_keys import TaggedKeyRegistry

__all__ = [
    # Constants
    "SharedIntervalsType",
    "SHARED_INTERVALS",
    "DataType",
    "DIR_MARKET_DATA",
    "JSON_FILENAME_FORMAT",
    "MAX_FILE_VERSIONS",
    # Utilities
    "calendar_datetime_to_utc_and_unix",
    "unix_ms_to_utc_datetime",
    "unix_ms_to_filename_str",
    "get_current_unix_ms",
    "create_timestamped_json_filepath",
    "save_json_data",
    "find_duplicates_and_time_gaps",
    # File load utilities
    "parse_market_data_filename",
    "build_market_data_filepath",
    "load_json_file",
    # Base class
    "BaseScraper",
    # Config
    "ExchangeConfig",
    # Key registry
    "TaggedKeyRegistry",
]
