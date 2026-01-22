"""Inbox item models for Lloyd."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
import uuid


@dataclass
class InboxItem:
    """An item in the inbox requiring human attention."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: Literal["review", "blocked", "question", "failed", "spec_approval"] = "review"
    project_id: str = ""
    title: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    priority: Literal["high", "normal", "low"] = "normal"
    context: dict[str, Any] = field(default_factory=dict)
    actions: list[str] = field(default_factory=list)
    resolved: bool = False
    resolved_at: datetime | None = None
    resolution: str | None = None

    def resolve(self, action: str) -> None:
        """Mark this item as resolved with the given action."""
        self.resolved = True
        self.resolved_at = datetime.now()
        self.resolution = action

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "project_id": self.project_id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "priority": self.priority,
            "context": self.context,
            "actions": self.actions,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InboxItem":
        """Create an InboxItem from a dictionary."""
        data = data.copy()
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("resolved_at"):
            data["resolved_at"] = datetime.fromisoformat(data["resolved_at"])
        return cls(**data)
