"""Knowledge/learning entry models for Lloyd."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class LearningEntry:
    """A learned pattern or piece of knowledge."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    category: str = ""  # bug_pattern, fix_strategy, user_preference, etc.
    title: str = ""
    description: str = ""
    context: str = ""
    confidence: float = 0.3  # 0.0 to 1.0
    frequency: int = 1
    last_applied: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)

    def apply(self, success: bool) -> None:
        """Update confidence based on application result.

        Args:
            success: Whether the application was successful.
        """
        self.frequency += 1
        self.last_applied = datetime.now()
        if success:
            self.confidence = min(1.0, self.confidence + 0.1)
        else:
            self.confidence = max(0.0, self.confidence - 0.15)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "context": self.context,
            "confidence": self.confidence,
            "frequency": self.frequency,
            "last_applied": self.last_applied.isoformat() if self.last_applied else None,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningEntry":
        """Create from dictionary."""
        last_applied = None
        if data.get("last_applied"):
            last_applied = datetime.fromisoformat(data["last_applied"])

        return cls(
            id=data["id"],
            category=data["category"],
            title=data["title"],
            description=data["description"],
            context=data.get("context", ""),
            confidence=data["confidence"],
            frequency=data["frequency"],
            last_applied=last_applied,
            created_at=datetime.fromisoformat(data["created_at"]),
            tags=data.get("tags", []),
        )
