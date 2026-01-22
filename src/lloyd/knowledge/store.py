"""Knowledge store for Lloyd."""

import json
from pathlib import Path

from .models import LearningEntry


class KnowledgeStore:
    """Persistent storage for learned patterns and knowledge."""

    def __init__(self, lloyd_dir: Path | None = None) -> None:
        """Initialize the knowledge store.

        Args:
            lloyd_dir: Lloyd data directory. Defaults to .lloyd
        """
        self.lloyd_dir = lloyd_dir or Path(".lloyd")
        self.knowledge_file = self.lloyd_dir / "knowledge" / "entries.json"

    def _ensure_dir(self) -> None:
        """Ensure the knowledge directory exists."""
        self.knowledge_file.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[LearningEntry]:
        """Load all entries from storage."""
        if not self.knowledge_file.exists():
            return []
        with open(self.knowledge_file) as f:
            data = json.load(f)
        return [LearningEntry.from_dict(d) for d in data]

    def _save(self, entries: list[LearningEntry]) -> None:
        """Save all entries to storage."""
        self._ensure_dir()
        with open(self.knowledge_file, "w") as f:
            json.dump([e.to_dict() for e in entries], f, indent=2)

    def add(self, entry: LearningEntry) -> LearningEntry:
        """Add a learning entry.

        Args:
            entry: The entry to add.

        Returns:
            The added entry.
        """
        entries = self._load()
        entries.append(entry)
        self._save(entries)
        return entry

    def get(self, entry_id: str) -> LearningEntry | None:
        """Get an entry by ID.

        Args:
            entry_id: The entry ID.

        Returns:
            The entry or None if not found.
        """
        for entry in self._load():
            if entry.id == entry_id:
                return entry
        return None

    def update(self, entry: LearningEntry) -> bool:
        """Update an existing entry.

        Args:
            entry: The entry to update.

        Returns:
            True if updated, False if not found.
        """
        entries = self._load()
        for i, e in enumerate(entries):
            if e.id == entry.id:
                entries[i] = entry
                self._save(entries)
                return True
        return False

    def query(
        self,
        category: str | None = None,
        tags: list[str] | None = None,
        min_confidence: float = 0.0,
    ) -> list[LearningEntry]:
        """Query knowledge base with filters.

        Args:
            category: Filter by category.
            tags: Filter by tags (any match).
            min_confidence: Minimum confidence threshold.

        Returns:
            List of matching entries sorted by relevance.
        """
        entries = self._load()

        if category:
            entries = [e for e in entries if e.category == category]

        if tags:
            entries = [e for e in entries if any(t in e.tags for t in tags)]

        entries = [e for e in entries if e.confidence >= min_confidence]

        # Sort by confidence * frequency (relevance score)
        entries.sort(key=lambda e: e.confidence * e.frequency, reverse=True)

        return entries

    def get_relevant(self, context: str, limit: int = 5) -> list[LearningEntry]:
        """Get entries relevant to a context (simple keyword matching).

        Args:
            context: Context text to match against.
            limit: Maximum number of entries to return.

        Returns:
            List of relevant entries.
        """
        entries = self._load()
        context_lower = context.lower()

        scored: list[tuple[float, LearningEntry]] = []
        for entry in entries:
            score = 0.0
            for tag in entry.tags:
                if tag.lower() in context_lower:
                    score += 1
            if entry.title.lower() in context_lower:
                score += 2
            if score > 0:
                scored.append((score * entry.confidence, entry))

        scored.sort(reverse=True, key=lambda x: x[0])
        return [entry for _, entry in scored[:limit]]

    def delete(self, entry_id: str) -> bool:
        """Delete an entry.

        Args:
            entry_id: The entry ID.

        Returns:
            True if deleted, False if not found.
        """
        entries = self._load()
        original_len = len(entries)
        entries = [e for e in entries if e.id != entry_id]
        if len(entries) < original_len:
            self._save(entries)
            return True
        return False

    def list_all(self) -> list[LearningEntry]:
        """List all entries.

        Returns:
            List of all entries.
        """
        return self._load()
