"""Tests for SemanticCache."""

import tempfile
import time
from pathlib import Path

import pytest

from lloyd.utils.cache import CacheEntry, SemanticCache, cached_llm_call


@pytest.fixture
def temp_lloyd_dir():
    """Create a temporary lloyd directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache(temp_lloyd_dir):
    """Create a SemanticCache with temporary storage."""
    return SemanticCache(lloyd_dir=temp_lloyd_dir, default_ttl=3600)


class TestSemanticCacheBasics:
    """Basic cache operations tests."""

    def test_set_and_get(self, cache):
        """Can set and get a value."""
        cache.set("Hello world", "Response", "gpt-4")
        result = cache.get("Hello world", "gpt-4")

        assert result == "Response"

    def test_get_nonexistent_returns_none(self, cache):
        """Getting nonexistent key returns None."""
        result = cache.get("Never cached", "gpt-4")
        assert result is None

    def test_different_models_different_cache(self, cache):
        """Different models have separate cache entries."""
        cache.set("Same prompt", "Response A", "gpt-4")
        cache.set("Same prompt", "Response B", "gpt-3.5")

        assert cache.get("Same prompt", "gpt-4") == "Response A"
        assert cache.get("Same prompt", "gpt-3.5") == "Response B"

    def test_hit_count_increments(self, cache):
        """Hit count increments on cache hits."""
        cache.set("Test prompt", "Response", "gpt-4")

        cache.get("Test prompt", "gpt-4")
        cache.get("Test prompt", "gpt-4")
        cache.get("Test prompt", "gpt-4")

        stats = cache.get_stats()
        assert stats["total_hits"] >= 3


class TestPromptNormalization:
    """Tests for prompt normalization."""

    def test_whitespace_normalized(self, cache):
        """Extra whitespace is normalized."""
        cache.set("Hello   world", "Response", "gpt-4")
        result = cache.get("Hello world", "gpt-4")

        assert result == "Response"

    def test_leading_trailing_whitespace(self, cache):
        """Leading/trailing whitespace is stripped."""
        cache.set("  Test prompt  ", "Response", "gpt-4")
        result = cache.get("Test prompt", "gpt-4")

        assert result == "Response"


class TestTTL:
    """Tests for TTL expiration."""

    def test_expired_entry_returns_none(self, temp_lloyd_dir):
        """Expired entries return None."""
        cache = SemanticCache(lloyd_dir=temp_lloyd_dir, default_ttl=0.1)
        cache.set("Test", "Response", "gpt-4")

        # Wait for expiration
        time.sleep(0.2)

        result = cache.get("Test", "gpt-4")
        assert result is None

    def test_custom_ttl(self, cache):
        """Can set custom TTL per entry."""
        cache.set("Short lived", "Response", "gpt-4", ttl=0.1)
        cache.set("Long lived", "Response", "gpt-4", ttl=3600)

        time.sleep(0.2)

        assert cache.get("Short lived", "gpt-4") is None
        assert cache.get("Long lived", "gpt-4") == "Response"


class TestDiskPersistence:
    """Tests for disk persistence."""

    def test_persists_to_disk(self, temp_lloyd_dir):
        """Cache entries persist to disk."""
        cache1 = SemanticCache(lloyd_dir=temp_lloyd_dir)
        cache1.set("Persist me", "Persisted response", "gpt-4")

        # Create new cache instance
        cache2 = SemanticCache(lloyd_dir=temp_lloyd_dir)
        result = cache2.get("Persist me", "gpt-4")

        assert result == "Persisted response"

    def test_clear_removes_disk_cache(self, temp_lloyd_dir):
        """Clear removes disk cache."""
        cache = SemanticCache(lloyd_dir=temp_lloyd_dir)
        cache.set("To be cleared", "Response", "gpt-4")

        cache.clear()

        assert cache.get("To be cleared", "gpt-4") is None
        assert not (temp_lloyd_dir / "cache").exists()


class TestEviction:
    """Tests for cache eviction."""

    def test_evicts_oldest_when_full(self, temp_lloyd_dir):
        """Evicts oldest entries when over limit."""
        cache = SemanticCache(
            lloyd_dir=temp_lloyd_dir,
            max_memory_entries=3,
        )

        # Add more than limit
        cache.set("Entry 1", "R1", "gpt-4")
        time.sleep(0.01)  # Ensure different timestamps
        cache.set("Entry 2", "R2", "gpt-4")
        time.sleep(0.01)
        cache.set("Entry 3", "R3", "gpt-4")
        time.sleep(0.01)
        cache.set("Entry 4", "R4", "gpt-4")

        stats = cache.get_stats()
        assert stats["memory_entries"] <= 3


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_is_expired_fresh(self):
        """Fresh entry is not expired."""
        entry = CacheEntry(
            prompt_hash="abc",
            response="test",
            model="gpt-4",
            timestamp=time.time(),
            ttl=3600,
        )
        assert not entry.is_expired()

    def test_is_expired_old(self):
        """Old entry is expired."""
        entry = CacheEntry(
            prompt_hash="abc",
            response="test",
            model="gpt-4",
            timestamp=time.time() - 7200,  # 2 hours ago
            ttl=3600,  # 1 hour TTL
        )
        assert entry.is_expired()

    def test_to_dict_from_dict(self):
        """Can serialize and deserialize."""
        entry = CacheEntry(
            prompt_hash="abc123",
            response="test response",
            model="gpt-4",
            timestamp=time.time(),
            ttl=3600,
            hit_count=5,
        )

        data = entry.to_dict()
        restored = CacheEntry.from_dict(data)

        assert restored.prompt_hash == entry.prompt_hash
        assert restored.response == entry.response
        assert restored.hit_count == entry.hit_count


class TestCachedLlmCall:
    """Tests for cached_llm_call wrapper."""

    def test_calls_llm_on_miss(self, temp_lloyd_dir):
        """Calls LLM function on cache miss."""
        cache = SemanticCache(lloyd_dir=temp_lloyd_dir)
        call_count = [0]

        def mock_llm(prompt):
            call_count[0] += 1
            return "LLM response"

        result = cached_llm_call("Test prompt", mock_llm, "gpt-4", cache)

        assert result == "LLM response"
        assert call_count[0] == 1

    def test_uses_cache_on_hit(self, temp_lloyd_dir):
        """Uses cache on cache hit."""
        cache = SemanticCache(lloyd_dir=temp_lloyd_dir)
        call_count = [0]

        def mock_llm(prompt):
            call_count[0] += 1
            return "LLM response"

        # First call - cache miss
        cached_llm_call("Test prompt", mock_llm, "gpt-4", cache)

        # Second call - cache hit
        result = cached_llm_call("Test prompt", mock_llm, "gpt-4", cache)

        assert result == "LLM response"
        assert call_count[0] == 1  # Only called once

    def test_bypass_cache(self, temp_lloyd_dir):
        """Can bypass cache with use_cache=False."""
        cache = SemanticCache(lloyd_dir=temp_lloyd_dir)
        call_count = [0]

        def mock_llm(prompt):
            call_count[0] += 1
            return f"Response {call_count[0]}"

        cached_llm_call("Test", mock_llm, "gpt-4", cache, use_cache=False)
        result = cached_llm_call("Test", mock_llm, "gpt-4", cache, use_cache=False)

        assert call_count[0] == 2
        assert result == "Response 2"


class TestGetStats:
    """Tests for cache statistics."""

    def test_get_stats_returns_info(self, cache):
        """get_stats returns expected info."""
        cache.set("Test", "Response", "gpt-4")

        stats = cache.get_stats()

        assert "memory_entries" in stats
        assert "total_hits" in stats
        assert "cache_dir" in stats
        assert stats["memory_entries"] >= 1
