"""Debug session storage for Lloyd."""

import json
from pathlib import Path

from .models import DebugSession


class DebugStore:
    """Persistent storage for debug sessions."""

    def __init__(self, lloyd_dir: Path | None = None) -> None:
        """Initialize the debug store.

        Args:
            lloyd_dir: Lloyd data directory. Defaults to .lloyd
        """
        self.lloyd_dir = lloyd_dir or Path(".lloyd")
        self.debug_dir = self.lloyd_dir / "debug"

    def _ensure_dir(self) -> None:
        """Ensure the debug directory exists."""
        self.debug_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        """Get the path for a session file."""
        return self.debug_dir / f"{session_id}.json"

    def save(self, session: DebugSession) -> None:
        """Save a debug session.

        Args:
            session: The session to save.
        """
        self._ensure_dir()
        with open(self._session_path(session.session_id), "w") as f:
            json.dump(session.to_dict(), f, indent=2)

    def get(self, session_id: str) -> DebugSession | None:
        """Get a debug session by ID.

        Args:
            session_id: The session ID.

        Returns:
            The session or None if not found.
        """
        path = self._session_path(session_id)
        if not path.exists():
            return None
        with open(path) as f:
            data = json.load(f)
        return DebugSession.from_dict(data)

    def list_active(self) -> list[str]:
        """List session IDs that are in progress.

        Returns:
            List of active session IDs.
        """
        self._ensure_dir()
        active = []
        for f in self.debug_dir.glob("*.json"):
            with open(f) as file:
                data = json.load(file)
                if data.get("status") == "in_progress":
                    active.append(data["session_id"])
        return active

    def list_all(self) -> list[DebugSession]:
        """List all debug sessions.

        Returns:
            List of all sessions.
        """
        self._ensure_dir()
        sessions = []
        for f in self.debug_dir.glob("*.json"):
            with open(f) as file:
                data = json.load(file)
                sessions.append(DebugSession.from_dict(data))
        return sessions

    def delete(self, session_id: str) -> bool:
        """Delete a debug session.

        Args:
            session_id: The session ID.

        Returns:
            True if deleted, False if not found.
        """
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False
