"""
Simple in-memory cache for HTTP responses
Reduces redundant requests to e-class server
"""

import time
from typing import Optional, Dict, Any


class ResponseCache:
    """Simple time-based cache for HTTP responses"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str, max_age_seconds: int = 300) -> Optional[str]:
        """
        Get cached response if not expired

        Args:
            key: Cache key (usually URL)
            max_age_seconds: Maximum age in seconds (default: 5 minutes)

        Returns:
            Cached response or None if expired/missing
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        age = time.time() - entry['timestamp']

        if age > max_age_seconds:
            # Expired, remove from cache
            del self._cache[key]
            return None

        return entry['data']

    def set(self, key: str, data: str) -> None:
        """
        Store response in cache

        Args:
            key: Cache key (usually URL)
            data: Response data to cache
        """
        self._cache[key] = {
            'data': data,
            'timestamp': time.time()
        }

    def clear(self) -> None:
        """Clear all cached entries"""
        self._cache.clear()

    def remove(self, key: str) -> None:
        """Remove specific cache entry"""
        if key in self._cache:
            del self._cache[key]


# Global cache instance
_global_cache = ResponseCache()


def get_cached(key: str, max_age_seconds: int = 300) -> Optional[str]:
    """Get from global cache"""
    return _global_cache.get(key, max_age_seconds)


def set_cached(key: str, data: str) -> None:
    """Set in global cache"""
    _global_cache.set(key, data)


def clear_cache() -> None:
    """Clear global cache"""
    _global_cache.clear()
