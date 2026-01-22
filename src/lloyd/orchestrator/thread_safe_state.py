"""Thread-safe state management for parallel story execution."""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from filelock import FileLock

from lloyd.memory.prd_manager import PRD, Story, StoryStatus


class ThreadSafeStateManager:
    """Thread-safe manager for PRD state during parallel execution.

    Uses file locking to ensure atomic operations when multiple workers
    access the same PRD file.
    """

    def __init__(self, prd_path: str | Path = ".lloyd/prd.json") -> None:
        """Initialize the thread-safe state manager.

        Args:
            prd_path: Path to the PRD JSON file.
        """
        self.prd_path = Path(prd_path)
        self.lock_path = self.prd_path.with_suffix(".lock")
        self._lock = FileLock(str(self.lock_path), timeout=30)

    def _load_prd_unsafe(self) -> PRD | None:
        """Load PRD without locking (for internal use within locked context)."""
        if not self.prd_path.exists():
            return None
        try:
            with open(self.prd_path) as f:
                data = json.load(f)
            return PRD(**data)
        except Exception as e:
            print(f"Error loading PRD: {e}")
            return None

    def _save_prd_unsafe(self, prd: PRD) -> bool:
        """Save PRD without locking (for internal use within locked context)."""
        try:
            self.prd_path.parent.mkdir(parents=True, exist_ok=True)
            prd.updated_at = datetime.now(UTC).isoformat()

            # Update metadata
            prd.metadata.total_stories = len(prd.stories)
            prd.metadata.completed_stories = sum(1 for s in prd.stories if s.passes)
            prd.metadata.in_progress_stories = sum(
                1 for s in prd.stories if s.status == StoryStatus.IN_PROGRESS
            )

            with open(self.prd_path, "w") as f:
                json.dump(prd.model_dump(by_alias=True), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving PRD: {e}")
            return False

    def claim_story(self, story_id: str, worker_id: str | None = None) -> Story | None:
        """Atomically claim a story for execution.

        Args:
            story_id: ID of the story to claim.
            worker_id: Optional worker identifier. If not provided, generates a UUID.

        Returns:
            The claimed Story if successful, None if story is already claimed or not found.
        """
        if worker_id is None:
            worker_id = str(uuid.uuid4())[:8]

        with self._lock:
            prd = self._load_prd_unsafe()
            if prd is None:
                return None

            for story in prd.stories:
                if story.id == story_id:
                    # Check if story is available to claim
                    if story.status == StoryStatus.IN_PROGRESS:
                        # Already claimed by another worker
                        return None
                    if story.passes or story.status == StoryStatus.COMPLETED:
                        # Already completed
                        return None

                    # Claim the story
                    story.status = StoryStatus.IN_PROGRESS
                    story.worker_id = worker_id
                    story.started_at = datetime.now(UTC).isoformat()

                    self._save_prd_unsafe(prd)
                    return story

            return None

    def release_story(
        self, story_id: str, passed: bool, notes: str = ""
    ) -> bool:
        """Mark a story as complete or failed and release it.

        Args:
            story_id: ID of the story to release.
            passed: Whether the story passed verification.
            notes: Optional notes about the result.

        Returns:
            True if successfully released, False otherwise.
        """
        with self._lock:
            prd = self._load_prd_unsafe()
            if prd is None:
                return False

            for story in prd.stories:
                if story.id == story_id:
                    story.passes = passed
                    story.attempts += 1
                    story.completed_at = datetime.now(UTC).isoformat()
                    story.last_attempt_at = story.completed_at
                    story.worker_id = None

                    if passed:
                        story.status = StoryStatus.COMPLETED
                        if notes:
                            story.notes += f"\n{notes}" if story.notes else notes
                        else:
                            story.notes += (
                                f"\nPassed on attempt {story.attempts}"
                                if story.notes
                                else f"Passed on attempt {story.attempts}"
                            )
                    else:
                        # Check if blocked (too many attempts)
                        if story.attempts >= 3:
                            story.status = StoryStatus.BLOCKED
                        else:
                            story.status = StoryStatus.FAILED
                        if notes:
                            story.notes += f"\n{notes}" if story.notes else notes
                        else:
                            story.notes += (
                                f"\nFailed on attempt {story.attempts}"
                                if story.notes
                                else f"Failed on attempt {story.attempts}"
                            )

                    self._save_prd_unsafe(prd)
                    return True

            return False

    def get_ready_stories(self, max_count: int = 10) -> list[Story]:
        """Get all stories that are ready to execute.

        A story is ready if:
        - It has not passed (passes=False)
        - It is not currently in progress (status != IN_PROGRESS)
        - It is not blocked (status != BLOCKED)
        - All its dependencies have passed

        Args:
            max_count: Maximum number of stories to return.

        Returns:
            List of stories ready for execution, sorted by priority.
        """
        with self._lock:
            prd = self._load_prd_unsafe()
            if prd is None:
                return []

            completed_ids = {s.id for s in prd.stories if s.passes}
            ready_stories: list[Story] = []

            # Sort by priority (lower = higher priority)
            for story in sorted(prd.stories, key=lambda s: s.priority):
                if len(ready_stories) >= max_count:
                    break

                # Skip completed stories
                if story.passes:
                    continue

                # Skip in-progress stories
                if story.status == StoryStatus.IN_PROGRESS:
                    continue

                # Skip blocked stories
                if story.status == StoryStatus.BLOCKED:
                    continue

                # Check dependencies
                deps_met = all(dep in completed_ids for dep in story.dependencies)
                if deps_met:
                    ready_stories.append(story)

            return ready_stories

    def get_prd_snapshot(self) -> PRD | None:
        """Get a snapshot of the current PRD state.

        Returns:
            Current PRD state or None if not found.
        """
        with self._lock:
            return self._load_prd_unsafe()

    def get_status_summary(self) -> dict[str, Any]:
        """Get a summary of the current execution status.

        Returns:
            Dictionary with status counts and progress.
        """
        with self._lock:
            prd = self._load_prd_unsafe()
            if prd is None:
                return {
                    "total": 0,
                    "completed": 0,
                    "in_progress": 0,
                    "failed": 0,
                    "blocked": 0,
                    "pending": 0,
                    "completion_percentage": 0,
                }

            total = len(prd.stories)
            completed = sum(1 for s in prd.stories if s.passes)
            in_progress = sum(1 for s in prd.stories if s.status == StoryStatus.IN_PROGRESS)
            failed = sum(
                1
                for s in prd.stories
                if s.status == StoryStatus.FAILED and not s.passes
            )
            blocked = sum(1 for s in prd.stories if s.status == StoryStatus.BLOCKED)
            pending = total - completed - in_progress - failed - blocked

            return {
                "project_name": prd.project_name,
                "status": prd.status,
                "total": total,
                "completed": completed,
                "in_progress": in_progress,
                "failed": failed,
                "blocked": blocked,
                "pending": pending,
                "completion_percentage": (completed / total * 100) if total > 0 else 0,
            }

    def reset_failed_stories(self) -> int:
        """Reset all failed (not blocked) stories to pending status.

        Returns:
            Number of stories reset.
        """
        with self._lock:
            prd = self._load_prd_unsafe()
            if prd is None:
                return 0

            reset_count = 0
            for story in prd.stories:
                if story.status == StoryStatus.FAILED and not story.passes:
                    story.status = StoryStatus.PENDING
                    reset_count += 1

            if reset_count > 0:
                self._save_prd_unsafe(prd)

            return reset_count

    def is_all_complete(self) -> bool:
        """Check if all stories are complete.

        Returns:
            True if all stories have passed.
        """
        with self._lock:
            prd = self._load_prd_unsafe()
            if prd is None:
                return True  # No PRD = nothing to do

            return all(s.passes for s in prd.stories)

    def is_blocked(self) -> bool:
        """Check if execution is blocked.

        Returns:
            True if all remaining stories are blocked.
        """
        with self._lock:
            prd = self._load_prd_unsafe()
            if prd is None:
                return False

            incomplete = [s for s in prd.stories if not s.passes]
            if not incomplete:
                return False

            # Check if all incomplete stories are blocked
            return all(s.status == StoryStatus.BLOCKED for s in incomplete)
