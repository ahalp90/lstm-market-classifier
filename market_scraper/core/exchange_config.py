"""
Exchange config dataclass.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExchangeConfig:
    """Immutable config for an exchange API."""
    api_base_url: str
    max_records_per_request: int
    max_requests_per_window: int
    window_seconds: int
    request_timeout: int = 15
