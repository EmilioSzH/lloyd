"""Tests for parallel story execution."""

import json
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest

from lloyd.memory.prd_manager import PRD, PRDManager, Story, StoryStatus
from lloyd.orchestrator.parallel_executor import ParallelStoryExecutor, StoryResult
from lloyd.orchestrator.router import get_ready_stories
from lloyd.orchestrator.thread_safe_state import ThreadSafeStateManager


@pytest.fixture
def temp_prd_path(tmp_path: Path) -> Path:
    """Create a temporary PRD path."""
    return tmp_path / ".lloyd" / "prd.json"


@pytest.fixture
def prd_manager(temp_prd_path: Path) -> PRDManager:
    """Create a PRD manager with temp path."""
    return PRDManager(temp_prd_path)


@pytest.fixture
def state_manager(temp_prd_path: Path) -> ThreadSafeStateManager:
    """Create a thread-safe state manager with temp path."""
    return ThreadSafeStateManager(temp_prd_path)


@pytest.fixture
def sample_prd(prd_manager: PRDManager) -> PRD:
    """Create a sample PRD with multiple stories."""
    prd = prd_manager.create_new("Test Project", "Test description")

    # Add independent stories (no dependencies)
    prd_manager.add_story(prd, "Story 1", "First story", ["AC1"], priority=1)
    prd_manager.add_story(prd, "Story 2", "Second story", ["AC2"], priority=1)
    prd_manager.add_story(prd, "Story 3", "Third story", ["AC3"], priority=1)

    # Add dependent story
    prd_manager.add_story(
        prd,
        "Story 4",
        "Depends on Story 1",
        ["AC4"],
        priority=2,
        dependencies=["story-001"],
    )

    prd_manager.save(prd)
    return prd


class TestStoryStatus:
    """Tests for StoryStatus enum."""

    def test_story_status_values(self) -> None:
        """Test StoryStatus enum values."""
        assert StoryStatus.PENDING == "pending"
        assert StoryStatus.IN_PROGRESS == "in_progress"
        assert StoryStatus.COMPLETED == "completed"
        assert StoryStatus.FAILED == "failed"
        assert StoryStatus.BLOCKED == "blocked"

    def test_story_default_status(self) -> None:
        """Test Story default status is PENDING."""
        story = Story(
            id="test-001",
            title="Test",
            description="Test description",
        )
        assert story.status == StoryStatus.PENDING


class TestGetReadyStories:
    """Tests for get_ready_stories function."""

    def test_get_ready_stories_empty_prd(self, prd_manager: PRDManager) -> None:
        """Test with empty PRD."""
        prd = prd_manager.create_new("Test")
        result = get_ready_stories(prd)
        assert result == []

    def test_get_ready_stories_all_independent(self, sample_prd: PRD) -> None:
        """Test getting ready stories when all are independent."""
        result = get_ready_stories(sample_prd, max_count=10)
        # Should get stories 1, 2, 3 (story 4 has a dependency)
        assert len(result) == 3
        assert {s.id for s in result} == {"story-001", "story-002", "story-003"}

    def test_get_ready_stories_respects_max_count(self, sample_prd: PRD) -> None:
        """Test max_count parameter."""
        result = get_ready_stories(sample_prd, max_count=2)
        assert len(result) == 2

    def test_get_ready_stories_excludes_in_progress(self, sample_prd: PRD) -> None:
        """Test that in-progress stories are excluded."""
        sample_prd.stories[0].status = StoryStatus.IN_PROGRESS
        result = get_ready_stories(sample_prd, max_count=10)
        assert len(result) == 2
        assert "story-001" not in {s.id for s in result}

    def test_get_ready_stories_excludes_blocked(self, sample_prd: PRD) -> None:
        """Test that blocked stories are excluded."""
        sample_prd.stories[0].status = StoryStatus.BLOCKED
        result = get_ready_stories(sample_prd, max_count=10)
        assert len(result) == 2
        assert "story-001" not in {s.id for s in result}

    def test_get_ready_stories_includes_failed(self, sample_prd: PRD) -> None:
        """Test that failed stories (retry) are included."""
        sample_prd.stories[0].status = StoryStatus.FAILED
        result = get_ready_stories(sample_prd, max_count=10)
        # Failed stories should still be available for retry
        assert len(result) == 3

    def test_get_ready_stories_dependency_satisfied(self, sample_prd: PRD) -> None:
        """Test that story with satisfied dependency becomes ready."""
        # Mark story-001 as complete
        sample_prd.stories[0].passes = True
        result = get_ready_stories(sample_prd, max_count=10)
        # Now story-004 should also be ready
        assert len(result) == 3
        assert "story-004" in {s.id for s in result}


