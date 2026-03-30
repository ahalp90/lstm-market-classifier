"""
Reusable tagged key registry system.

Generic way to define keys with associated tags and query keys by tag, rather than exchange-specific boilerplate.
"""

from enum import StrEnum
from typing import TypeVar, Generic

K = TypeVar('K', bound=StrEnum)


class TaggedKeyRegistry(Generic[K]):
    """
    Registry for keys with associated tags. Use to filter by tag.

    eg:
        registry = TaggedKeyRegistry(MyKeys, TAGS)
        float_keys = registry.get_keys_by_tag("float")
    """

    def __init__(self, key_enum: type[K], tags: dict[K, frozenset[str]]):
        self._key_enum = key_enum
        self._tags = tags

        # Pre-compute all keys and tags
        self._all_keys: list[K] = list(key_enum)

        self._available_tags: frozenset[str] = frozenset(
            tag for tag_set in tags.values() for tag in tag_set
        )

    def get_keys_by_tag(self, tag: str) -> list[K]:
        """
        Get list of keys that have a specific tag."""
        return [key for key, tags in self._tags.items() if tag in tags]

    @property
    def all_keys(self) -> list[K]:
        """Get list of all keys."""
        return self._all_keys.copy()

    @property
    def all_key_values(self) -> list[str]:
        """Get list of all key values (string names)."""
        return [key.value for key in self._all_keys]

    @property
    def available_tags(self) -> frozenset[str]:
        """Get set of all available tags across all keys"""
        return self._available_tags

    def get_tags_for_key(self, key: K) -> frozenset[str]:
        """Get all tags associated with a specific key."""
        return self._tags.get(key, frozenset())

    def has_tag(self, key: K, tag: str) -> bool:
        """Check if a key has a specific tag. True if has the tag"""
        return tag in self._tags.get(key, frozenset())
