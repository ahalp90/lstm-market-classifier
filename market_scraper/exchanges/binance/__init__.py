"""
Binance exchange module.

Scrapers and utilities for Binance market data.
"""

from .constants import (
    BinanceSymbolType,
    BinanceIntervalType,
    BINANCE_SYMBOLS,
    BINANCE_INTERVALS,
    BINANCE_CONFIG,
    BinanceKlineRaw,
    KlineIndex,
    MAX_RECORDS_PER_REQUEST,
    MAX_REQUESTS_PER_MINUTE,
)

from .kline_dataclass import (
    KlineKeys,
    KLINE_TAGS,
    get_keys_by_tag,
    FLOAT_KEYS,
    INT_KEYS,
    TIME_KEYS,
    VOLUME_KEYS,
    TAKER_KEYS,
    PRICE_KEYS,
    ALL_KEYS,
    API_KEYS,
)

from .kline_scraper import (
    BinanceKlineScraper,
    # Backward-compatible convenience functions
    get_kline_data,
    batch_scrape_klines,
    get_and_save_klines,
)

__all__ = [
    # Constants
    "BinanceSymbolType",
    "BinanceIntervalType",
    "BINANCE_SYMBOLS",
    "BINANCE_INTERVALS",
    "BINANCE_CONFIG",
    "BinanceKlineRaw",
    "KlineIndex",
    "MAX_RECORDS_PER_REQUEST",
    "MAX_REQUESTS_PER_MINUTE",
    # Dataclass
    "KlineKeys",
    "KLINE_TAGS",
    "get_keys_by_tag",
    "FLOAT_KEYS",
    "INT_KEYS",
    "TIME_KEYS",
    "VOLUME_KEYS",
    "TAKER_KEYS",
    "PRICE_KEYS",
    "ALL_KEYS",
    "API_KEYS",
    # Scraper
    "BinanceKlineScraper",
    "get_kline_data",
    "batch_scrape_klines",
    "get_and_save_klines",
]
