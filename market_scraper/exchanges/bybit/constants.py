"""
Bybit constants and type definitions.

Defines symbols, intervals, and API config.
"""

from typing import Literal, get_args, TypedDict

from market_scraper.core import ExchangeConfig

# BYBIT SYMBOLS (Linear Perpetual USDT contracts)
# ******
type BybitSymbolType = Literal["BTCUSDT", "ETHUSDT", "SOLUSDT"]
BYBIT_SYMBOLS: frozenset[BybitSymbolType] = frozenset(get_args(BybitSymbolType.__value__))


# BYBIT INTERVALS
# ******
# Bybit open interest and long/short ratio support these intervals:
# 5min, 15min, 30min, 1h, 4h, 1d

type BybitIntervalType = Literal["5min", "15min", "30min", "1h", "4h", "1d"]
BYBIT_INTERVALS: frozenset[BybitIntervalType] = frozenset(get_args(BybitIntervalType.__value__))

# Mapping from shared interval format to Bybit format
INTERVAL_TO_BYBIT: dict[str, str] = {
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

BYBIT_TO_INTERVAL: dict[str, str] = {v: k for k, v in INTERVAL_TO_BYBIT.items()}

# Intervals in milliseconds
INTERVAL_DURATION_MS: dict[str, int] = {
    "5min": 300_000,
    "15min": 900_000,
    "30min": 1_800_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


# API CONFIGURATION
# ******

BYBIT_CONFIG = ExchangeConfig(
    api_base_url="https://api.bybit.com",
    max_records_per_request=200,  # OI limit; LSR uses 500
    max_requests_per_window=600,
    window_seconds=5,
    request_timeout=15,
)

# Market data endpoints
BYBIT_OPEN_INTEREST_ENDPOINT = "/v5/market/open-interest"
BYBIT_LONG_SHORT_RATIO_ENDPOINT = "/v5/market/account-ratio"
BYBIT_INSTRUMENTS_INFO_ENDPOINT = "/v5/market/instruments-info"

# Category
BYBIT_CATEGORY = "linear"

# Pagination limits (per data type)
MAX_RECORDS_OPEN_INTEREST: int = 200
MAX_RECORDS_LONG_SHORT_RATIO: int = 500

# Convenience aliases
BYBIT_API_BASE_URL = BYBIT_CONFIG.api_base_url
MAX_REQUESTS_PER_5_SECONDS = BYBIT_CONFIG.max_requests_per_window
RATE_LIMIT_WINDOW_SECONDS = BYBIT_CONFIG.window_seconds
REQUEST_TIMEOUT = BYBIT_CONFIG.request_timeout

# Hardcoded fallback earliest timestamp (July 20, 2020) if needed
BYBIT_V5_DATA_START_MS: int = 1595203200000


# DATA TYPE DEFINITIONS
# ******

class BybitOpenInterestRecord(TypedDict):
    """Single open interest data point from Bybit API."""
    openInterest: str  # The OI value (sum of both sides)
    timestamp: str     # Timestamp in milliseconds


class BybitLongShortRatioRecord(TypedDict):
    """Single long/short ratio data point from Bybit API."""
    symbol: str       # Symbol name
    buyRatio: str     # Ratio of long position holders
    sellRatio: str    # Ratio of short position holders
    timestamp: str    # Timestamp in milliseconds