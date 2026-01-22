"""Tests for the PRD manager."""

import tempfile
from pathlib import Path

from lloyd.memory.prd_manager import PRDManager, Story


def test_create_new_prd() -> None:
    """Test creating a new PRD."""
    manager = PRDManager()
    prd = manager.create_new(
        project_name="Test Project",
        description="A test project",
    )

    assert prd.project_name == "Test Project"
    assert prd.description == "A test project"
    assert prd.status == "idle"
    assert len(prd.stories) == 0


def test_add_story() -> None:
    """Test adding a story to PRD."""
    manager = PRDManager()
    prd = manager.create_new("Test")

    story = manager.add_story(
        prd,
        title="Test Story",
        description="A test story",
        acceptance_criteria=["Criterion 1", "Criterion 2"],
        priority=1,
    )

    assert story.id == "story-001"
    assert story.title == "Test Story"
    assert len(story.acceptance_criteria) == 2
    assert len(prd.stories) == 1


def test_save_and_load_prd() -> None:
    """Test saving and loading PRD."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prd_path = Path(tmpdir) / "prd.json"
        manager = PRDManager(prd_path)

        # Create and save
        prd = manager.create_new("Test Project", "Description")
        manager.add_story(prd, "Story 1", "Desc", ["Criterion"])
        manager.save(prd)

        # Load and verify
        loaded = manager.load()
        assert loaded is not None
        assert loaded.project_name == "Test Project"
        assert len(loaded.stories) == 1


def test_get_next_story() -> None:
    """Test getting the next story to work on."""
    manager = PRDManager()
    prd = manager.create_new("Test")

    # Add stories with dependencies
    manager.add_story(prd, "Story 1", "First", ["C1"], priority=1)
    manager.add_story(prd, "Story 2", "Second", ["C2"], priority=2, dependencies=["story-001"])

    # First story should be returned
    next_story = manager.get_next_story(prd)
    assert next_story is not None
    assert next_story.title == "Story 1"

    # Mark first as complete
    prd.stories[0].passes = True

    # Second story should now be available
    next_story = manager.get_next_story(prd)
    assert next_story is not None
    assert next_story.title == "Story 2"


def test_update_story() -> None:
    """Test updating a story."""
    manager = PRDManager()
    prd = manager.create_new("Test")
    manager.add_story(prd, "Test Story", "Desc", ["Criterion"])

    # Update story
    result = manager.update_story(prd, "story-001", passes=True, attempts=2)

    assert result is True
    assert prd.stories[0].passes is True
    assert prd.stories[0].attempts == 2


def test_get_status_summary() -> None:
    """Test getting status summary."""
    manager = PRDManager()
    prd = manager.create_new("Test")
    manager.add_story(prd, "Story 1", "Desc", ["C1"])
    manager.add_story(prd, "Story 2", "Desc", ["C2"])
    prd.stories[0].passes = True

    summary = manager.get_status_summary(prd)

    assert summary["total_stories"] == 2
    assert summary["completed"] == 1
    assert summary["completion_percentage"] == 50.0


def test_story_model() -> None:
    """Test Story model."""
    story = Story(
        id="test-001",
        title="Test",
        description="Test description",
        acceptanceCriteria=["Criterion 1"],
    )

    assert story.id == "test-001"
    assert story.passes is False
    assert story.attempts == 0
