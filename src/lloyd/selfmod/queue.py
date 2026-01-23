"""Queue for self-modification tasks."""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


@dataclass
class SelfModTask:
    """A self-modification task."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    risk_level: str = "moderate"
    status: Literal[
        "queued",
        "in_progress",
        "testing",
        "awaiting_gpu",
        "awaiting_approval",
        "merged",
        "failed",
        "rejected",
    ] = "queued"
    clone_path: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    test_results: dict = field(default_factory=dict)
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "risk_level": self.risk_level,
            "status": self.status,
            "clone_path": self.clone_path,
            "created_at": self.created_at.isoformat(),
            "test_results": {k: list(v) for k, v in self.test_results.items()},
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SelfModTask":
        """Create from dictionary."""
        task = cls(
            task_id=data["task_id"],
            description=data["description"],
            risk_level=data["risk_level"],
            status=data["status"],
            clone_path=data.get("clone_path"),
            test_results={k: tuple(v) for k, v in data.get("test_results", {}).items()},
            error_message=data.get("error_message"),
        )
        if data.get("created_at"):
            task.created_at = datetime.fromisoformat(data["created_at"])
        return task


class SelfModQueue:
    """Persistent queue for self-modification tasks."""

    def __init__(self, lloyd_dir: Path | None = None):
        """Initialize the queue.

        Args:
            lloyd_dir: Lloyd data directory. Defaults to .lloyd
        """
        self.lloyd_dir = lloyd_dir or Path(".lloyd")
        self.queue_file = self.lloyd_dir / "selfmod" / "queue.json"

    def _ensure_dir(self) -> None:
        """Ensure the queue directory exists."""
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[SelfModTask]:
        """Load tasks from storage."""
        if not self.queue_file.exists():
            return []
        with open(self.queue_file, encoding="utf-8") as f:
            return [SelfModTask.from_dict(d) for d in json.load(f)]

    def _save(self, tasks: list[SelfModTask]) -> None:
        """Save tasks to storage."""
        self._ensure_dir()
        with open(self.queue_file, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in tasks], f, indent=2)

    def add(self, task: SelfModTask) -> None:
        """Add a task to the queue."""
        tasks = self._load()
        tasks.append(task)
        self._save(tasks)

    def get(self, task_id: str) -> SelfModTask | None:
        """Get a task by ID."""
        return next((t for t in self._load() if t.task_id == task_id), None)

    def update(self, task: SelfModTask) -> None:
        """Update a task in the queue."""
        tasks = self._load()
        for i, t in enumerate(tasks):
            if t.task_id == task.task_id:
                tasks[i] = task
                break
        self._save(tasks)

    def get_by_status(self, status: str) -> list[SelfModTask]:
        """Get all tasks with a specific status."""
        return [t for t in self._load() if t.status == status]

    def list_all(self) -> list[SelfModTask]:
        """List all tasks."""
        return self._load()

    def delete(self, task_id: str) -> bool:
        """Delete a task by ID."""
        tasks = self._load()
        original_len = len(tasks)
        tasks = [t for t in tasks if t.task_id != task_id]
        if len(tasks) < original_len:
            self._save(tasks)
            return True
        return False
