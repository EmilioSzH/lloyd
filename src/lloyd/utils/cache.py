"""Semantic LLM Response Cache.

Provides caching for LLM responses with TTL-based expiration
and dual-layer storage (in-memory + disk persistence).
"""

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class CacheEntry:
    """A cached LLM response entry.

    Attributes:
        prompt_hash: Hash of the normalized prompt.
        response: The cached response.
        model: Model name used.
        timestamp: Unix timestamp when cached.
        ttl: Time-to-live in seconds.
        hit_count: Number of cache hits.
    """

    prompt_hash: str
    response: str
    model: str
    timestamp: float
    ttl: float
    hit_count: int = 0

    def is_expired(self) -> bool:
        """Check if this entry has expired.

        Returns:
            True if expired.
        """
        return time.time() > self.timestamp + self.ttl

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dict representation.
        """
        return {
            "prompt_hash": self.prompt_hash,
            "response": self.response,
            "model": self.model,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "hit_count": self.hit_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheEntry":
        """Create from dictionary.

        Args:
            data: Dict representation.

        Returns:
            CacheEntry instance.
        """
        return cls(
            prompt_hash=data["prompt_hash"],
            response=data["response"],
            model=data["model"],
            timestamp=data["timestamp"],
            ttl=data["ttl"],
            hit_count=data.get("hit_count", 0),
        )


class SemanticCache:
    """Semantic cache for LLM responses with dual-layer storage.

    Features:
    - In-memory cache for fast access
    - Disk persistence in .lloyd/cache/
    - TTL-based expiration (default 24 hours)
    - Prompt normalization for better hit rates
    """

    DEFAULT_TTL = 24 * 60 * 60  # 24 hours

    def __init__(
        self,
        lloyd_dir: Path | None = None,
        default_ttl: float | None = None,
        max_memory_entries: int = 1000,
    ) -> None:
        """Initialize the semantic cache.

        Args:
            lloyd_dir: Lloyd data directory. Defaults to .lloyd
            default_ttl: Default TTL in seconds. Defaults to 24 hours.
            max_memory_entries: Maximum entries to keep in memory.
        """
        self.lloyd_dir = lloyd_dir or Path(".lloyd")
        self.cache_dir = self.lloyd_dir / "cache"
        self.default_ttl = default_ttl or self.DEFAULT_TTL
        self.max_memory_entries = max_memory_entries

        # In-memory cache
        self._memory_cache: dict[str, CacheEntry] = {}

        # Load from disk on init
        self._load_from_disk()

    def _ensure_cache_dir(self) -> None:
        """Ensure the cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_prompt(self, prompt: str) -> str:
        """Normalize a prompt for consistent hashing.

        Removes extra whitespace, normalizes case for common words,
        and strips leading/trailing whitespace.

        Args:
            prompt: Raw prompt string.

        Returns:
            Normalized prompt string.
        """
        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", prompt.strip())

        # Lowercase common structural words
        structural_words = ["the", "a", "an", "is", "are", "was", "were", "be", "been"]
        for word in structural_words:
            # Only at word boundaries
            normalized = re.sub(rf"\b{word}\b", word.lower(), normalized)

        return normalized

    def _compute_hash(self, prompt: str, model: str) -> str:
        """Compute cache key hash.

        Args:
            prompt: Normalized prompt.
            model: Model name.

        Returns:
            SHA256 hash as hex string.
        """
        key = f"{model}:{prompt}"
        return hashlib.sha256(key.encode()).hexdigest()

    def _get_cache_file_path(self, prompt_hash: str) -> Path:
        """Get the disk cache file path for a hash.

        Uses first 2 chars for subdirectory to avoid too many files.

        Args:
            prompt_hash: The hash.

        Returns:
            Path to cache file.
        """
        subdir = prompt_hash[:2]
        return self.cache_dir / subdir / f"{prompt_hash}.json"

    def get(self, prompt: str, model: str) -> str | None:
        """Get a cached response for a prompt.

        Args:
            prompt: The prompt to look up.
            model: Model name.

        Returns:
            Cached response or None if not found/expired.
        """
        normalized = self._normalize_prompt(prompt)
        key = self._compute_hash(normalized, model)

        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if not entry.is_expired():
                entry.hit_count += 1
                return entry.response
            else:
                # Remove expired entry
                del self._memory_cache[key]
                self._remove_from_disk(key)
                return None

        # Check disk cache
        entry = self._load_from_disk_entry(key)
        if entry and not entry.is_expired():
            # Add to memory cache
            self._memory_cache[key] = entry
            entry.hit_count += 1
            return entry.response
        elif entry:
            # Remove expired disk entry
            self._remove_from_disk(key)

        return None

    def set(
        self,
        prompt: str,
        response: str,
        model: str,
        ttl: float | None = None,
    ) -> None:
        """Cache a response.

        Args:
            prompt: The prompt.
            response: The response to cache.
            model: Model name.
            ttl: Optional TTL override in seconds.
        """
        normalized = self._normalize_prompt(prompt)
        key = self._compute_hash(normalized, model)

        entry = CacheEntry(
            prompt_hash=key,
            response=response,
            model=model,
            timestamp=time.time(),
            ttl=ttl or self.default_ttl,
        )

        # Add to memory cache
        self._memory_cache[key] = entry

        # Persist to disk
        self._save_to_disk(entry)

        # Evict old entries if over limit
        self._evict_if_needed()

    def _load_from_disk(self) -> None:
        """Load all cache entries from disk."""
        if not self.cache_dir.exists():
            return

        for subdir in self.cache_dir.iterdir():
            if subdir.is_dir():
                for cache_file in subdir.glob("*.json"):
                    try:
                        with open(cache_file) as f:
                            data = json.load(f)
                        entry = CacheEntry.from_dict(data)
                        if not entry.is_expired():
                            self._memory_cache[entry.prompt_hash] = entry
                    except (json.JSONDecodeError, KeyError):
                        # Invalid cache file, skip
                        pass

    def _load_from_disk_entry(self, key: str) -> CacheEntry | None:
        """Load a specific entry from disk.

        Args:
            key: The cache key hash.

        Returns:
            CacheEntry or None if not found.
        """
        path = self._get_cache_file_path(key)
        if not path.exists():
            return None

        try:
            with open(path) as f:
                data = json.load(f)
            return CacheEntry.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def _save_to_disk(self, entry: CacheEntry) -> None:
        """Save an entry to disk.

        Args:
            entry: The entry to save.
        """
        self._ensure_cache_dir()
        path = self._get_cache_file_path(entry.prompt_hash)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(entry.to_dict(), f, indent=2)

    def _remove_from_disk(self, key: str) -> None:
        """Remove an entry from disk.

        Args:
            key: The cache key hash.
        """
        path = self._get_cache_file_path(key)
        if path.exists():
            path.unlink()

    def _evict_if_needed(self) -> None:
        """Evict old entries if over memory limit."""
        if len(self._memory_cache) <= self.max_memory_entries:
            return

        # Sort by timestamp (oldest first)
        sorted_entries = sorted(
            self._memory_cache.items(),
            key=lambda x: x[1].timestamp,
        )

        # Remove oldest entries until under limit
        to_remove = len(self._memory_cache) - self.max_memory_entries
        for key, _ in sorted_entries[:to_remove]:
            del self._memory_cache[key]

    def clear(self) -> None:
        """Clear all cached entries."""
        self._memory_cache.clear()

        if self.cache_dir.exists():
            import shutil

            shutil.rmtree(self.cache_dir)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache stats.
        """
        total_hits = sum(e.hit_count for e in self._memory_cache.values())
        expired_count = sum(
            1 for e in self._memory_cache.values() if e.is_expired()
        )

        return {
            "memory_entries": len(self._memory_cache),
            "total_hits": total_hits,
            "expired_entries": expired_count,
            "cache_dir": str(self.cache_dir),
        }


def cached_llm_call(
    prompt: str,
    llm_func: Callable[[str], str],
    model: str = "default",
    cache: SemanticCache | None = None,
    use_cache: bool = True,
    ttl: float | None = None,
) -> str:
    """Wrapper for LLM calls with caching.

    Args:
        prompt: The prompt to send.
        llm_func: Function that takes prompt and returns response.
        model: Model name for cache keying.
        cache: SemanticCache instance. Creates temporary one if None.
        use_cache: Whether to use caching.
        ttl: Optional TTL override.

    Returns:
        LLM response (from cache or fresh call).
    """
    if not use_cache:
        return llm_func(prompt)

    # Use provided cache or create temporary one
    _cache = cache or SemanticCache()

    # Try cache first
    cached = _cache.get(prompt, model)
    if cached is not None:
        return cached

    # Make actual call
    response = llm_func(prompt)

    # Cache the response
    _cache.set(prompt, response, model, ttl)

    return response