class TestThreadSafeStateManager:
    """Tests for ThreadSafeStateManager."""

    def test_claim_story_success(
        self, state_manager: ThreadSafeStateManager, sample_prd: PRD
    ) -> None:
        """Test successfully claiming a story."""
        story = state_manager.claim_story("story-001", "worker-1")
        assert story is not None
        assert story.id == "story-001"
        assert story.status == StoryStatus.IN_PROGRESS
        assert story.worker_id == "worker-1"

    def test_claim_story_already_claimed(
        self, state_manager: ThreadSafeStateManager, sample_prd: PRD
    ) -> None:
        """Test claiming already claimed story."""
        # First claim succeeds
        story1 = state_manager.claim_story("story-001", "worker-1")
        assert story1 is not None

        # Second claim fails
        story2 = state_manager.claim_story("story-001", "worker-2")
        assert story2 is None

    def test_claim_story_completed(
        self, state_manager: ThreadSafeStateManager, sample_prd: PRD
    ) -> None:
        """Test claiming completed story."""
        # Mark story as completed
        state_manager.claim_story("story-001", "worker-1")
        state_manager.release_story("story-001", passed=True)

        # Try to claim again
        story = state_manager.claim_story("story-001", "worker-2")
        assert story is None

    def test_release_story_passed(
        self, state_manager: ThreadSafeStateManager, sample_prd: PRD
    ) -> None:
        """Test releasing story as passed."""
        state_manager.claim_story("story-001", "worker-1")
        result = state_manager.release_story("story-001", passed=True)
        assert result is True

        # Verify state
        prd = state_manager.get_prd_snapshot()
        assert prd is not None
        story = next(s for s in prd.stories if s.id == "story-001")
        assert story.passes is True
        assert story.status == StoryStatus.COMPLETED
        assert story.worker_id is None

    def test_release_story_failed(
        self, state_manager: ThreadSafeStateManager, sample_prd: PRD
    ) -> None:
        """Test releasing story as failed."""
        state_manager.claim_story("story-001", "worker-1")
        result = state_manager.release_story("story-001", passed=False)
        assert result is True

        prd = state_manager.get_prd_snapshot()
        assert prd is not None
        story = next(s for s in prd.stories if s.id == "story-001")
        assert story.passes is False
        assert story.status == StoryStatus.FAILED
        assert story.attempts == 1

    def test_release_story_blocked_after_max_attempts(
        self, state_manager: ThreadSafeStateManager, sample_prd: PRD
    ) -> None:
        """Test story becomes blocked after max attempts."""
        for i in range(3):
            state_manager.claim_story("story-001", f"worker-{i}")
            state_manager.release_story("story-001", passed=False)

        prd = state_manager.get_prd_snapshot()
        assert prd is not None
        story = next(s for s in prd.stories if s.id == "story-001")
        assert story.status == StoryStatus.BLOCKED
        assert story.attempts == 3

    def test_get_ready_stories(
        self, state_manager: ThreadSafeStateManager, sample_prd: PRD
    ) -> None:
        """Test getting ready stories through state manager."""
        stories = state_manager.get_ready_stories(max_count=5)
        assert len(stories) == 3

    def test_get_status_summary(
        self, state_manager: ThreadSafeStateManager, sample_prd: PRD
    ) -> None:
        """Test status summary."""
        # Complete one story
        state_manager.claim_story("story-001", "worker-1")
        state_manager.release_story("story-001", passed=True)

        # Fail another
        state_manager.claim_story("story-002", "worker-2")
        state_manager.release_story("story-002", passed=False)

        summary = state_manager.get_status_summary()
        assert summary["total"] == 4
        assert summary["completed"] == 1
        assert summary["failed"] == 1
        assert summary["pending"] == 2  # story-003 and story-004

    def test_is_all_complete(
        self, state_manager: ThreadSafeStateManager, prd_manager: PRDManager
    ) -> None:
        """Test is_all_complete check."""
        # Create simple PRD with one story
        prd = prd_manager.create_new("Test")
        prd_manager.add_story(prd, "Only Story", "Desc", ["AC"])
        prd_manager.save(prd)

        assert state_manager.is_all_complete() is False

        state_manager.claim_story("story-001", "worker")
        state_manager.release_story("story-001", passed=True)

        assert state_manager.is_all_complete() is True


