"""
Bybit market data key definitions.

Gives typed key enums and tag-based filtering for Bybit API response fields.
Separate enums per data type because their API formats are different.
"""

from enum import StrEnum, auto

from market_scraper.core import TaggedKeyRegistry


# OPEN INTEREST KEYS
# ******

class OpenInterestKeys(StrEnum):
    """Enum of open interest response field names."""
    OPEN_INTEREST = "openInterest"
    TIMESTAMP = "timestamp"


OI_TAGS: dict[OpenInterestKeys, frozenset[str]] = {
    OpenInterestKeys.OPEN_INTEREST: frozenset({"api", "float", "keep"}),
    OpenInterestKeys.TIMESTAMP: frozenset({"api", "int", "keep", "time"}),
}

# Registry instance for tag-based lookups
_oi_registry = TaggedKeyRegistry(OpenInterestKeys, OI_TAGS)


def get_oi_keys_by_tag(tag: str) -> list[OpenInterestKeys]:
    """Get OI keys matching a tag"""
    return _oi_registry.get_keys_by_tag(tag)


OI_FLOAT_KEYS: list[OpenInterestKeys] = _oi_registry.get_keys_by_tag("float")
OI_INT_KEYS: list[OpenInterestKeys] = _oi_registry.get_keys_by_tag("int")
OI_ALL_KEYS: list[OpenInterestKeys] = _oi_registry.all_keys


# LONG/SHORT RATIO KEYS
# ******

class LongShortRatioKeys(StrEnum):
    """Enum of long/short ratio response field names."""
    SYMBOL = "symbol"
    BUY_RATIO = "buyRatio"
    SELL_RATIO = "sellRatio"
    TIMESTAMP = "timestamp"


LSR_TAGS: dict[LongShortRatioKeys, frozenset[str]] = {
    LongShortRatioKeys.SYMBOL: frozenset({"api", "str", "keep"}),
    LongShortRatioKeys.BUY_RATIO: frozenset({"api", "float", "keep", "ratio"}),
    LongShortRatioKeys.SELL_RATIO: frozenset({"api", "float", "keep", "ratio"}),
    LongShortRatioKeys.TIMESTAMP: frozenset({"api", "int", "keep", "time"}),
}

# Registry instance for tag-based lookups
_lsr_registry = TaggedKeyRegistry(LongShortRatioKeys, LSR_TAGS)


def get_lsr_keys_by_tag(tag: str) -> list[LongShortRatioKeys]:
    """Get LSR keys matching a tag"""
    return _lsr_registry.get_keys_by_tag(tag)


LSR_FLOAT_KEYS: list[LongShortRatioKeys] = _lsr_registry.get_keys_by_tag("float")
LSR_INT_KEYS: list[LongShortRatioKeys] = _lsr_registry.get_keys_by_tag("int")
LSR_STR_KEYS: list[LongShortRatioKeys] = _lsr_registry.get_keys_by_tag("str")
LSR_RATIO_KEYS: list[LongShortRatioKeys] = _lsr_registry.get_keys_by_tag("ratio")
LSR_ALL_KEYS: list[LongShortRatioKeys] = _lsr_registry.all_keys