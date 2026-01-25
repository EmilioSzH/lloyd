"""Tests for IdeaQueue."""

import tempfile
from pathlib import Path

import pytest

from lloyd.orchestrator.idea_queue import IdeaQueue, IdeaStatus, QueuedIdea


@pytest.fixture
def temp_queue():
    """Create a temporary queue."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queue_path = Path(tmpdir) / "queue.json"
        yield IdeaQueue(queue_path)


class TestQueuedIdea:
    """Tests for QueuedIdea model."""

    def test_creation(self):
        """Creates idea with defaults."""
        idea = QueuedIdea(description="Test idea")

        assert idea.description == "Test idea"
        assert idea.status == IdeaStatus.PENDING
        assert idea.priority == 1
        assert idea.id is not None
        assert idea.created_at is not None

    def test_to_dict(self):
        """Converts to dictionary."""
        idea = QueuedIdea(description="Test idea")
        d = idea.to_dict()

        assert d["description"] == "Test idea"
        assert d["status"] == "pending"


class TestIdeaQueueAdd:
    """Tests for adding ideas."""

    def test_add_single(self, temp_queue):
        """Adds a single idea."""
        idea = temp_queue.add("Build a website")

        assert idea.description == "Build a website"
        assert idea.status == IdeaStatus.PENDING
        assert len(temp_queue.list_all()) == 1

    def test_add_with_priority(self, temp_queue):
        """Adds idea with priority."""
        idea = temp_queue.add("Important idea", priority=0)

        assert idea.priority == 0

    def test_add_with_custom_id(self, temp_queue):
        """Adds idea with custom ID."""
        idea = temp_queue.add("Custom ID idea", idea_id="custom-123")

        assert idea.id == "custom-123"

    def test_add_many(self, temp_queue):
        """Adds multiple ideas."""
        ideas = temp_queue.add_many([
            "First idea",
            "Second idea",
            "Third idea",
        ])

        assert len(ideas) == 3
        assert len(temp_queue.list_all()) == 3
        # Check order maintained
        assert ideas[0].priority < ideas[1].priority < ideas[2].priority


class TestIdeaQueueGet:
    """Tests for getting ideas."""

    def test_get_by_id(self, temp_queue):
        """Gets idea by ID."""
        added = temp_queue.add("Test idea")
        found = temp_queue.get(added.id)

        assert found is not None
        assert found.description == "Test idea"

    def test_get_not_found(self, temp_queue):
        """Returns None for missing ID."""
        found = temp_queue.get("nonexistent")

        assert found is None

    def test_get_next(self, temp_queue):
        """Gets next pending idea by priority."""
        temp_queue.add("Low priority", priority=10)
        temp_queue.add("High priority", priority=1)
        temp_queue.add("Medium priority", priority=5)

        next_idea = temp_queue.get_next()

        assert next_idea is not None
        assert next_idea.description == "High priority"

    def test_get_next_empty(self, temp_queue):
        """Returns None for empty queue."""
        next_idea = temp_queue.get_next()

        assert next_idea is None

    def test_get_next_skips_non_pending(self, temp_queue):
        """Skips non-pending ideas."""
        idea1 = temp_queue.add("First", priority=1)
        temp_queue.add("Second", priority=2)

        # Mark first as in progress
        temp_queue.start(idea1.id)

        next_idea = temp_queue.get_next()

        assert next_idea is not None
        assert next_idea.description == "Second"


class TestIdeaQueueStatus:
    """Tests for status transitions."""

    def test_start(self, temp_queue):
        """Marks idea as in progress."""
        idea = temp_queue.add("Test idea")
        updated = temp_queue.start(idea.id)

        assert updated is not None
        assert updated.status == IdeaStatus.IN_PROGRESS
        assert updated.started_at is not None

    def test_complete_success(self, temp_queue):
        """Marks idea as completed."""
        idea = temp_queue.add("Test idea")
        temp_queue.start(idea.id)
        updated = temp_queue.complete(idea.id, success=True, iterations=5)

        assert updated is not None
        assert updated.status == IdeaStatus.COMPLETED
        assert updated.completed_at is not None
        assert updated.iterations == 5

    def test_complete_failure(self, temp_queue):
        """Marks idea as failed."""
        idea = temp_queue.add("Test idea")
        temp_queue.start(idea.id)
        updated = temp_queue.complete(idea.id, success=False, error="Something broke")

        assert updated is not None
        assert updated.status == IdeaStatus.FAILED
        assert updated.error == "Something broke"

    def test_skip(self, temp_queue):
        """Skips an idea."""
        idea = temp_queue.add("Test idea")
        updated = temp_queue.skip(idea.id, reason="Not relevant")

        assert updated is not None
        assert updated.status == IdeaStatus.SKIPPED
        assert updated.notes == "Not relevant"


class TestIdeaQueueRemove:
    """Tests for removing ideas."""

    def test_remove(self, temp_queue):
        """Removes an idea."""
        idea = temp_queue.add("Test idea")
        result = temp_queue.remove(idea.id)

        assert result is True
        assert len(temp_queue.list_all()) == 0

    def test_remove_not_found(self, temp_queue):
        """Returns False for missing ID."""
        result = temp_queue.remove("nonexistent")

        assert result is False

    def test_clear_completed(self, temp_queue):
        """Clears completed ideas."""
        idea1 = temp_queue.add("Pending")
        idea2 = temp_queue.add("To complete")
        idea3 = temp_queue.add("To fail")

        temp_queue.complete(idea2.id, success=True)
        temp_queue.complete(idea3.id, success=False)

        removed = temp_queue.clear_completed()

        assert removed == 2
        assert len(temp_queue.list_all()) == 1
        assert temp_queue.get(idea1.id) is not None


class TestIdeaQueueList:
    """Tests for listing ideas."""

    def test_list_all(self, temp_queue):
        """Lists all ideas."""
        temp_queue.add("First")
        temp_queue.add("Second")

        ideas = temp_queue.list_all()

        assert len(ideas) == 2

    def test_list_pending(self, temp_queue):
        """Lists only pending ideas."""
        idea1 = temp_queue.add("Pending")
        idea2 = temp_queue.add("Completed")

        temp_queue.complete(idea2.id, success=True)

        pending = temp_queue.list_pending()

        assert len(pending) == 1
        assert pending[0].id == idea1.id

    def test_count(self, temp_queue):
        """Gets counts by status."""
        idea1 = temp_queue.add("Pending")
        idea2 = temp_queue.add("In progress")
        idea3 = temp_queue.add("Completed")

        temp_queue.start(idea2.id)
        temp_queue.complete(idea3.id, success=True)

        counts = temp_queue.count()

        assert counts["pending"] == 1
        assert counts["in_progress"] == 1
        assert counts["completed"] == 1
        assert counts["total"] == 3


class TestIdeaQueuePersistence:
    """Tests for persistence."""

    def test_persists_on_add(self):
        """Saves queue when adding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = Path(tmpdir) / "queue.json"

            q1 = IdeaQueue(queue_path)
            q1.add("Test idea")

            # Load fresh
            q2 = IdeaQueue(queue_path)
            assert len(q2.list_all()) == 1

    def test_persists_on_update(self):
        """Saves queue when updating."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = Path(tmpdir) / "queue.json"

            q1 = IdeaQueue(queue_path)
            idea = q1.add("Test idea")
            q1.start(idea.id)

            # Load fresh
            q2 = IdeaQueue(queue_path)
            found = q2.get(idea.id)
            assert found is not None
            assert found.status == IdeaStatus.IN_PROGRESS


class TestIdeaQueueReorder:
    """Tests for reordering."""

    def test_reorder(self, temp_queue):
        """Changes idea priority."""
        idea = temp_queue.add("Test idea", priority=5)
        updated = temp_queue.reorder(idea.id, new_priority=1)

        assert updated is not None
        assert updated.priority == 1
