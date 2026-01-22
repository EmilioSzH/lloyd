"""Tests for AEGIS routing logic."""

from lloyd.memory.prd_manager import PRDManager
from lloyd.orchestrator.router import (
    check_all_complete,
    check_blocked,
    get_next_story,
)


def test_get_next_story_empty() -> None:
    """Test get_next_story with no stories."""
    manager = PRDManager()
    prd = manager.create_new("Test")

    result = get_next_story(prd)
    assert result is None


def test_get_next_story_with_dependencies() -> None:
    """Test get_next_story respects dependencies."""
    manager = PRDManager()
    prd = manager.create_new("Test")

    # Add stories where story-002 depends on story-001
    manager.add_story(prd, "First", "Desc", ["C1"], priority=2)
    manager.add_story(prd, "Second", "Desc", ["C2"], priority=1, dependencies=["story-001"])

    # Even though story-002 has higher priority (1), story-001 should come first
    # because story-002 depends on it
    next_story = get_next_story(prd)
    assert next_story is not None
    assert next_story.title == "First"

    # Mark first complete
    prd.stories[0].passes = True

    # Now second should be available
    next_story = get_next_story(prd)
    assert next_story is not None
    assert next_story.title == "Second"


def test_check_all_complete() -> None:
    """Test check_all_complete."""
    manager = PRDManager()
    prd = manager.create_new("Test")
    manager.add_story(prd, "Story 1", "Desc", ["C1"])
    manager.add_story(prd, "Story 2", "Desc", ["C2"])

    assert check_all_complete(prd) is False

    prd.stories[0].passes = True
    assert check_all_complete(prd) is False

    prd.stories[1].passes = True
    assert check_all_complete(prd) is True


def test_check_blocked() -> None:
    """Test check_blocked."""
    manager = PRDManager()
    prd = manager.create_new("Test")
    manager.add_story(prd, "Story 1", "Desc", ["C1"])

    # Not blocked initially
    blocked = check_blocked(prd)
    assert len(blocked) == 0

    # Set attempts >= 3
    prd.stories[0].attempts = 3

    # Now blocked
    blocked = check_blocked(prd)
    assert len(blocked) == 1
    assert blocked[0].title == "Story 1"
