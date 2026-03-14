"""Query cache for search results."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class QueryCache:
    """LRU cache for search query results.

    This class provides:
    - Time-based cache expiration (TTL)
    - Size-based LRU eviction
    - Efficient cache key generation

    Attributes:
        max_size: Maximum number of cached entries.
        ttl_seconds: Time-to-live in seconds.
    """

    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: int = 3600
    ):
        if max_size < 1:
            raise ValueError("max_size must be at least 1")
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be at least 1")

        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[list[dict[str, Any]], float]] = {}

    def _cache_key(
        self,
        query: str,
        search_type: str,
        time_range: tuple[float, float] | None
    ) -> str:
        """Generate a cache key from query parameters.

        Args:
            query: Search query string.
            search_type: Search type identifier.
            time_range: Optional time range tuple.

        Returns:
            MD5 hash string as cache key.
        """
        time_range_str = ""
        if time_range:
            time_range_str = f"{time_range[0]:.0f}-{time_range[1]:.0f}"

        key_str = f"{query}:{search_type}:{time_range_str}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(
        self,
        query: str,
        search_type: str,
        time_range: tuple[float, float] | None
    ) -> list[dict[str, Any]] | None:
        """Get cached results if available and not expired.

        Args:
            query: Search query string.
            search_type: Search type identifier.
            time_range: Optional time range tuple.

        Returns:
            Cached results or None if not found/expired.
        """
        key = self._cache_key(query, search_type, time_range)

        if key in self._cache:
            results, timestamp = self._cache[key]
            current_time = time.time()

            if current_time - timestamp < self.ttl_seconds:
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return results
            else:
                del self._cache[key]
                logger.debug(f"Cache expired for query: {query[:50]}...")

        return None

    def set(
        self,
        query: str,
        search_type: str,
        time_range: tuple[float, float] | None,
        results: list[dict[str, Any]]
    ) -> None:
        """Cache search results.

        Args:
            query: Search query string.
            search_type: Search type identifier.
            time_range: Optional time range tuple.
            results: Search results to cache.
        """
        if len(self._cache) >= self.max_size:
            self._evict_oldest()

        key = self._cache_key(query, search_type, time_range)
        self._cache[key] = (results, time.time())

        logger.debug(f"Cached results for query: {query[:50]}...")

    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry (LRU)."""
        if not self._cache:
            return

        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k][1]
        )
        del self._cache[oldest_key]
        logger.debug("Evicted oldest cache entry")

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        logger.debug("Cache cleared")

    def invalidate(
        self,
        query: str,
        search_type: str,
        time_range: tuple[float, float] | None
    ) -> bool:
        """Invalidate a specific cache entry.

        Args:
            query: Search query string.
            search_type: Search type identifier.
            time_range: Optional time range tuple.

        Returns:
            True if entry was found and removed.
        """
        key = self._cache_key(query, search_type, time_range)

        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Invalidated cache for query: {query[:50]}...")
            return True

        return False

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache size and configuration.
        """
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds
        }

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed.
        """
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp >= self.ttl_seconds
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    @property
    def size(self) -> int:
        """Current number of cached entries."""
        return len(self._cache)

    @property
    def is_empty(self) -> bool:
        """Check if cache is empty."""
        return len(self._cache) == 0
