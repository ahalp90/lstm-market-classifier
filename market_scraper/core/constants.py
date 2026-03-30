"""
Shared constants across all exchange scrapers.

Covers intervals, file paths, and abstract type definitions (where exchange-agnostic).
"""

import os
from typing import Literal, get_args
from enum import StrEnum, auto


# SHARED INTERVALS
# ******
# Intersection of Binance kline intervals and Bybit derivatives intervals
# Bybit OI/LSR supports: 5min, 15min, 30min, 1h, 4h, 1d
# Binance klines supports: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M

type SharedIntervalsType = Literal["5m", "15m", "30m", "1h", "4h", "1d"]
SHARED_INTERVALS: frozenset[SharedIntervalsType] = frozenset(get_args(SharedIntervalsType.__value__))


# DATA TYPES
# ******

class DataType(StrEnum):
    """Enum for different types of market data."""
    KLINE = auto()
    OPEN_INTEREST = auto()
    LONG_SHORT_RATIO = auto()


# FILE SYSTEM PATHS
# ******


# Base directory for all scraped data
DIR_MARKET_DATA: str = os.path.join(os.getcwd(), "market_data")

# Filename format: {exchange}_{symbol}_{interval}_{start_time}_to_{end_time}.json
JSON_FILENAME_FORMAT: str = "{exchange}_{symbol}_{data_type}_{interval}_{start_time_str}_to_{end_time_str}.json"


# FILE VERSIONING
# ******

MAX_FILE_VERSIONS: int = 50
