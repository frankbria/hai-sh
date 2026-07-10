"""
Rate limiting for LLM API calls.

This module implements token bucket rate limiting to prevent:
- API abuse and cost overruns
- Excessive retry loops
- Provider rate limit exhaustion
"""

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Implements a sliding window rate limiter that tracks API calls
    within a time window and enforces maximum call limits.

    Example:
        >>> limiter = RateLimiter(max_calls=60, window_seconds=60)
        >>> allowed, msg = limiter.check_limit()
        >>> if not allowed:
        ...     print(f"Rate limited: {msg}")
    """

    def __init__(self, max_calls: int = 60, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed in the time window
            window_seconds: Time window in seconds
        """
        self.max_calls = max_calls
        self.window = timedelta(seconds=window_seconds)
        self.calls = []

    def check_limit(self) -> tuple[bool, Optional[str]]:
        """
        Check if we're within rate limit and record this call.

        Returns:
            tuple: (is_allowed, error_message)
                - is_allowed: True if within rate limit
                - error_message: None if allowed, otherwise describes the limit
        """
        now = datetime.now()

        # Remove old calls outside the time window
        self.calls = [t for t in self.calls if now - t < self.window]

        # Check if we've exceeded the limit
        if len(self.calls) >= self.max_calls:
            oldest_call = min(self.calls)
            wait_seconds = (oldest_call + self.window - now).total_seconds()
            return False, (
                f"Rate limit exceeded: {self.max_calls} calls per {self.window.total_seconds():.0f}s. "
                f"Wait {wait_seconds:.0f} seconds."
            )

        # Record this call
        self.calls.append(now)
        return True, None

    def get_remaining_calls(self) -> int:
        """
        Get number of remaining calls in current window.

        Returns:
            int: Number of calls remaining before hitting rate limit
        """
        now = datetime.now()
        self.calls = [t for t in self.calls if now - t < self.window]
        return max(0, self.max_calls - len(self.calls))

    def reset(self):
        """Reset the rate limiter by clearing all recorded calls."""
        self.calls = []


# Global rate limiters per provider (lazily initialized)
_rate_limiters: dict[str, RateLimiter] = {}


def get_rate_limiter(provider_name: str, max_calls: int = 60, window_seconds: int = 60) -> RateLimiter:
    """
    Get or create a rate limiter for a specific provider.

    Args:
        provider_name: Name of the LLM provider (e.g., "OpenAIProvider")
        max_calls: Maximum calls per window (default: 60)
        window_seconds: Time window in seconds (default: 60)

    Returns:
        RateLimiter: Rate limiter instance for this provider
    """
    if provider_name not in _rate_limiters:
        _rate_limiters[provider_name] = RateLimiter(max_calls, window_seconds)

    return _rate_limiters[provider_name]


def check_rate_limit(provider_name: str) -> tuple[bool, Optional[str]]:
    """
    Check rate limit for a provider.

    Args:
        provider_name: Name of the LLM provider

    Returns:
        tuple: (is_allowed, error_message)
    """
    limiter = get_rate_limiter(provider_name)
    return limiter.check_limit()


def reset_rate_limit(provider_name: str):
    """
    Reset rate limit for a provider.

    Args:
        provider_name: Name of the LLM provider
    """
    if provider_name in _rate_limiters:
        _rate_limiters[provider_name].reset()


def get_remaining_calls(provider_name: str) -> int:
    """
    Get remaining calls for a provider.

    Args:
        provider_name: Name of the LLM provider

    Returns:
        int: Number of remaining calls before rate limit
    """
    limiter = get_rate_limiter(provider_name)
    return limiter.get_remaining_calls()
