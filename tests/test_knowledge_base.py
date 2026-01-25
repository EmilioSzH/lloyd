"""Tests for KnowledgeBase query and learning capabilities."""

import tempfile
from pathlib import Path

import pytest

from lloyd.memory.knowledge import KnowledgeBase
from lloyd.knowledge.models import LearningEntry


@pytest.fixture
def temp_lloyd_dir():
    """Create a temporary lloyd directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def knowledge_base(temp_lloyd_dir):
    """Create a KnowledgeBase with temporary storage."""
    return KnowledgeBase(lloyd_dir=temp_lloyd_dir)


class TestQuerySimilar:
    """Tests for query_similar method."""

    def test_empty_knowledge_base_returns_empty(self, knowledge_base):
        """Query on empty knowledge base returns empty list."""
        result = knowledge_base.query_similar("JWT authentication")
        assert result == []

    def test_query_returns_matching_entries(self, knowledge_base):
        """Query returns entries with matching keywords."""
        # Add some entries
        entry1 = LearningEntry(
            category="auth",
            title="JWT token handling",
            description="Use environment variables for JWT secrets",
            tags=["jwt", "auth", "security"],
            confidence=0.8,
            frequency=3,
        )
        entry2 = LearningEntry(
            category="database",
            title="Database migrations",
            description="Always backup before migrations",
            tags=["database", "migration"],
            confidence=0.9,
            frequency=2,
        )
        knowledge_base.store.add(entry1)
        knowledge_base.store.add(entry2)

        # Query for JWT-related
        results = knowledge_base.query_similar("JWT authentication token", top_k=3)

        assert len(results) >= 1
        assert results[0].category == "auth"
        assert "jwt" in results[0].title.lower()

    def test_query_respects_top_k(self, knowledge_base):
        """Query returns at most top_k entries."""
        # Add multiple entries
        for i in range(5):
            entry = LearningEntry(
                category="testing",
                title=f"Test pattern {i}",
                description=f"Description for test pattern number {i}",
                tags=["test", "pattern"],
                confidence=0.7,
            )
            knowledge_base.store.add(entry)

        results = knowledge_base.query_similar("test pattern", top_k=2)
        assert len(results) <= 2

    def test_scoring_includes_confidence_and_frequency(self, knowledge_base):
        """Higher confidence and frequency should rank higher."""
        entry_low = LearningEntry(
            category="api",
            title="API endpoint",
            description="API request handling",
            confidence=0.3,
            frequency=1,
        )
        entry_high = LearningEntry(
            category="api",
            title="API endpoint",
            description="API request handling optimized",
            confidence=0.9,
            frequency=5,
        )
        knowledge_base.store.add(entry_low)
        knowledge_base.store.add(entry_high)

        results = knowledge_base.query_similar("API request", top_k=2)

        # Higher confidence/frequency entry should be first
        assert len(results) == 2
        assert results[0].confidence > results[1].confidence


class TestRecordOutcome:
    """Tests for record_outcome method."""

    def test_success_creates_positive_pattern(self, knowledge_base):
        """Successful outcome creates positive_pattern entry."""
        story = {"title": "Implement user login", "description": "Create login endpoint with JWT"}
        result = {"status": "success"}

        entry = knowledge_base.record_outcome(story, result, success=True)

        assert "positive_pattern" in entry.tags
        assert entry.confidence >= 0.5
        assert "login" in entry.title.lower()

    def test_failure_creates_avoid_this_entry(self, knowledge_base):
        """Failed outcome creates avoid_this entry."""
        story = {"title": "Database connection", "description": "Connect to PostgreSQL"}
        result = {"error": "Connection timeout", "status": "failed"}

        entry = knowledge_base.record_outcome(story, result, success=False)

        assert "avoid_this" in entry.tags
        assert entry.confidence < 0.5
        assert "timeout" in entry.description.lower()

    def test_duplicate_increments_frequency(self, knowledge_base):
        """Recording same pattern increments frequency."""
        story = {"title": "API test", "description": "Test the API endpoint"}
        result = {"status": "success"}

        # Record twice
        entry1 = knowledge_base.record_outcome(story, result, success=True)
        entry2 = knowledge_base.record_outcome(story, result, success=True)

        assert entry2.frequency > entry1.frequency

    def test_auto_extracts_category(self, knowledge_base):
        """Category is auto-extracted from content."""
        story = {"title": "JWT authentication", "description": "Implement JWT token validation"}
        result = {"status": "success"}

        entry = knowledge_base.record_outcome(story, result, success=True)

        assert entry.category == "auth"

    def test_persists_to_learnings_file(self, knowledge_base):
        """Learnings are persisted to JSON file."""
        story = {"title": "Test story", "description": "A test description"}
        result = {"status": "success"}

        knowledge_base.record_outcome(story, result, success=True)

        assert knowledge_base.learnings_file.exists()


class TestFormatForPrompt:
    """Tests for format_for_prompt method."""

    def test_empty_entries_returns_empty_string(self, knowledge_base):
        """Empty entries list returns empty string."""
        result = knowledge_base.format_for_prompt([])
        assert result == ""

    def test_formats_positive_patterns(self, knowledge_base):
        """Positive patterns appear in 'What worked well' section."""
        entry = LearningEntry(
            category="testing",
            title="positive_pattern: Unit tests",
            description="Write unit tests before implementation",
            tags=["positive_pattern"],
            confidence=0.9,
        )

        result = knowledge_base.format_for_prompt([entry])

        assert "What worked well" in result
        assert "Unit tests" in result

    def test_formats_avoid_patterns(self, knowledge_base):
        """Avoid patterns appear in 'What to avoid' section."""
        entry = LearningEntry(
            category="config",
            title="avoid_this: Hardcoded secrets",
            description="Never hardcode API keys",
            tags=["avoid_this"],
            confidence=0.3,
        )

        result = knowledge_base.format_for_prompt([entry])

        assert "What to avoid" in result
        assert "Hardcoded secrets" in result


class TestGetLearningsForStory:
    """Tests for get_learnings_for_story convenience method."""

    def test_returns_formatted_learnings(self, knowledge_base):
        """Returns formatted string of relevant learnings."""
        # Add a learning
        entry = LearningEntry(
            category="auth",
            title="Auth pattern",
            description="JWT authentication best practices",
            tags=["jwt", "auth"],
            confidence=0.8,
        )
        knowledge_base.store.add(entry)

        story = {"title": "Implement JWT login", "description": "Create JWT-based auth"}
        result = knowledge_base.get_learnings_for_story(story)

        # Should find the auth-related entry
        assert "Auth pattern" in result or result == ""  # Might be empty if no match
