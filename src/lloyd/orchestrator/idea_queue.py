"""Idea Queue for batch processing multiple ideas."""

import json
import uuid
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class IdeaStatus(str, Enum):
    """Status of an idea in the queue."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class QueuedIdea(BaseModel):
    """A single idea in the queue."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str
    status: IdeaStatus = IdeaStatus.PENDING
    priority: int = 1  # Lower = higher priority
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    prd_path: str | None = None  # Path to PRD created for this idea
    iterations: int = 0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()


class IdeaQueue:
    """Manages a queue of ideas for batch processing."""

    def __init__(self, queue_path: str | Path = ".lloyd/idea_queue.json") -> None:
        """Initialize the idea queue.

        Args:
            queue_path: Path to the queue JSON file.
        """
        self.queue_path = Path(queue_path)
        self._ideas: list[QueuedIdea] = []
        self._load()

    def _load(self) -> None:
        """Load queue from disk."""
        if self.queue_path.exists():
            try:
                with open(self.queue_path) as f:
                    data = json.load(f)
                self._ideas = [QueuedIdea(**idea) for idea in data.get("ideas", [])]
            except Exception:
                self._ideas = []
        else:
            self._ideas = []

    def _save(self) -> None:
        """Save queue to disk."""
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.queue_path, "w") as f:
            json.dump(
                {
                    "ideas": [idea.model_dump() for idea in self._ideas],
                    "updated_at": datetime.now(UTC).isoformat(),
                },
                f,
                indent=2,
            )

    def add(
        self,
        description: str,
        priority: int = 1,
        idea_id: str | None = None,
    ) -> QueuedIdea:
        """Add an idea to the queue.

        Args:
            description: The idea description or spec content.
            priority: Priority (lower = higher priority).
            idea_id: Optional custom ID.

        Returns:
            The created QueuedIdea.
        """
        idea = QueuedIdea(
            description=description,
            priority=priority,
        )
        if idea_id:
            idea.id = idea_id

        self._ideas.append(idea)
        self._save()
        return idea

    def add_many(
        self,
        descriptions: list[str],
        priority: int = 1,
    ) -> list[QueuedIdea]:
        """Add multiple ideas to the queue.

        Args:
            descriptions: List of idea descriptions.
            priority: Priority for all ideas.

        Returns:
            List of created QueuedIdeas.
        """
        ideas = []
        for i, desc in enumerate(descriptions):
            idea = QueuedIdea(
                description=desc,
                priority=priority + i,  # Maintain order
            )
            self._ideas.append(idea)
            ideas.append(idea)

        self._save()
        return ideas

    def get(self, idea_id: str) -> QueuedIdea | None:
        """Get an idea by ID.

        Args:
            idea_id: The idea ID.

        Returns:
            QueuedIdea if found, None otherwise.
        """
        for idea in self._ideas:
            if idea.id == idea_id:
                return idea
        return None

    def get_next(self) -> QueuedIdea | None:
        """Get the next pending idea (highest priority).

        Returns:
            Next QueuedIdea to process, or None if queue empty.
        """
        pending = [i for i in self._ideas if i.status == IdeaStatus.PENDING]
        if not pending:
            return None
        return min(pending, key=lambda i: i.priority)

    def start(self, idea_id: str) -> QueuedIdea | None:
        """Mark an idea as in progress.

        Args:
            idea_id: The idea ID.

        Returns:
            Updated QueuedIdea if found.
        """
        idea = self.get(idea_id)
        if idea:
            idea.status = IdeaStatus.IN_PROGRESS
            idea.started_at = datetime.now(UTC).isoformat()
            self._save()
        return idea

    def complete(
        self,
        idea_id: str,
        success: bool = True,
        error: str | None = None,
        iterations: int = 0,
        prd_path: str | None = None,
    ) -> QueuedIdea | None:
        """Mark an idea as completed.

        Args:
            idea_id: The idea ID.
            success: Whether it completed successfully.
            error: Error message if failed.
            iterations: Number of iterations used.
            prd_path: Path to the PRD created.

        Returns:
            Updated QueuedIdea if found.
        """
        idea = self.get(idea_id)
        if idea:
            idea.status = IdeaStatus.COMPLETED if success else IdeaStatus.FAILED
            idea.completed_at = datetime.now(UTC).isoformat()
            idea.error = error
            idea.iterations = iterations
            idea.prd_path = prd_path
            self._save()
        return idea

    def skip(self, idea_id: str, reason: str = "") -> QueuedIdea | None:
        """Skip an idea.

        Args:
            idea_id: The idea ID.
            reason: Reason for skipping.

        Returns:
            Updated QueuedIdea if found.
        """
        idea = self.get(idea_id)
        if idea:
            idea.status = IdeaStatus.SKIPPED
            idea.notes = reason
            self._save()
        return idea

    def remove(self, idea_id: str) -> bool:
        """Remove an idea from the queue.

        Args:
            idea_id: The idea ID.

        Returns:
            True if removed, False if not found.
        """
        for i, idea in enumerate(self._ideas):
            if idea.id == idea_id:
                self._ideas.pop(i)
                self._save()
                return True
        return False

    def clear_completed(self) -> int:
        """Remove all completed/failed/skipped ideas.

        Returns:
            Number of ideas removed.
        """
        original_count = len(self._ideas)
        self._ideas = [
            i
            for i in self._ideas
            if i.status not in (IdeaStatus.COMPLETED, IdeaStatus.FAILED, IdeaStatus.SKIPPED)
        ]
        removed = original_count - len(self._ideas)
        if removed > 0:
            self._save()
        return removed

    def list_all(self) -> list[QueuedIdea]:
        """Get all ideas in the queue.

        Returns:
            List of all QueuedIdeas.
        """
        return sorted(self._ideas, key=lambda i: (i.status != IdeaStatus.IN_PROGRESS, i.priority))

    def list_pending(self) -> list[QueuedIdea]:
        """Get all pending ideas.

        Returns:
            List of pending QueuedIdeas.
        """
        pending = [i for i in self._ideas if i.status == IdeaStatus.PENDING]
        return sorted(pending, key=lambda i: i.priority)

    def count(self) -> dict[str, int]:
        """Get counts by status.

        Returns:
            Dictionary of status -> count.
        """
        counts = {status.value: 0 for status in IdeaStatus}
        for idea in self._ideas:
            counts[idea.status.value] += 1
        counts["total"] = len(self._ideas)
        return counts

    def reorder(self, idea_id: str, new_priority: int) -> QueuedIdea | None:
        """Change priority of an idea.

        Args:
            idea_id: The idea ID.
            new_priority: New priority value.

        Returns:
            Updated QueuedIdea if found.
        """
        idea = self.get(idea_id)
        if idea:
            idea.priority = new_priority
            self._save()
        return idea
