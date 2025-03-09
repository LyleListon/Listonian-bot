"""Rate limiting utilities."""

import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for API requests."""

    def __init__(
        self, max_requests: int = 100, time_window: int = 60, testing: bool = False
    ):
        """
        Initialize rate limiter.

        Args:
            max_requests (int, optional): Maximum requests per time window
            time_window (int, optional): Time window in seconds
            testing (bool, optional): Whether to bypass rate limiting for testing
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.testing = testing
        self._request_times = []
        logger.info("Rate limiter initialized")

    async def can_execute(self) -> bool:
        """
        Check if request can be executed.

        Returns:
            bool: True if request is allowed
        """
        if self.testing:
            return True

        current_time = time.time()

        # Remove old requests
        self._request_times = [
            t for t in self._request_times if current_time - t < self.time_window
        ]

        # Check if under limit
        if len(self._request_times) < self.max_requests:
            self._request_times.append(current_time)
            return True

        return False

    def get_remaining_requests(self) -> int:
        """
        Get remaining requests in current window.

        Returns:
            int: Number of remaining requests
        """
        if self.testing:
            return self.max_requests

        current_time = time.time()

        # Remove old requests
        self._request_times = [
            t for t in self._request_times if current_time - t < self.time_window
        ]

        return max(0, self.max_requests - len(self._request_times))

    def get_reset_time(self) -> Optional[float]:
        """
        Get time until rate limit resets.

        Returns:
            Optional[float]: Seconds until reset or None if no active limit
        """
        if self.testing or not self._request_times:
            return None

        current_time = time.time()
        oldest_request = min(self._request_times)

        return max(0, self.time_window - (current_time - oldest_request))

    def reset(self):
        """Reset rate limiter."""
        self._request_times = []
        logger.info("Rate limiter reset")


def create_rate_limiter(
    max_requests: int = 100, time_window: int = 60, testing: bool = False
) -> RateLimiter:
    """
    Create RateLimiter instance.

    Args:
        max_requests (int, optional): Maximum requests per time window
        time_window (int, optional): Time window in seconds
        testing (bool, optional): Whether to bypass rate limiting for testing

    Returns:
        RateLimiter: Rate limiter instance
    """
    return RateLimiter(
        max_requests=max_requests, time_window=time_window, testing=testing
    )
