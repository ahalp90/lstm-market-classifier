"""
Bybit exchange module.

Initialises scrapers for Bybit derivatives data:
* Open Interest
* Long/Short Ratio
"""

from .constants import (
    BybitSymbolType,
    BybitIntervalType,
    BYBIT_SYMBOLS,
    BYBIT_INTERVALS,
    BYBIT_CONFIG,
    INTERVAL_TO_BYBIT,
    INTERVAL_DURATION_MS,
    MAX_REQUESTS_PER_5_SECONDS,
    MAX_RECORDS_OPEN_INTEREST,
    MAX_RECORDS_LONG_SHORT_RATIO,
    BybitOpenInterestRecord,
    BybitLongShortRatioRecord,
)

from .keys import (
    OpenInterestKeys,
    OI_TAGS,
    get_oi_keys_by_tag,
    OI_FLOAT_KEYS,
    OI_INT_KEYS,
    OI_ALL_KEYS,
    LongShortRatioKeys,
    LSR_TAGS,
    get_lsr_keys_by_tag,
    LSR_FLOAT_KEYS,
    LSR_INT_KEYS,
    LSR_STR_KEYS,
    LSR_RATIO_KEYS,
    LSR_ALL_KEYS,
)

from .scraper import (
    BybitScraper,
    get_and_save_bybit_data,
)

__all__ = [
    # Constants
    "BybitSymbolType",
    "BybitIntervalType",
    "BYBIT_SYMBOLS",
    "BYBIT_INTERVALS",
    "BYBIT_CONFIG",
    "INTERVAL_TO_BYBIT",
    "INTERVAL_DURATION_MS",
    "MAX_REQUESTS_PER_5_SECONDS",
    "MAX_RECORDS_OPEN_INTEREST",
    "MAX_RECORDS_LONG_SHORT_RATIO",
    # TypedDicts
    "BybitOpenInterestRecord",
    "BybitLongShortRatioRecord",
    # Open Interest Keys
    "OpenInterestKeys",
    "OI_TAGS",
    "get_oi_keys_by_tag",
    "OI_FLOAT_KEYS",
    "OI_INT_KEYS",
    "OI_ALL_KEYS",
    # Long/Short Ratio Keys
    "LongShortRatioKeys",
    "LSR_TAGS",
    "get_lsr_keys_by_tag",
    "LSR_FLOAT_KEYS",
    "LSR_INT_KEYS",
    "LSR_STR_KEYS",
    "LSR_RATIO_KEYS",
    "LSR_ALL_KEYS",
    # Scraper
    "BybitScraper",
    "get_and_save_bybit_data",
]