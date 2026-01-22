"""Debug feedback loop models for Lloyd."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class DebugAttempt:
    """A single debugging attempt within a session."""

    attempt_number: int
    approach: str
    result: str
    feedback_type: Literal["fixed", "regression", "partial", "no_effect"] | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "attempt_number": self.attempt_number,
            "approach": self.approach,
            "result": self.result,
            "feedback_type": self.feedback_type,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DebugAttempt":
        """Create from dictionary."""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class DebugSession:
    """A debugging session for iterative bug fixing."""

    session_id: str
    project_id: str
    original_issue: str
    attempts: list[DebugAttempt] = field(default_factory=list)
    status: Literal["in_progress", "resolved", "escalated"] = "in_progress"
    max_attempts: int = 5
    created_at: datetime = field(default_factory=datetime.now)

    def add_attempt(self, approach: str, result: str) -> DebugAttempt:
        """Add a new debugging attempt.

        Args:
            approach: Description of the fix approach.
            result: Result of applying the fix.

        Returns:
            The created attempt.
        """
        attempt = DebugAttempt(
            attempt_number=len(self.attempts) + 1,
            approach=approach,
            result=result,
        )
        self.attempts.append(attempt)
        return attempt

    def record_feedback(
        self, feedback_type: Literal["fixed", "regression", "partial", "no_effect"]
    ) -> None:
        """Record feedback for the most recent attempt.

        Args:
            feedback_type: Type of feedback from user.
        """
        if self.attempts:
            self.attempts[-1].feedback_type = feedback_type

            if feedback_type == "fixed":
                self.status = "resolved"
            elif len(self.attempts) >= self.max_attempts:
                self.status = "escalated"

    def get_failed_approaches(self) -> list[str]:
        """Get approaches that didn't work, to avoid retrying them.

        Returns:
            List of failed approach descriptions.
        """
        return [
            a.approach
            for a in self.attempts
            if a.feedback_type in ["no_effect", "regression"]
        ]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "project_id": self.project_id,
            "original_issue": self.original_issue,
            "attempts": [a.to_dict() for a in self.attempts],
            "status": self.status,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DebugSession":
        """Create from dictionary."""
        attempts = [DebugAttempt.from_dict(a) for a in data.get("attempts", [])]
        return cls(
            session_id=data["session_id"],
            project_id=data["project_id"],
            original_issue=data["original_issue"],
            attempts=attempts,
            status=data["status"],
            max_attempts=data["max_attempts"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )
