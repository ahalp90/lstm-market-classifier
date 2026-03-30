"""
Binance-specific constants and type definitions.

Defines Binance trading pairs, intervals, and API configuration.
"""

from typing import Literal, get_args

from market_scraper.core import ExchangeConfig

# BINANCE SYMBOLS
#******

type BinanceSymbolType = Literal["BTCFDUSD", "ETHFDUSD", "SOLFDUSD", "ETHBTC", "BTCUSDT", "ETHUSDT"]
BINANCE_SYMBOLS: frozenset[BinanceSymbolType] = frozenset(get_args(BinanceSymbolType.__value__))


# BINANCE INTERVALS
#******
# Note: 1s interval excluded

type BinanceIntervalType = Literal[
    "1m", "3m", "5m", "15m", "30m", 
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1M"
]
BINANCE_INTERVALS: frozenset[BinanceIntervalType] = frozenset(get_args(BinanceIntervalType.__value__))


# API CONFIG
#******

BINANCE_CONFIG = ExchangeConfig(
    api_base_url="https://api.binance.com",
    max_records_per_request=1500,
    max_requests_per_window=6000,
    window_seconds=60,
    request_timeout=15,
)

# Endpoints
BINANCE_KLINE_ENDPOINT = "/api/v3/klines"

# Convenience aliases
BINANCE_API_BASE_URL = BINANCE_CONFIG.api_base_url
MAX_RECORDS_PER_REQUEST = BINANCE_CONFIG.max_records_per_request
MAX_REQUESTS_PER_MINUTE = BINANCE_CONFIG.max_requests_per_window
REQUEST_TIMEOUT = BINANCE_CONFIG.request_timeout


# KLINE DATA STRUCTURE
#******
# Binance returns klines as arrays with the following indices:

type BinanceKlineRaw = list[int | str]


class KlineIndex:
    """
    Named indices for Binance kline array positions.

    Use these instead of magic numbers when accessing kline data:
        kline[KlineIndex.OPEN_TIME]  # instead of kline[0]
        kline[KlineIndex.CLOSE]      # instead of kline[4]
    """
    OPEN_TIME = 0
    OPEN = 1
    HIGH = 2
    LOW = 3
    CLOSE = 4
    VOLUME = 5
    CLOSE_TIME = 6
    QUOTE_ASSET_VOLUME = 7
    NUMBER_OF_TRADES = 8
    TAKER_BUY_BASE_ASSET_VOLUME = 9
    TAKER_BUY_QUOTE_ASSET_VOLUME = 10
    IGNORE = 11
