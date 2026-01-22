"""Task metrics tracking for Lloyd."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal


@dataclass
class TaskMetrics:
    """Metrics for a single task execution."""

    task_id: str
    idea: str
    complexity: str
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    agents_used: list[str] = field(default_factory=list)
    iterations: int = 0
    outcome: Literal["success", "failure", "timeout"] | None = None

    def complete(self, outcome: Literal["success", "failure", "timeout"]) -> None:
        """Mark the task as complete.

        Args:
            outcome: The task outcome.
        """
        self.completed_at = datetime.now()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        self.outcome = outcome

    @property
    def duration_human(self) -> str:
        """Get human-readable duration string."""
        if self.duration_seconds is None:
            return "in progress"
        if self.duration_seconds < 60:
            return f"{self.duration_seconds:.1f}s"
        elif self.duration_seconds < 3600:
            return f"{self.duration_seconds / 60:.1f}m"
        else:
            return f"{self.duration_seconds / 3600:.1f}h"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "idea": self.idea,
            "complexity": self.complexity,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "duration_human": self.duration_human,
            "agents_used": self.agents_used,
            "iterations": self.iterations,
            "outcome": self.outcome,
        }


class MetricsStore:
    """Persistent storage for task metrics."""

    def __init__(self, lloyd_dir: Path | None = None) -> None:
        """Initialize the metrics store.

        Args:
            lloyd_dir: Lloyd data directory. Defaults to .lloyd
        """
        self.lloyd_dir = lloyd_dir or Path(".lloyd")
        self.metrics_file = self.lloyd_dir / "metrics" / "tasks.jsonl"

    def save(self, metrics: TaskMetrics) -> None:
        """Save task metrics to the store.

        Args:
            metrics: TaskMetrics to save.
        """
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metrics_file, "a") as f:
            f.write(json.dumps(metrics.to_dict()) + "\n")

    def get_recent(self, n: int = 10) -> list[dict]:
        """Get the most recent task metrics.

        Args:
            n: Number of recent tasks to return.

        Returns:
            List of task metric dictionaries.
        """
        if not self.metrics_file.exists():
            return []
        with open(self.metrics_file) as f:
            lines = f.readlines()
        return [json.loads(line) for line in lines[-n:]]

    def get_stats(self) -> dict:
        """Get aggregate statistics.

        Returns:
            Dictionary with aggregate stats.
        """
        metrics = self.get_recent(100)
        if not metrics:
            return {"total": 0}

        successful = [m for m in metrics if m.get("outcome") == "success"]
        durations = [m["duration_seconds"] for m in metrics if m.get("duration_seconds")]

        return {
            "total": len(metrics),
            "successful": len(successful),
            "success_rate": len(successful) / len(metrics) * 100 if metrics else 0,
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "by_complexity": self._group_by_complexity(metrics),
        }

    def _group_by_complexity(self, metrics: list[dict]) -> dict:
        """Group metrics by complexity level."""
        groups: dict[str, list[dict]] = {}
        for m in metrics:
            c = m.get("complexity", "unknown")
            if c not in groups:
                groups[c] = []
            groups[c].append(m)

        result = {}
        for complexity, items in groups.items():
            durations = [i["duration_seconds"] for i in items if i.get("duration_seconds")]
            result[complexity] = {
                "count": len(items),
                "avg_duration": sum(durations) / len(durations) if durations else 0,
            }
        return result
