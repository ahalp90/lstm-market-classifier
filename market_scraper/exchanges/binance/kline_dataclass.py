"""
Binance kline data structure definitions.

Has typed key enums and tag-based filtering for kline data fields.
Useful for data processing and analysis pipeline.
"""

from enum import StrEnum, auto
from typing import TypeAlias

from market_scraper.core import TaggedKeyRegistry


class KlineKeys(StrEnum):
    """Enum of all kline field names."""
    OPEN_TIME = auto()
    OPEN = auto()
    HIGH = auto()
    LOW = auto()
    CLOSE = auto()
    VOLUME = auto()
    CLOSE_TIME = auto()
    QUOTE_ASSET_VOLUME = auto()
    NUMBER_OF_TRADES = auto()
    TAKER_BUY_BASE_ASSET_VOLUME = auto()
    TAKER_BUY_QUOTE_ASSET_VOLUME = auto()
    IGNORE = auto()

KK: TypeAlias = KlineKeys


# Tag definitions for each kline field
# Tags help categorise fields for different feature eng
KLINE_TAGS: dict[KlineKeys, frozenset[str]] = {
    KlineKeys.OPEN_TIME: frozenset({"api", "int", "keep", "time"}),
    KlineKeys.OPEN: frozenset({"api", "float", "keep", "price", "string_wrapped_values"}),
    KlineKeys.HIGH: frozenset({"api", "float", "keep", "price", "string_wrapped_values"}),
    KlineKeys.LOW: frozenset({"api", "float", "keep", "price", "string_wrapped_values"}),
    KlineKeys.CLOSE: frozenset({"api", "float", "keep", "price", "string_wrapped_values"}),
    KlineKeys.VOLUME: frozenset({"api", "float", "keep", "volume", "string_wrapped_values"}),
    KlineKeys.CLOSE_TIME: frozenset({"api", "int", "keep", "time"}),
    KlineKeys.QUOTE_ASSET_VOLUME: frozenset({"api", "float", "volume", "string_wrapped_values"}),
    KlineKeys.NUMBER_OF_TRADES: frozenset({"api", "int", "keep", "volume"}),
    KlineKeys.TAKER_BUY_BASE_ASSET_VOLUME: frozenset({"api", "float", "volume", "taker", "string_wrapped_values"}),
    KlineKeys.TAKER_BUY_QUOTE_ASSET_VOLUME: frozenset({"api", "float", "volume", "taker", "string_wrapped_values"}),
    KlineKeys.IGNORE: frozenset({"api", "ignore", "string_wrapped_values"}),
}

# Registry instance for tag-based lookups
_kline_registry = TaggedKeyRegistry(KlineKeys, KLINE_TAGS)


def get_keys_by_tag(tag: str) -> list[KlineKeys]:
    """Get list of kline keys that have a specific tag."""
    return _kline_registry.get_keys_by_tag(tag)


# Pre-computed key lists by tag for convenience
FLOAT_KEYS: list[KlineKeys] = _kline_registry.get_keys_by_tag("float")
INT_KEYS: list[KlineKeys] = _kline_registry.get_keys_by_tag("int")
TIME_KEYS: list[KlineKeys] = _kline_registry.get_keys_by_tag("time")
VOLUME_KEYS: list[KlineKeys] = _kline_registry.get_keys_by_tag("volume")
TAKER_KEYS: list[KlineKeys] = _kline_registry.get_keys_by_tag("taker")
PRICE_KEYS: list[KlineKeys] = _kline_registry.get_keys_by_tag("price")
IGNORE_KEYS: list[KlineKeys] = _kline_registry.get_keys_by_tag("ignore")
STRING_WRAPPED_VALUES: list[KlineKeys] = _kline_registry.get_keys_by_tag("string_wrapped_values")
ALL_KEYS: list[KlineKeys] = _kline_registry.all_keys
API_KEYS: list[KlineKeys] = _kline_registry.get_keys_by_tag("api")