class TestParallelStoryExecutor:
    """Tests for ParallelStoryExecutor."""

    def test_execute_story_success(
        self, state_manager: ThreadSafeStateManager, sample_prd: PRD
    ) -> None:
        """Test executing a single story successfully."""
        def mock_execute(story: Story) -> dict[str, Any]:
            return {"result": "success"}

        def mock_verify(story: Story, result: Any) -> bool:
            return True

        with ParallelStoryExecutor(state_manager, max_workers=1) as executor:
            story = sample_prd.stories[0]
            result = executor.execute_story(story, mock_execute, mock_verify, "test-worker")

        assert result.passed is True
        assert result.story_id == "story-001"
        assert result.error is None

    def test_execute_story_failure(
        self, state_manager: ThreadSafeStateManager, sample_prd: PRD
    ) -> None:
        """Test executing a story that fails verification."""
        def mock_execute(story: Story) -> dict[str, Any]:
            return {"result": "done"}

        def mock_verify(story: Story, result: Any) -> bool:
            return False

        with ParallelStoryExecutor(state_manager, max_workers=1) as executor:
            story = sample_prd.stories[0]
            result = executor.execute_story(story, mock_execute, mock_verify, "test-worker")

        assert result.passed is False
        assert result.story_id == "story-001"

    def test_execute_story_exception(
        self, state_manager: ThreadSafeStateManager, sample_prd: PRD
    ) -> None:
        """Test handling exception during execution."""
        def mock_execute(story: Story) -> dict[str, Any]:
            raise ValueError("Test error")

        def mock_verify(story: Story, result: Any) -> bool:
            return True

        with ParallelStoryExecutor(state_manager, max_workers=1) as executor:
            story = sample_prd.stories[0]
            result = executor.execute_story(story, mock_execute, mock_verify, "test-worker")

        assert result.passed is False
        assert "Test error" in (result.error or "")

    def test_run_parallel_batch(
        self, state_manager: ThreadSafeStateManager, sample_prd: PRD
    ) -> None:
        """Test running a batch of stories in parallel."""
        execution_order: list[str] = []

        def mock_execute(story: Story) -> dict[str, Any]:
            execution_order.append(story.id)
            time.sleep(0.05)  # Simulate work
            return {"result": "done"}

        def mock_verify(story: Story, result: Any) -> bool:
            return True

        stories = [s for s in sample_prd.stories if not s.dependencies]

        with ParallelStoryExecutor(state_manager, max_workers=3) as executor:
            results = executor.run_parallel_batch(stories, mock_execute, mock_verify)

        assert len(results) == 3
        assert all(r.passed for r in results)
        # With parallel execution, all stories should be started quickly
        assert len(execution_order) == 3

    def test_run_parallel_batch_mixed_results(
        self, state_manager: ThreadSafeStateManager, sample_prd: PRD
    ) -> None:
        """Test batch with mixed pass/fail results."""
        def mock_execute(story: Story) -> dict[str, Any]:
            return {"story_id": story.id}

        def mock_verify(story: Story, result: Any) -> bool:
            # Only story-001 passes
            return story.id == "story-001"

        stories = [s for s in sample_prd.stories if not s.dependencies]

        with ParallelStoryExecutor(state_manager, max_workers=3) as executor:
            results = executor.run_parallel_batch(stories, mock_execute, mock_verify)

        passed = [r for r in results if r.passed]
        failed = [r for r in results if not r.passed]

        assert len(passed) == 1
        assert len(failed) == 2

    def test_concurrent_claim_prevention(
        self, state_manager: ThreadSafeStateManager, sample_prd: PRD
    ) -> None:
        """Test that concurrent workers don't double-claim stories."""
        claimed_count = 0

        def mock_execute(story: Story) -> dict[str, Any]:
            nonlocal claimed_count
            claimed_count += 1
            time.sleep(0.1)  # Hold the story
            return {"done": True}

        def mock_verify(story: Story, result: Any) -> bool:
            return True

        # Only one story, but try with multiple workers
        stories = [sample_prd.stories[0]]

        with ParallelStoryExecutor(state_manager, max_workers=3) as executor:
            # Submit the same story multiple times (simulating race condition)
            results = executor.run_parallel_batch(
                stories * 3, mock_execute, mock_verify
            )

        # Only one should have actually executed
        successful = [r for r in results if r.passed]
        assert len(successful) == 1


class TestIntegration:
    """Integration tests for parallel execution."""

    def test_full_workflow_parallel(
        self, prd_manager: PRDManager, state_manager: ThreadSafeStateManager
    ) -> None:
        """Test complete parallel workflow."""
        # Create PRD with dependencies
        prd = prd_manager.create_new("Integration Test")
        prd_manager.add_story(prd, "Setup", "Setup task", ["Done"], priority=1)
        prd_manager.add_story(prd, "Feature A", "Feature A", ["Done"], priority=2)
        prd_manager.add_story(prd, "Feature B", "Feature B", ["Done"], priority=2)
        prd_manager.add_story(
            prd,
            "Integration",
            "Integrate features",
            ["Done"],
            priority=3,
            dependencies=["story-002", "story-003"],
        )
        prd_manager.save(prd)

        def mock_execute(story: Story) -> dict[str, Any]:
            return {"completed": story.id}

        def mock_verify(story: Story, result: Any) -> bool:
            return True

        with ParallelStoryExecutor(state_manager, max_workers=2) as executor:
            # First batch: Setup only (others depend on it or have no deps met)
            ready = state_manager.get_ready_stories(max_count=3)
            assert len(ready) == 3  # Setup, Feature A, Feature B

            results = executor.run_parallel_batch(ready, mock_execute, mock_verify)
            assert all(r.passed for r in results)

            # Second batch: Integration (dependencies now met)
            ready = state_manager.get_ready_stories(max_count=3)
            assert len(ready) == 1
            assert ready[0].title == "Integration"

            results = executor.run_parallel_batch(ready, mock_execute, mock_verify)
            assert all(r.passed for r in results)

        # Verify all complete
        assert state_manager.is_all_complete() is True
