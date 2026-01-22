"""Brainstorming session models and storage for Lloyd."""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class BrainstormSession:
    """A brainstorming session for refining vague ideas into specs."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    initial_idea: str = ""
    clarifications: list[dict[str, str]] = field(default_factory=list)  # [{question, answer}]
    spec: str | None = None
    status: str = "in_progress"  # in_progress, spec_ready, approved, queued
    created_at: datetime = field(default_factory=datetime.now)

    def add_clarification(self, question: str, answer: str) -> None:
        """Add a clarification Q&A pair.

        Args:
            question: The clarifying question.
            answer: The user's answer.
        """
        self.clarifications.append({"question": question, "answer": answer})

    def set_spec(self, spec: str) -> None:
        """Set the generated spec.

        Args:
            spec: The specification text.
        """
        self.spec = spec
        self.status = "spec_ready"

    def approve(self) -> None:
        """Approve the spec and queue for execution."""
        self.status = "approved"

    def queue(self) -> None:
        """Mark as queued for execution."""
        self.status = "queued"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "initial_idea": self.initial_idea,
            "clarifications": self.clarifications,
            "spec": self.spec,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BrainstormSession":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            initial_idea=data["initial_idea"],
            clarifications=data.get("clarifications", []),
            spec=data.get("spec"),
            status=data["status"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


class BrainstormStore:
    """Persistent storage for brainstorm sessions."""

    def __init__(self, lloyd_dir: Path | None = None) -> None:
        """Initialize the brainstorm store.

        Args:
            lloyd_dir: Lloyd data directory. Defaults to .lloyd
        """
        self.lloyd_dir = lloyd_dir or Path(".lloyd")
        self.brainstorm_dir = self.lloyd_dir / "brainstorms"

    def _ensure_dir(self) -> None:
        """Ensure the brainstorm directory exists."""
        self.brainstorm_dir.mkdir(parents=True, exist_ok=True)

    def save(self, session: BrainstormSession) -> None:
        """Save a brainstorm session.

        Args:
            session: The session to save.
        """
        self._ensure_dir()
        path = self.brainstorm_dir / f"{session.session_id}.json"
        with open(path, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    def get(self, session_id: str) -> BrainstormSession | None:
        """Get a brainstorm session by ID.

        Args:
            session_id: The session ID.

        Returns:
            The session or None if not found.
        """
        path = self.brainstorm_dir / f"{session_id}.json"
        if not path.exists():
            return None
        with open(path) as f:
            data = json.load(f)
        return BrainstormSession.from_dict(data)

    def list_sessions(self) -> list[str]:
        """List all session IDs.

        Returns:
            List of session IDs.
        """
        self._ensure_dir()
        return [f.stem for f in self.brainstorm_dir.glob("*.json")]

    def list_all(self) -> list[BrainstormSession]:
        """List all brainstorm sessions.

        Returns:
            List of all sessions.
        """
        self._ensure_dir()
        sessions = []
        for f in self.brainstorm_dir.glob("*.json"):
            with open(f) as file:
                data = json.load(file)
                sessions.append(BrainstormSession.from_dict(data))
        return sessions

    def delete(self, session_id: str) -> bool:
        """Delete a brainstorm session.

        Args:
            session_id: The session ID.

        Returns:
            True if deleted, False if not found.
        """
        path = self.brainstorm_dir / f"{session_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False
